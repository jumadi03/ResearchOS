"""Rotate the local PostgreSQL password with automatic rollback."""

from __future__ import annotations

from pathlib import Path
import secrets
import subprocess
import time

from bootstrap_local import atomic_secret_write, parse_env, replace_env


ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "deploy"
STACK_PATH = DEPLOY / "stack.env"


def compose(*arguments: str) -> None:
    subprocess.run(
        [
            "docker", "compose", "--env-file", "stack.env", "-f", "compose.yaml",
            *arguments,
        ],
        cwd=DEPLOY,
        check=True,
    )


def alter_role(username: str, password: str) -> None:
    if not username.replace("_", "").isalnum():
        raise RuntimeError("POSTGRES_USER is unsafe for role rotation")
    sql = f'ALTER ROLE "{username}" PASSWORD \'{password}\';\n'
    subprocess.run(
        [
            "docker", "exec", "-i", "researchos-postgres-1",
            "psql", "-v", "ON_ERROR_STOP=1", "-U", username, "-d", "postgres",
        ],
        input=sql,
        text=True,
        check=True,
        capture_output=True,
    )


def recreate_consumers() -> None:
    compose(
        "up", "--detach", "--force-recreate", "--wait",
        "postgres", "api", "worker", "backup", "postgres-exporter",
    )


def password_works(values: dict[str, str], password: str) -> bool:
    import psycopg

    for attempt in range(10):
        try:
            with psycopg.connect(
                host="127.0.0.1",
                port=5432,
                dbname=values.get("POSTGRES_DB", "researchos"),
                user=values.get("POSTGRES_USER", "researchos"),
                password=password,
                connect_timeout=3,
            ) as connection, connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return cursor.fetchone() == (1,)
        except psycopg.Error:
            if attempt == 9:
                return False
            time.sleep(2)
    return False


def rotate() -> None:
    original_stack = STACK_PATH.read_text(encoding="utf-8")
    values = parse_env(original_stack)
    username = values.get("POSTGRES_USER", "researchos")
    old_password = values["POSTGRES_PASSWORD"]
    new_password = secrets.token_urlsafe(32)
    rotated_stack = replace_env(
        original_stack, {"POSTGRES_PASSWORD": new_password}
    )

    database_changed = False
    try:
        alter_role(username, new_password)
        database_changed = True
        atomic_secret_write(STACK_PATH, rotated_stack)
        recreate_consumers()
        if not password_works(values, new_password):
            raise RuntimeError("New PostgreSQL password was not accepted")
        if password_works(values, old_password):
            raise RuntimeError("Old PostgreSQL password is still accepted")
    except BaseException:
        if database_changed:
            alter_role(username, old_password)
        atomic_secret_write(STACK_PATH, original_stack)
        recreate_consumers()
        raise
    print(
        "postgres-password-rotation=passed "
        "new_password=accepted old_password=rejected secrets=hidden"
    )


if __name__ == "__main__":
    rotate()
