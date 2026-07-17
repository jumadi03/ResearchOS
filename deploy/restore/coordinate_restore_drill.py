"""Coordinate an exclusive restore-drill lease without executing the drill."""

from __future__ import annotations

import argparse
import json
import os
from uuid import UUID

import psycopg


class RestoreDrillCoordinationError(RuntimeError):
    """Raised when canonical restore-drill coordination rejects an action."""


def _connect(database_url: str):
    return psycopg.connect(database_url)


def acquire(database_url: str, owner: str, lease_seconds: int) -> dict:
    with _connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT run_id,lease_token,backup_id,backup_stamp,backup_set_hash,
                   manifest_filename,lease_expires_at
            FROM acquire_restore_drill_lease(%s,%s)
            """,
            (owner, lease_seconds),
        )
        row = cursor.fetchone()
    if row is None:
        raise RestoreDrillCoordinationError("Lease acquisition returned no canonical run")
    return {
        "status": "running",
        "run_id": str(row[0]),
        "lease_token": str(row[1]),
        "backup_id": str(row[2]),
        "backup_stamp": row[3],
        "backup_set_hash": row[4],
        "manifest_filename": row[5],
        "lease_expires_at": row[6].isoformat(),
    }


def acquire_due(database_url: str, owner: str, lease_seconds: int) -> dict:
    with _connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT schedule_status,next_due_at,run_id,lease_token,backup_id,
                   backup_stamp,backup_set_hash,manifest_filename,lease_expires_at
            FROM acquire_due_restore_drill_lease(%s,%s)
            """,
            (owner, lease_seconds),
        )
        row = cursor.fetchone()
    if row is None:
        raise RestoreDrillCoordinationError(
            "Scheduled lease decision returned no canonical receipt"
        )
    receipt = {"status": row[0], "next_due_at": row[1].isoformat()}
    if row[0] == "running" and row[3] is not None:
        receipt.update(
            {
                "run_id": str(row[2]),
                "lease_token": str(row[3]),
                "backup_id": str(row[4]),
                "backup_stamp": row[5],
                "backup_set_hash": row[6],
                "manifest_filename": row[7],
                "lease_expires_at": row[8].isoformat(),
            }
        )
    elif row[2] is not None:
        receipt["run_id"] = str(row[2])
    return receipt


def schedule_status(database_url: str) -> dict:
    with _connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT status,cadence_seconds,next_due_at,revision,policy_hash,
                   pending_run_id
            FROM restore_drill_schedule_state WHERE schedule_name='canonical'
            """
        )
        row = cursor.fetchone()
    if row is None:
        raise RestoreDrillCoordinationError("Canonical restore schedule is missing")
    return {
        "status": row[0],
        "cadence_seconds": row[1],
        "next_due_at": row[2].isoformat(),
        "revision": row[3],
        "policy_hash": row[4],
        "pending_run_id": str(row[5]) if row[5] else None,
    }


def configure_schedule(
    database_url: str, cadence_seconds: int, actor: str, rationale: str
) -> dict:
    with _connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT configure_restore_drill_schedule(%s,%s,%s)",
            (cadence_seconds, actor, rationale),
        )
        revision = cursor.fetchone()[0]
    return {"status": "configured", "revision": revision}


def transition_schedule(
    database_url: str, status: str, actor: str, rationale: str
) -> dict:
    with _connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT set_restore_drill_schedule_status(%s,%s,%s)",
            (status, actor, rationale),
        )
        result = cursor.fetchone()[0]
    return {"status": result}


def complete(
    database_url: str,
    run_id: UUID,
    lease_token: UUID,
    report_content_hash: str,
    verification_id: UUID,
    actor: str,
) -> dict:
    with _connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT complete_restore_drill_run(%s,%s,%s,%s,%s)",
            (run_id, lease_token, report_content_hash, verification_id, actor),
        )
        status = cursor.fetchone()[0]
    if status != "completed":
        raise RestoreDrillCoordinationError(
            "Restore drill completion was rejected because the lease expired"
        )
    return {
        "status": status,
        "run_id": str(run_id),
        "verification_id": str(verification_id),
        "report_content_hash": report_content_hash,
    }


def fail(
    database_url: str,
    run_id: UUID,
    lease_token: UUID,
    error: str,
    actor: str,
) -> dict:
    with _connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT fail_restore_drill_run(%s,%s,%s,%s)",
            (run_id, lease_token, error, actor),
        )
        status = cursor.fetchone()[0]
    return {
        "status": status,
        "run_id": str(run_id),
        "error": error[:2000],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL"),
        help="Canonical PostgreSQL URL; defaults to DATABASE_URL",
    )
    actions = parser.add_subparsers(dest="action", required=True)

    acquire_parser = actions.add_parser("acquire")
    acquire_parser.add_argument("--owner", required=True)
    acquire_parser.add_argument("--lease-seconds", type=int, default=3600)

    due_parser = actions.add_parser("acquire-due")
    due_parser.add_argument("--owner", required=True)
    due_parser.add_argument("--lease-seconds", type=int, default=3600)

    actions.add_parser("schedule-status")

    configure_parser = actions.add_parser("schedule-configure")
    configure_parser.add_argument("--cadence-seconds", type=int, required=True)
    configure_parser.add_argument("--actor", required=True)
    configure_parser.add_argument("--rationale", required=True)

    for action in ("schedule-pause", "schedule-resume"):
        transition_parser = actions.add_parser(action)
        transition_parser.add_argument("--actor", required=True)
        transition_parser.add_argument("--rationale", required=True)

    complete_parser = actions.add_parser("complete")
    complete_parser.add_argument("--run-id", type=UUID, required=True)
    complete_parser.add_argument("--lease-token", type=UUID, required=True)
    complete_parser.add_argument("--report-content-hash", required=True)
    complete_parser.add_argument("--verification-id", type=UUID, required=True)
    complete_parser.add_argument("--actor", required=True)

    fail_parser = actions.add_parser("fail")
    fail_parser.add_argument("--run-id", type=UUID, required=True)
    fail_parser.add_argument("--lease-token", type=UUID, required=True)
    fail_parser.add_argument("--error", required=True)
    fail_parser.add_argument("--actor", required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if not args.database_url:
        print("restore drill coordination: rejected: DATABASE_URL is required")
        return 1
    try:
        if args.action == "acquire":
            result = acquire(args.database_url, args.owner, args.lease_seconds)
        elif args.action == "acquire-due":
            result = acquire_due(args.database_url, args.owner, args.lease_seconds)
        elif args.action == "schedule-status":
            result = schedule_status(args.database_url)
        elif args.action == "schedule-configure":
            result = configure_schedule(
                args.database_url,
                args.cadence_seconds,
                args.actor,
                args.rationale,
            )
        elif args.action in {"schedule-pause", "schedule-resume"}:
            result = transition_schedule(
                args.database_url,
                "paused" if args.action == "schedule-pause" else "active",
                args.actor,
                args.rationale,
            )
        elif args.action == "complete":
            result = complete(
                args.database_url,
                args.run_id,
                args.lease_token,
                args.report_content_hash,
                args.verification_id,
                args.actor,
            )
        else:
            result = fail(
                args.database_url,
                args.run_id,
                args.lease_token,
                args.error,
                args.actor,
            )
    except (psycopg.Error, RestoreDrillCoordinationError) as exc:
        print(f"restore drill coordination: rejected: {exc}")
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
