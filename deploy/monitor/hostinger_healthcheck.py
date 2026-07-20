"""Continuously verify the private ResearchOS production dependencies."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
import time
from urllib.request import urlopen

import psycopg


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def check_http(name: str, url: str) -> dict[str, object]:
    with urlopen(url, timeout=10) as response:
        if response.status != 200:
            raise RuntimeError(f"{name} returned HTTP {response.status}")
    return {"name": name, "status": "passed"}


def check_database(database_url: str, expected_schema: int) -> dict[str, object]:
    with psycopg.connect(database_url, connect_timeout=10) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COALESCE(MAX(version), 0) FROM schema_migrations")
            schema_version = int(cursor.fetchone()[0])
            cursor.execute("SELECT COUNT(*) FROM knowledge_objects")
            object_count = int(cursor.fetchone()[0])
    if schema_version != expected_schema:
        raise RuntimeError(
            f"schema version {schema_version} does not match {expected_schema}"
        )
    return {
        "name": "postgresql",
        "status": "passed",
        "schema_version": schema_version,
        "canonical_object_count": object_count,
    }


def run_checks() -> tuple[dict[str, object], bool]:
    checks: list[dict[str, object]] = []
    failures: list[str] = []
    configured_checks = (
        (
            "api",
            os.environ.get(
                "RESEARCHOS_INTERNAL_HEALTH_URL", "http://api:8000/health"
            ),
        ),
        (
            "minio",
            os.environ.get(
                "MINIO_INTERNAL_HEALTH_URL",
                "http://minio:9000/minio/health/live",
            ),
        ),
    )
    for name, url in configured_checks:
        try:
            checks.append(check_http(name, url))
        except Exception as exc:
            failures.append(f"{name}: {exc}")
            checks.append({"name": name, "status": "failed"})
    try:
        checks.append(
            check_database(
                os.environ["DATABASE_URL"],
                int(os.environ.get("EXPECTED_SCHEMA_VERSION", "41")),
            )
        )
    except Exception as exc:
        failures.append(f"postgresql: {exc}")
        checks.append({"name": "postgresql", "status": "failed"})
    passed = not failures
    return (
        {
            "schema_version": "1.0",
            "checked_at": utc_now().isoformat(),
            "status": "passed" if passed else "failed",
            "checks": checks,
            "failures": failures,
        },
        passed,
    )


def write_state(path: Path, state: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.partial")
    temporary.write_text(
        json.dumps(state, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def verify_state(path: Path, interval_seconds: int) -> int:
    state = json.loads(path.read_text(encoding="utf-8"))
    checked_at = datetime.fromisoformat(str(state["checked_at"]))
    maximum_age = timedelta(seconds=max(interval_seconds * 3, 180))
    if state.get("status") != "passed" or utc_now() - checked_at > maximum_age:
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--verify-state", action="store_true")
    args = parser.parse_args()
    interval = int(os.environ.get("HEALTHCHECK_INTERVAL_SECONDS", "60"))
    state_path = Path(
        os.environ.get("HEALTHCHECK_STATE_PATH", "/state/health.json")
    )
    if args.verify_state:
        try:
            return verify_state(state_path, interval)
        except (OSError, KeyError, ValueError, json.JSONDecodeError):
            return 1
    while True:
        state, passed = run_checks()
        write_state(state_path, state)
        print(json.dumps(state, sort_keys=True), flush=True)
        if args.once:
            return 0 if passed else 1
        time.sleep(interval)


if __name__ == "__main__":
    sys.exit(main())
