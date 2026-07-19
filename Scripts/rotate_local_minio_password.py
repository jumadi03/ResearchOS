"""Rotate the local MinIO root password with automatic rollback."""

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


def recreate_consumers() -> None:
    compose(
        "up", "--detach", "--force-recreate", "--wait",
        "minio", "api", "worker", "backup",
    )


def credentials_work(access_key: str, secret_key: str) -> bool:
    import boto3
    from botocore.config import Config

    client = boto3.client(
        "s3",
        endpoint_url="http://127.0.0.1:9000",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(connect_timeout=3, read_timeout=3, retries={"max_attempts": 0}),
    )
    for attempt in range(10):
        try:
            client.head_bucket(Bucket="researchos-documents")
            client.head_bucket(Bucket="researchos-backups")
            return True
        except Exception:
            if attempt == 9:
                return False
            time.sleep(2)
    return False


def rotate() -> None:
    original_stack = STACK_PATH.read_text(encoding="utf-8")
    values = parse_env(original_stack)
    access_key = values.get("MINIO_ROOT_USER", "researchos")
    old_password = values["MINIO_ROOT_PASSWORD"]
    new_password = secrets.token_urlsafe(32)
    rotated_stack = replace_env(
        original_stack, {"MINIO_ROOT_PASSWORD": new_password}
    )

    try:
        atomic_secret_write(STACK_PATH, rotated_stack)
        recreate_consumers()
        if not credentials_work(access_key, new_password):
            raise RuntimeError("New MinIO password was not accepted")
        if credentials_work(access_key, old_password):
            raise RuntimeError("Old MinIO password is still accepted")
    except BaseException:
        atomic_secret_write(STACK_PATH, original_stack)
        recreate_consumers()
        raise
    print(
        "minio-password-rotation=passed buckets=2 "
        "new_password=accepted old_password=rejected secrets=hidden"
    )


if __name__ == "__main__":
    rotate()
