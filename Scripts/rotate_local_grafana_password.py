"""Rotate the local Grafana administrator password with automatic rollback."""

from __future__ import annotations

import base64
import http.client
from pathlib import Path
import secrets
import subprocess
import time
import urllib.error
import urllib.request

from bootstrap_local import atomic_secret_write, parse_env, replace_env


ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "deploy"
STACK_PATH = DEPLOY / "stack.env"


def reset_password(password: str) -> None:
    subprocess.run(
        [
            "docker", "exec", "researchos-grafana-1",
            "grafana", "cli", "admin", "reset-admin-password", password,
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def recreate_grafana() -> None:
    subprocess.run(
        [
            "docker", "compose", "--env-file", "stack.env", "-f", "compose.yaml",
            "up", "--detach", "--force-recreate", "--wait", "grafana",
        ],
        cwd=DEPLOY,
        check=True,
    )


def login_works(username: str, password: str) -> bool:
    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
    for attempt in range(10):
        request = urllib.request.Request(
            "http://127.0.0.1:3000/api/user",
            headers={"Authorization": f"Basic {credentials}"},
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status == 200
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                return False
            if attempt == 9:
                raise
        except (http.client.RemoteDisconnected, urllib.error.URLError):
            if attempt == 9:
                raise
        time.sleep(2)
    return False


def rotate() -> None:
    original_stack = STACK_PATH.read_text(encoding="utf-8")
    values = parse_env(original_stack)
    username = values.get("GRAFANA_ADMIN_USER", "admin")
    old_password = values["GRAFANA_ADMIN_PASSWORD"]
    new_password = secrets.token_urlsafe(32)
    rotated_stack = replace_env(
        original_stack, {"GRAFANA_ADMIN_PASSWORD": new_password}
    )

    database_changed = False
    try:
        reset_password(new_password)
        database_changed = True
        atomic_secret_write(STACK_PATH, rotated_stack)
        recreate_grafana()
        if not login_works(username, new_password):
            raise RuntimeError("New Grafana password was not accepted")
        if login_works(username, old_password):
            raise RuntimeError("Old Grafana password is still accepted")
    except BaseException:
        if database_changed:
            reset_password(old_password)
        atomic_secret_write(STACK_PATH, original_stack)
        recreate_grafana()
        raise
    print(
        "grafana-password-rotation=passed "
        "new_password=accepted old_password=rejected secrets=hidden"
    )


if __name__ == "__main__":
    rotate()
