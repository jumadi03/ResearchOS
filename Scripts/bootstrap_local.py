"""Secure, idempotent bootstrap for the local ResearchOS stack."""

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile
import urllib.request


ACCOUNT_DEFINITIONS = (
    ("discoverer", "Research Discoverer", ["discoverer"]),
    ("auditor", "Research Auditor", ["auditor"]),
    ("reviewer", "Research Reviewer", ["reviewer"]),
    ("indexer", "Research Indexer", ["indexer"]),
    ("admin", "Research Administrator", ["admin"]),
)
TOKEN_ROLES = ("discoverer", "auditor", "reviewer", "indexer")


def parse_env(content: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in content.splitlines():
        if line and not line.lstrip().startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value
    return values


def replace_env(content: str, replacements: dict[str, str]) -> str:
    found: set[str] = set()
    output: list[str] = []
    for line in content.splitlines():
        if line and not line.lstrip().startswith("#") and "=" in line:
            key = line.split("=", 1)[0].strip()
            if key in replacements:
                output.append(f"{key}={replacements[key]}")
                found.add(key)
                continue
        output.append(line)
    missing = set(replacements) - found
    if missing:
        raise RuntimeError(f"Template is missing required keys: {sorted(missing)}")
    return "\n".join(output) + "\n"


def atomic_secret_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def generated_configuration(template: str) -> tuple[str, str, str]:
    tokens = {role: secrets.token_hex(32) for role in TOKEN_ROLES}
    monitor_token = secrets.token_hex(32)
    passwords = {name: secrets.token_urlsafe(24) for name, _, _ in ACCOUNT_DEFINITIONS}
    knowledge = {
        tokens[role]: {
            "roles": [role],
            "actor_id": f"{role}@researchos.local",
        }
        for role in TOKEN_ROLES
    }
    architecture = {
        monitor_token: {"actor_id": "prometheus", "roles": ["auditor"]}
    }
    stack = replace_env(
        template,
        {
            "POSTGRES_PASSWORD": secrets.token_urlsafe(32),
            "MINIO_ROOT_PASSWORD": secrets.token_urlsafe(32),
            "GRAFANA_ADMIN_PASSWORD": secrets.token_urlsafe(32),
            "KNOWLEDGE_API_PRINCIPALS": json.dumps(
                knowledge, separators=(",", ":")
            ),
            "ARCHITECTURE_API_PRINCIPALS": json.dumps(
                architecture, separators=(",", ":")
            ),
        },
    )
    local_lines = [
        "# Local-only ResearchOS workspace credentials. Never commit this file.",
        *(
            f"RESEARCHOS_{role.upper()}_TOKEN={tokens[role]}"
            for role in TOKEN_ROLES
        ),
        "",
        "# Human workspace accounts (local-only bootstrap credentials)",
    ]
    for name, _, _ in ACCOUNT_DEFINITIONS:
        local_lines.extend(
            (
                f"RESEARCHOS_{name.upper()}_USERNAME={name}",
                f"RESEARCHOS_{name.upper()}_PASSWORD={passwords[name]}",
            )
        )
    return stack, "\n".join(local_lines) + "\n", monitor_token + "\n"


def validate_configuration(stack: str, local: str, monitor: str) -> None:
    stack_values = parse_env(stack)
    local_values = parse_env(local)
    if any("replace-with" in value for value in stack_values.values()):
        raise RuntimeError("Local stack still contains placeholder credentials")
    knowledge = json.loads(stack_values["KNOWLEDGE_API_PRINCIPALS"])
    architecture = json.loads(stack_values["ARCHITECTURE_API_PRINCIPALS"])
    for role in TOKEN_ROLES:
        token = local_values.get(f"RESEARCHOS_{role.upper()}_TOKEN")
        if not token or token not in knowledge:
            raise RuntimeError(f"Local {role} token is not synchronized")
    if monitor.strip() not in architecture:
        raise RuntimeError("Prometheus token is not synchronized")
    for name, _, _ in ACCOUNT_DEFINITIONS:
        username = local_values.get(f"RESEARCHOS_{name.upper()}_USERNAME")
        password = local_values.get(f"RESEARCHOS_{name.upper()}_PASSWORD")
        if not username or not password or len(password) < 20:
            raise RuntimeError(f"Local {name} account configuration is incomplete")


def ensure_configuration(root: Path) -> str:
    deploy = root / "deploy"
    stack_path = deploy / "stack.env"
    local_path = deploy / "local-access.env"
    monitor_path = deploy / "monitoring" / "prometheus.token"
    secret_paths = (stack_path, local_path, monitor_path)
    existing = [path.exists() for path in secret_paths]
    if any(existing) and not all(existing):
        raise RuntimeError(
            "Partial local configuration detected. Restore or remove all three ignored "
            "secret files before bootstrapping."
        )
    if all(existing):
        validate_configuration(
            stack_path.read_text(encoding="utf-8"),
            local_path.read_text(encoding="utf-8"),
            monitor_path.read_text(encoding="utf-8"),
        )
        return "reused"
    template = (deploy / "stack.env.example").read_text(encoding="utf-8")
    stack, local, monitor = generated_configuration(template)
    validate_configuration(stack, local, monitor)
    atomic_secret_write(stack_path, stack)
    atomic_secret_write(local_path, local)
    atomic_secret_write(monitor_path, monitor)
    return "created"


def refuse_orphaned_volumes(root: Path) -> None:
    secret_paths = (
        root / "deploy" / "stack.env",
        root / "deploy" / "local-access.env",
        root / "deploy" / "monitoring" / "prometheus.token",
    )
    if any(path.exists() for path in secret_paths) or shutil.which("docker") is None:
        return
    result = subprocess.run(
        [
            "docker", "volume", "ls", "--quiet", "--filter",
            "label=com.docker.compose.project=researchos",
        ],
        text=True,
        capture_output=True,
        check=True,
    )
    if result.stdout.strip():
        raise RuntimeError(
            "ResearchOS volumes exist but local credentials are missing. Restore the "
            "ignored secret files instead of generating incompatible passwords."
        )


def compose(root: Path, *arguments: str, input_text: str | None = None) -> None:
    command = [
        "docker", "compose", "--env-file", "stack.env", "-f", "compose.yaml",
        *arguments,
    ]
    subprocess.run(
        command,
        cwd=root / "deploy",
        input=input_text,
        text=True,
        check=True,
    )


def bootstrap_accounts(root: Path) -> None:
    local = parse_env((root / "deploy" / "local-access.env").read_text(encoding="utf-8"))
    accounts = [
        {
            "username": local[f"RESEARCHOS_{name.upper()}_USERNAME"],
            "password": local[f"RESEARCHOS_{name.upper()}_PASSWORD"],
            "display_name": display_name,
            "roles": roles,
        }
        for name, display_name, roles in ACCOUNT_DEFINITIONS
    ]
    source = """
import json, os, sys
import boto3
from app.product.sessions import WorkspaceSessionManager

accounts = json.load(sys.stdin)
manager = WorkspaceSessionManager(os.environ["DATABASE_URL"])
for account in accounts:
    manager.create_user(
        account["username"], account["password"],
        account["display_name"], account["roles"],
    )
    token, _, _, _ = manager.login(
        account["username"], account["password"], "local-bootstrap-check"
    )
    manager.logout(token)
client = boto3.client(
    "s3", endpoint_url=os.environ["MINIO_ENDPOINT"],
    aws_access_key_id=os.environ["MINIO_ACCESS_KEY"],
    aws_secret_access_key=os.environ["MINIO_SECRET_KEY"],
)
for bucket in ("researchos-documents", "researchos-backups"):
    client.head_bucket(Bucket=bucket)
print("runtime-bootstrap=passed accounts=5 buckets=2")
"""
    encoded = base64.b64encode(source.encode()).decode()
    runner = "import os,base64;exec(base64.b64decode(os.getenv('BOOTSTRAP_CODE')))"
    compose(
        root,
        "exec", "-T", "-e", f"BOOTSTRAP_CODE={encoded}",
        "api", "python", "-c", runner,
        input_text=json.dumps(accounts),
    )


def verify_health() -> None:
    with urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=15) as response:
        if response.status != 200:
            raise RuntimeError(f"ResearchOS health check returned {response.status}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--configuration-only", action="store_true",
        help="Generate or validate ignored secret files without starting Docker.",
    )
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    refuse_orphaned_volumes(root)
    state = ensure_configuration(root)
    print(f"local-configuration={state} secrets=hidden", flush=True)
    if args.configuration_only:
        return 0
    if shutil.which("docker") is None:
        raise RuntimeError("Docker is required to start the local ResearchOS stack")
    compose(root, "up", "--build", "--detach", "--wait")
    bootstrap_accounts(root)
    verify_health()
    print("researchos-bootstrap=passed credentials=deploy/local-access.env")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.CalledProcessError, OSError) as error:
        print(f"bootstrap-error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
