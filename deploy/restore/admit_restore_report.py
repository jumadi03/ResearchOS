"""Verify and idempotently admit one signed restore report to the canonical ledger."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

from app.product.restore_attestation import (
    RestoreAttestationError,
    verify_signed_report,
)


def admit_report(
    report_path: Path,
    trust_root: Path,
    database_url: str,
) -> dict:
    if report_path.is_symlink() or not report_path.is_file():
        raise RestoreAttestationError("Restore report is not a safe regular file")
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RestoreAttestationError("Restore report is unreadable") from exc
    if not isinstance(report, dict):
        raise RestoreAttestationError("Restore report must be a JSON object")
    verify_signed_report(report, trust_root)
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT admit_backup_restore_verification(%s)",
            (Jsonb(report),),
        )
        verification_id = cursor.fetchone()[0]
    return {
        "status": "admitted",
        "verification_id": str(verification_id),
        "content_hash": report["content_hash"],
        "manifest_hash": report["manifest_hash"],
        "attestation_key_id": report["attestation"]["key_id"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--trust-root", type=Path, required=True)
    parser.add_argument("--database-url", required=True)
    args = parser.parse_args()
    try:
        receipt = admit_report(
            args.report.resolve(),
            args.trust_root.resolve(),
            args.database_url,
        )
    except (OSError, psycopg.Error, RestoreAttestationError) as exc:
        print(f"restore evidence admission: rejected: {exc}")
        return 1
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
