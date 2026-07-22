"""Verify local PostgreSQL and object-storage continuity across a safe restart."""

from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import subprocess
import sys
import time

import bootstrap_local


PROBE_SOURCE = r"""
import hashlib, io, json, os, sys
import boto3
import psycopg

request = json.load(sys.stdin)
client = boto3.client(
    "s3",
    endpoint_url=os.environ["MINIO_ENDPOINT"],
    aws_access_key_id=os.environ["MINIO_ACCESS_KEY"],
    aws_secret_access_key=os.environ["MINIO_SECRET_KEY"],
)
bucket = os.environ["MINIO_DOCUMENT_BUCKET"]
key = request["key"]
payload = request["payload"].encode()
if request["operation"] == "before":
    client.put_object(Bucket=bucket, Key=key, Body=io.BytesIO(payload), ContentLength=len(payload))
else:
    stored = client.get_object(Bucket=bucket, Key=key)["Body"].read()
    if stored != payload:
        raise RuntimeError("Object-storage continuity sentinel changed")
    client.delete_object(Bucket=bucket, Key=key)

with psycopg.connect(os.environ["DATABASE_URL"]) as connection, connection.cursor() as cursor:
    cursor.execute("SELECT system_identifier::text FROM pg_control_system()")
    system_identifier = cursor.fetchone()[0]
    cursor.execute("SELECT COALESCE(max(version), 0) FROM schema_migrations")
    schema_version = cursor.fetchone()[0]
    cursor.execute("SELECT username FROM workspace_users ORDER BY username")
    usernames = [row[0] for row in cursor.fetchall()]

print(json.dumps({
    "postgres_system_identifier": system_identifier,
    "schema_version": schema_version,
    "workspace_user_count": len(usernames),
    "workspace_user_hash": hashlib.sha256("\n".join(usernames).encode()).hexdigest(),
    "object_sentinel_sha256": hashlib.sha256(payload).hexdigest(),
}, sort_keys=True))
"""


def probe(root: Path, *, operation: str, key: str, payload: str) -> dict:
    encoded = base64.b64encode(PROBE_SOURCE.encode()).decode()
    runner = "import base64,os;exec(base64.b64decode(os.environ['CONTINUITY_CODE']))"
    result = bootstrap_local.compose(
        root,
        "exec", "-T", "-e", f"CONTINUITY_CODE={encoded}",
        "api", "python", "-c", runner,
        input_text=json.dumps({"operation": operation, "key": key, "payload": payload}),
        capture_output=True,
    )
    return json.loads(result.stdout)


def verify(root: Path, report_path: Path) -> dict:
    bootstrap_local.require_local_configuration(root)
    bootstrap_local.show_status(root)
    key = f"operations/continuity-probe/{secrets.token_hex(16)}"
    payload = secrets.token_hex(32)
    before = probe(root, operation="before", key=key, payload=payload)
    try:
        bootstrap_local.compose(root, "restart", "postgres", "minio", "api", "worker")
        last_error: BaseException | None = None
        for _attempt in range(20):
            try:
                bootstrap_local.verify_runtime()
                last_error = None
                break
            except (RuntimeError, OSError) as error:
                last_error = error
                time.sleep(3)
        if last_error is not None:
            raise RuntimeError(
                f"ResearchOS did not become ready after restart: {last_error}"
            )
        after = probe(root, operation="after", key=key, payload=payload)
    except BaseException:
        try:
            probe(root, operation="after", key=key, payload=payload)
        except BaseException:
            pass
        raise
    if before != after:
        raise RuntimeError("Local persistence identity changed across restart")
    report = {
        "schema_version": "1.0",
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "result": "passed",
        "restart": "docker_compose_restart_data_preserved",
        "evidence": before,
        "sentinel_cleanup": "passed",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        type=Path,
        default=Path(".tmp/local-continuity-report.json"),
    )
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    report = verify(root, (root / args.report).resolve())
    print(
        "local-continuity=passed "
        f"schema={report['evidence']['schema_version']} "
        f"accounts={report['evidence']['workspace_user_count']} "
        f"report={args.report}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.CalledProcessError, OSError, ValueError) as error:
        print(f"continuity-error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
