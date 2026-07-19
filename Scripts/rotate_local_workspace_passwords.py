"""Rotate all local human workspace passwords with automatic rollback."""

from __future__ import annotations

from pathlib import Path
import secrets
import sys

from bootstrap_local import ACCOUNT_DEFINITIONS, atomic_secret_write, parse_env, replace_env


ROOT = Path(__file__).resolve().parents[1]
ACCESS_PATH = ROOT / "deploy" / "local-access.env"
STACK_PATH = ROOT / "deploy" / "stack.env"
sys.path.insert(0, str(ROOT / "AI-Gateway"))

from app.product.sessions import WorkspaceSessionManager  # noqa: E402


def database_url(values: dict[str, str]) -> str:
    return (
        f"postgresql://{values.get('POSTGRES_USER', 'researchos')}:"
        f"{values['POSTGRES_PASSWORD']}@127.0.0.1:5432/"
        f"{values.get('POSTGRES_DB', 'researchos')}"
    )


def login_is_accepted(
    manager: WorkspaceSessionManager, username: str, password: str
) -> bool:
    try:
        token, _, _, _ = manager.login(
            username, password, "local-password-rotation-verification"
        )
    except PermissionError:
        return False
    manager.logout(token)
    return True


def rotate() -> None:
    original_access = ACCESS_PATH.read_text(encoding="utf-8")
    access_values = parse_env(original_access)
    stack_values = parse_env(STACK_PATH.read_text(encoding="utf-8"))
    manager = WorkspaceSessionManager(database_url(stack_values))
    old_passwords = {
        name: access_values[f"RESEARCHOS_{name.upper()}_PASSWORD"]
        for name, _, _ in ACCOUNT_DEFINITIONS
    }
    new_passwords = {
        name: secrets.token_urlsafe(32)
        for name, _, _ in ACCOUNT_DEFINITIONS
    }
    rotated_access = replace_env(
        original_access,
        {
            f"RESEARCHOS_{name.upper()}_PASSWORD": new_passwords[name]
            for name, _, _ in ACCOUNT_DEFINITIONS
        },
    )
    changed: list[str] = []
    try:
        for name, _, _ in ACCOUNT_DEFINITIONS:
            manager.rotate_password(
                name, new_passwords[name], "local-credential-rotation"
            )
            changed.append(name)
        atomic_secret_write(ACCESS_PATH, rotated_access)
        for name, _, _ in ACCOUNT_DEFINITIONS:
            if login_is_accepted(manager, name, old_passwords[name]):
                raise RuntimeError(f"Old password is still accepted for {name}")
            if not login_is_accepted(manager, name, new_passwords[name]):
                raise RuntimeError(f"New password was rejected for {name}")
    except BaseException:
        for name in changed:
            manager.rotate_password(
                name, old_passwords[name], "local-credential-rotation-rollback"
            )
        atomic_secret_write(ACCESS_PATH, original_access)
        raise
    print(
        "workspace-password-rotation=passed accounts=6 "
        "new_passwords=accepted old_passwords=rejected sessions=revoked "
        "secrets=hidden"
    )


if __name__ == "__main__":
    rotate()
