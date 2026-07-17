from datetime import datetime, timezone
from importlib.util import find_spec
import sys
from types import ModuleType
from uuid import UUID

if find_spec("psycopg") is None:
    psycopg = ModuleType("psycopg")
    psycopg.connect = lambda *_args, **_kwargs: None
    psycopg_types = ModuleType("psycopg.types")
    psycopg_json = ModuleType("psycopg.types.json")
    psycopg_json.Jsonb = lambda value: value
    sys.modules["psycopg"] = psycopg
    sys.modules["psycopg.types"] = psycopg_types
    sys.modules["psycopg.types.json"] = psycopg_json

from app.product.sessions import WorkspaceSessionManager


NOW = datetime(2026, 7, 17, 12, 0, tzinfo=timezone.utc)
BACKUP_ID = UUID("11111111-1111-1111-1111-111111111111")
VERIFY_ID = UUID("22222222-2222-2222-2222-222222222222")
SET_HASH = "a" * 64


class FakeCursor:
    def __init__(self, rows):
        self.rows = iter(rows)
        self.executions = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def execute(self, query, params=None):
        self.executions.append((query, params))

    def fetchone(self):
        return next(self.rows)


class FakeConnection:
    def __init__(self, rows):
        self.cursor_instance = FakeCursor(rows)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def cursor(self):
        return self.cursor_instance


class FakeManager(WorkspaceSessionManager):
    connection = None

    def _connect(self):
        return type(self).connection


def manager_with_rows(
    *rows,
    max_age_seconds=604_800,
    clock_skew_seconds=300,
):
    connection = FakeConnection(rows)
    FakeManager.connection = connection
    return (
        FakeManager(
            "unused",
            restore_trust_root="trust",
            restore_evidence_max_age_seconds=max_age_seconds,
            restore_evidence_clock_skew_seconds=clock_skew_seconds,
            clock=lambda: NOW,
        ),
        connection.cursor_instance,
    )


def backup_row(*, portable=True, completed=True):
    return (
        BACKUP_ID,
        "20260717T120000Z",
        "completed" if completed else "failed",
        completed,
        completed,
        completed,
        NOW if completed else None,
        None if completed else "failed",
        "backup-set:20260717T120000Z:aaaaaaaaaaaaaaaa" if portable else None,
        SET_HASH if portable else None,
        "/backups/backup-set-20260717T120000Z.json" if portable else None,
        portable and completed,
    )


def verified_restore(*, completed_at=NOW):
    report = {
        "content_hash": "b" * 64,
        "attestation": {
            "algorithm": "ed25519",
            "key_id": "restore-ed25519-test",
            "signature": "signature",
        },
    }
    return (
        VERIFY_ID,
        "isolated",
        "researchos_restore_drill+researchos-restore-drill",
        ["architecture", "configuration", "knowledge", "migration", "minio", "postgresql"],
        "verified",
        [{"check": "schema", "outcome": "passed"}],
        "operations",
        completed_at,
        completed_at,
        "b" * 64,
        report,
        "ed25519",
        "restore-ed25519-test",
        "signature",
    )


def test_recovery_status_is_fail_closed_without_backup():
    manager, _ = manager_with_rows(None)

    result = manager.recovery_status()

    assert result["ready"] is False
    assert result["backup_integrity_ready"] is False
    assert result["restore_verified"] is False
    assert result["recovery_ready"] is False


def test_legacy_backup_integrity_is_not_recovery_readiness():
    manager, cursor = manager_with_rows(backup_row(portable=False))

    result = manager.recovery_status()

    assert result["ready"] is True
    assert result["ready_semantics"] == "deprecated_backup_integrity_alias"
    assert result["backup_integrity_ready"] is False
    assert result["recovery_ready"] is False
    assert len(cursor.executions) == 1


def test_portable_backup_without_restore_is_not_recovery_ready():
    manager, _ = manager_with_rows(backup_row(), None)

    result = manager.recovery_status()

    assert result["backup_integrity_ready"] is True
    assert result["restore_verified"] is False
    assert result["recovery_ready"] is False


def test_matching_isolated_restore_provides_recovery_provenance(monkeypatch):
    monkeypatch.setattr(
        "app.product.sessions.verify_signed_report",
        lambda report, _root: report,
    )
    manager, cursor = manager_with_rows(backup_row(), verified_restore())

    result = manager.recovery_status()

    assert result["backup_integrity_ready"] is True
    assert result["restore_verified"] is True
    assert result["restore_fresh"] is True
    assert result["recovery_ready"] is True
    assert result["latest_restore"]["target_kind"] == "isolated"
    assert result["latest_restore"]["content_hash"] == "b" * 64
    assert result["latest_restore"]["trust_valid"] is True
    assert result["latest_restore"]["fresh"] is True
    assert result["latest_restore"]["age_seconds"] == 0
    assert cursor.executions[1][1] == (BACKUP_ID, SET_HASH)


def test_failed_restore_cannot_claim_recovery_readiness():
    restore = list(verified_restore())
    restore[4] = "failed"
    manager, _ = manager_with_rows(backup_row(), tuple(restore))

    result = manager.recovery_status()

    assert result["restore_verified"] is False
    assert result["recovery_ready"] is False


def test_untrusted_verified_row_cannot_claim_recovery_readiness():
    manager, _ = manager_with_rows(backup_row(), verified_restore())

    result = manager.recovery_status()

    assert result["restore_verified"] is False
    assert result["recovery_ready"] is False
    assert result["latest_restore"]["trust_valid"] is False


def test_stale_signed_restore_cannot_claim_recovery_readiness(monkeypatch):
    monkeypatch.setattr(
        "app.product.sessions.verify_signed_report",
        lambda report, _root: report,
    )
    stale = NOW.replace(day=9)
    manager, _ = manager_with_rows(
        backup_row(),
        verified_restore(completed_at=stale),
    )

    result = manager.recovery_status()

    assert result["restore_verified"] is True
    assert result["restore_fresh"] is False
    assert result["recovery_ready"] is False
    assert result["latest_restore"]["fresh"] is False
    assert result["latest_restore"]["age_seconds"] == 691_200
    assert result["latest_restore"]["fresh_until"].startswith("2026-07-16")
    assert result["message"] == (
        "Verified restore evidence is stale; run a new isolated restore"
    )


def test_restore_at_exact_freshness_boundary_is_accepted(monkeypatch):
    monkeypatch.setattr(
        "app.product.sessions.verify_signed_report",
        lambda report, _root: report,
    )
    boundary = NOW.replace(day=10)
    manager, _ = manager_with_rows(
        backup_row(),
        verified_restore(completed_at=boundary),
    )

    result = manager.recovery_status()

    assert result["latest_restore"]["age_seconds"] == 604_800
    assert result["restore_fresh"] is True
    assert result["recovery_ready"] is True


def test_restore_timestamp_beyond_clock_skew_is_rejected(monkeypatch):
    monkeypatch.setattr(
        "app.product.sessions.verify_signed_report",
        lambda report, _root: report,
    )
    future = NOW.replace(minute=6)
    manager, _ = manager_with_rows(
        backup_row(),
        verified_restore(completed_at=future),
    )

    result = manager.recovery_status()

    assert result["restore_verified"] is True
    assert result["restore_fresh"] is False
    assert result["recovery_ready"] is False
    assert result["latest_restore"]["age_seconds"] == -360
    assert result["message"] == (
        "Verified restore evidence timestamp is too far in the future"
    )
