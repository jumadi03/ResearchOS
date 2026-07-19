"""Rotate ignored local ResearchOS API tokens with automatic rollback."""

from __future__ import annotations

import json
import http.client
from pathlib import Path
import secrets
import subprocess
import time
import urllib.error
import urllib.request

from bootstrap_local import TOKEN_ROLES, atomic_secret_write, parse_env, replace_env


ROOT = Path(__file__).resolve().parents[1]
STACK_PATH = ROOT / "deploy" / "stack.env"
ACCESS_PATH = ROOT / "deploy" / "local-access.env"


def request_status(path: str, token: str) -> int:
    for attempt in range(10):
        request = urllib.request.Request(
            f"http://127.0.0.1:8080{path}",
            headers={"Authorization": f"Bearer {token}"},
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return response.status
        except urllib.error.HTTPError as exc:
            return exc.code
        except (
            ConnectionError,
            http.client.RemoteDisconnected,
            urllib.error.URLError,
        ):
            if attempt == 9:
                raise
            time.sleep(2)
    raise RuntimeError("Unreachable token verification state")


def recreate_runtime() -> None:
    subprocess.run(
        [
            "docker", "compose", "--env-file", "stack.env", "-f", "compose.yaml",
            "up", "--detach", "--force-recreate", "--wait", "api", "worker",
        ],
        cwd=ROOT / "deploy",
        check=True,
    )


def rotate() -> None:
    original_stack = STACK_PATH.read_text(encoding="utf-8")
    original_access = ACCESS_PATH.read_text(encoding="utf-8")
    stack_values = parse_env(original_stack)
    access_values = parse_env(original_access)
    principals = json.loads(stack_values["KNOWLEDGE_API_PRINCIPALS"])
    old_tokens = {
        role: access_values[f"RESEARCHOS_{role.upper()}_TOKEN"]
        for role in TOKEN_ROLES
    }
    new_tokens = {role: secrets.token_hex(32) for role in TOKEN_ROLES}
    rotated_principals = {
        new_tokens[role]: principals[old_tokens[role]]
        for role in TOKEN_ROLES
    }
    rotated_stack = replace_env(
        original_stack,
        {
            "KNOWLEDGE_API_PRINCIPALS": json.dumps(
                rotated_principals, separators=(",", ":")
            )
        },
    )
    rotated_access = replace_env(
        original_access,
        {
            f"RESEARCHOS_{role.upper()}_TOKEN": new_tokens[role]
            for role in TOKEN_ROLES
        },
    )

    try:
        atomic_secret_write(STACK_PATH, rotated_stack)
        atomic_secret_write(ACCESS_PATH, rotated_access)
        recreate_runtime()
        new_status = request_status("/knowledge/semantic-relations", new_tokens["reviewer"])
        old_status = request_status("/knowledge/semantic-relations", old_tokens["reviewer"])
        if new_status != 200 or old_status not in {401, 403}:
            raise RuntimeError(
                "Token verification failed after runtime recreation"
            )
    except BaseException:
        atomic_secret_write(STACK_PATH, original_stack)
        atomic_secret_write(ACCESS_PATH, original_access)
        recreate_runtime()
        raise
    print(
        "api-token-rotation=passed roles=5 "
        "new_reviewer=accepted old_reviewer=rejected secrets=hidden"
    )


if __name__ == "__main__":
    rotate()
