"""Create an idempotent ignored environment file for Hostinger deployment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import secrets

from bootstrap_local import (
    TOKEN_ROLES,
    atomic_secret_write,
    parse_env,
    replace_env,
)


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "deploy" / "stack.hostinger.env.example"
TARGET = ROOT / "deploy" / "stack.hostinger.env"


def generated_configuration(template: str, hostname: str) -> str:
    tokens = {role: secrets.token_hex(32) for role in TOKEN_ROLES}
    knowledge = {
        tokens[role]: {
            "roles": [role],
            "actor_id": f"{role}@researchos.hostinger",
        }
        for role in TOKEN_ROLES
    }
    architecture_token = secrets.token_hex(32)
    architecture = {
        architecture_token: {
            "roles": ["auditor"],
            "actor_id": "hostinger-monitor@researchos.hostinger",
        }
    }
    return replace_env(
        template,
        {
            "POSTGRES_PASSWORD": secrets.token_urlsafe(32),
            "MINIO_ROOT_PASSWORD": secrets.token_urlsafe(32),
            "KNOWLEDGE_API_PRINCIPALS": json.dumps(
                knowledge, separators=(",", ":")
            ),
            "ARCHITECTURE_API_PRINCIPALS": json.dumps(
                architecture, separators=(",", ":")
            ),
            "RESEARCHOS_API_HOSTNAME": hostname,
        },
    )


def validate_configuration(content: str, hostname: str) -> None:
    values = parse_env(content)
    if values.get("RESEARCHOS_API_HOSTNAME") != hostname:
        raise RuntimeError("Hostinger API hostname is not synchronized")
    if any("replace-with" in value for value in values.values()):
        raise RuntimeError("Hostinger environment contains placeholder credentials")
    if len(values.get("POSTGRES_PASSWORD", "")) < 32:
        raise RuntimeError("Hostinger PostgreSQL password is too short")
    if len(values.get("MINIO_ROOT_PASSWORD", "")) < 32:
        raise RuntimeError("Hostinger MinIO password is too short")
    knowledge = json.loads(values["KNOWLEDGE_API_PRINCIPALS"])
    architecture = json.loads(values["ARCHITECTURE_API_PRINCIPALS"])
    if len(knowledge) != len(TOKEN_ROLES) or len(architecture) != 1:
        raise RuntimeError("Hostinger API principal mapping is incomplete")


def ensure_configuration(hostname: str) -> str:
    if TARGET.exists():
        content = TARGET.read_text(encoding="utf-8")
        validate_configuration(content, hostname)
        return "reused"
    content = generated_configuration(
        TEMPLATE.read_text(encoding="utf-8"),
        hostname,
    )
    validate_configuration(content, hostname)
    atomic_secret_write(TARGET, content)
    return "created"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hostname", required=True)
    args = parser.parse_args()
    status = ensure_configuration(args.hostname)
    print(f"hostinger-bootstrap=passed configuration={status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
