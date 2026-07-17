from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from uuid import UUID


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "deploy/postgres/init/031_restore_drill_coordination.sql"
COORDINATOR = ROOT / "deploy/restore/coordinate_restore_drill.py"
COMPOSE = ROOT / "deploy/compose.yaml"
SPEC = spec_from_file_location("researchos_restore_coordinator", COORDINATOR)
assert SPEC and SPEC.loader
coordinator = module_from_spec(SPEC)
SPEC.loader.exec_module(coordinator)

RUN_ID = UUID("11111111-1111-1111-1111-111111111111")
TOKEN = UUID("22222222-2222-2222-2222-222222222222")
BACKUP_ID = UUID("33333333-3333-3333-3333-333333333333")
VERIFICATION_ID = UUID("44444444-4444-4444-4444-444444444444")


class FakeCursor:
    def __init__(self, row):
        self.row = row
        self.statement = None
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def execute(self, statement, params=None):
        self.statement = statement
        self.params = params

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(self, row):
        self.cursor_instance = FakeCursor(row)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def cursor(self):
        return self.cursor_instance


def test_schema_31_defines_exclusive_lease_and_auditable_lifecycle():
    contract = MIGRATION.read_text(encoding="utf-8")

    assert "restore_drill_runs_single_active_idx" in contract
    assert "WHERE status = 'running'" in contract
    assert "restore_drill_run_events_immutable" in contract
    assert "acquire_restore_drill_lease" in contract
    assert "complete_restore_drill_run" in contract
    assert "fail_restore_drill_run" in contract
    assert "another restore drill lease is already active" in contract
    assert "Restore drill lease expired before completion" in contract
    assert "canonical backup manifest path is invalid" in contract
    assert "restore verification does not match the leased backup and report" in contract
    assert "completed run requires matching canonical verification" in contract
    assert "expired restore drill lease cannot complete" in contract
    assert "'operational_staging'" in contract
    assert "'immutable_ledger'" in contract


def test_coordinator_runtime_has_database_only_and_no_execution_authority():
    compose = COMPOSE.read_text(encoding="utf-8")
    block = compose.split("  restore-coordinator:", 1)[1].split(
        "\n  postgres-exporter:", 1
    )[0]

    assert 'profiles: ["restore-coordinator"]' in block
    assert "DATABASE_URL:" in block
    assert "coordinate_restore_drill.py" in block
    for prohibited in (
        "private/",
        "restore-attestation-private",
        "/backups",
        "/reports",
        "/restore-trust",
        "docker.sock",
        "worker",
    ):
        assert prohibited not in block


def test_acquire_returns_only_server_selected_backup(monkeypatch):
    expires = datetime(2026, 7, 17, 15, 0, tzinfo=timezone.utc)
    connection = FakeConnection(
        (
            RUN_ID,
            TOKEN,
            BACKUP_ID,
            "20260717T140000Z",
            "a" * 64,
            "backup-set-20260717T140000Z.json",
            expires,
        )
    )
    monkeypatch.setattr(coordinator, "_connect", lambda _url: connection)

    result = coordinator.acquire("database", "periodic-controller", 3600)

    assert connection.cursor_instance.params == ("periodic-controller", 3600)
    assert result["run_id"] == str(RUN_ID)
    assert result["lease_token"] == str(TOKEN)
    assert result["backup_id"] == str(BACKUP_ID)
    assert result["manifest_filename"] == "backup-set-20260717T140000Z.json"
    assert "manifest" not in connection.cursor_instance.params


def test_completion_requires_canonical_verification_binding(monkeypatch):
    connection = FakeConnection(("completed",))
    monkeypatch.setattr(coordinator, "_connect", lambda _url: connection)

    result = coordinator.complete(
        "database",
        RUN_ID,
        TOKEN,
        "b" * 64,
        VERIFICATION_ID,
        "periodic-controller",
    )

    assert result["status"] == "completed"
    assert connection.cursor_instance.params == (
        RUN_ID,
        TOKEN,
        "b" * 64,
        VERIFICATION_ID,
        "periodic-controller",
    )


def test_expired_completion_is_explicitly_rejected(monkeypatch):
    connection = FakeConnection(("failed",))
    monkeypatch.setattr(coordinator, "_connect", lambda _url: connection)

    try:
        coordinator.complete(
            "database",
            RUN_ID,
            TOKEN,
            "b" * 64,
            VERIFICATION_ID,
            "periodic-controller",
        )
    except coordinator.RestoreDrillCoordinationError as exc:
        assert "lease expired" in str(exc)
    else:
        raise AssertionError("Expired restore drill completion was accepted")


def test_failure_requires_run_and_lease_identity(monkeypatch):
    connection = FakeConnection(("failed",))
    monkeypatch.setattr(coordinator, "_connect", lambda _url: connection)

    result = coordinator.fail(
        "database",
        RUN_ID,
        TOKEN,
        "isolated drill failed",
        "periodic-controller",
    )

    assert result["status"] == "failed"
    assert connection.cursor_instance.params == (
        RUN_ID,
        TOKEN,
        "isolated drill failed",
        "periodic-controller",
    )
