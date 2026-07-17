from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from uuid import UUID


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "deploy/postgres/init/032_restore_drill_schedule_gate.sql"
COORDINATOR = ROOT / "deploy/restore/coordinate_restore_drill.py"
SPEC = spec_from_file_location("researchos_restore_schedule_coordinator", COORDINATOR)
assert SPEC and SPEC.loader
coordinator = module_from_spec(SPEC)
SPEC.loader.exec_module(coordinator)

RUN_ID = UUID("11111111-1111-1111-1111-111111111111")
TOKEN = UUID("22222222-2222-2222-2222-222222222222")
BACKUP_ID = UUID("33333333-3333-3333-3333-333333333333")


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


def test_schema_32_defines_fail_closed_canonical_due_gate():
    contract = MIGRATION.read_text(encoding="utf-8")

    assert "restore_drill_schedule_state" in contract
    assert "restore_drill_schedule_events" in contract
    assert "'paused',604800" in contract
    assert "acquire_due_restore_drill_lease" in contract
    assert "configure_restore_drill_schedule" in contract
    assert "set_restore_drill_schedule_status" in contract
    assert "restore_drill_schedule_events_immutable" in contract
    assert "restore_drill_schedule_state_guard" in contract
    assert "Host triggers request due decisions but cannot choose scheduled time" in contract
    assert "p_cadence_seconds BETWEEN" not in contract
    assert "cadence_seconds BETWEEN 86400 AND 2678400" in contract
    assert "pending_run_id" in contract
    assert "slot_expired" in contract


def test_due_acquisition_returns_server_schedule_and_backup(monkeypatch):
    due = datetime(2026, 7, 18, 1, 0, tzinfo=timezone.utc)
    expires = datetime(2026, 7, 18, 3, 0, tzinfo=timezone.utc)
    connection = FakeConnection(
        (
            "running",
            due,
            RUN_ID,
            TOKEN,
            BACKUP_ID,
            "20260718T000000Z",
            "a" * 64,
            "backup-set-20260718T000000Z.json",
            expires,
        )
    )
    monkeypatch.setattr(coordinator, "_connect", lambda _url: connection)

    receipt = coordinator.acquire_due("database", "host-trigger", 7200)

    assert receipt["status"] == "running"
    assert receipt["run_id"] == str(RUN_ID)
    assert receipt["manifest_filename"] == "backup-set-20260718T000000Z.json"
    assert connection.cursor_instance.params == ("host-trigger", 7200)


def test_not_due_and_paused_decisions_disclose_no_lease(monkeypatch):
    due = datetime(2026, 7, 25, 1, 0, tzinfo=timezone.utc)
    for status in ("not_due", "paused"):
        connection = FakeConnection(
            (status, due, None, None, None, None, None, None, None)
        )
        monkeypatch.setattr(coordinator, "_connect", lambda _url: connection)

        receipt = coordinator.acquire_due("database", "host-trigger", 7200)

        assert receipt == {"status": status, "next_due_at": due.isoformat()}


def test_schedule_changes_require_actor_and_rationale(monkeypatch):
    configured = FakeConnection((2,))
    monkeypatch.setattr(coordinator, "_connect", lambda _url: configured)
    assert coordinator.configure_schedule(
        "database", 604800, "operator", "weekly restore proof"
    ) == {"status": "configured", "revision": 2}
    assert configured.cursor_instance.params == (
        604800,
        "operator",
        "weekly restore proof",
    )

    paused = FakeConnection(("paused",))
    monkeypatch.setattr(coordinator, "_connect", lambda _url: paused)
    assert coordinator.transition_schedule(
        "database", "paused", "operator", "maintenance window"
    ) == {"status": "paused"}
    assert paused.cursor_instance.params == (
        "paused",
        "operator",
        "maintenance window",
    )
