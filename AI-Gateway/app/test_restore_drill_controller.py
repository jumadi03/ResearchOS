import json
import subprocess
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
CONTROLLER = ROOT / "deploy/restore/run_restore_drill_controller.py"
SPEC = spec_from_file_location("researchos_restore_drill_controller", CONTROLLER)
assert SPEC and SPEC.loader
controller = module_from_spec(SPEC)
SPEC.loader.exec_module(controller)

LEASE = {
    "status": "running",
    "run_id": "11111111-1111-1111-1111-111111111111",
    "lease_token": "22222222-2222-2222-2222-222222222222",
    "backup_id": "33333333-3333-3333-3333-333333333333",
    "manifest_filename": "backup-set-20260717T140000Z.json",
}
ADMISSION = {
    "status": "admitted",
    "verification_id": "44444444-4444-4444-4444-444444444444",
    "content_hash": "a" * 64,
}


def result(receipt: dict | None = None):
    return subprocess.CompletedProcess(
        [], 0, stdout=(json.dumps(receipt) + "\n") if receipt else "", stderr=""
    )


def test_controller_composes_only_canonical_fixed_boundaries(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(controller, "REPORT_ROOT", tmp_path)

    def run(command, *, cwd, environment=None):
        calls.append((command, cwd, environment))
        if "acquire" in command:
            return result(LEASE)
        if "compose.restore-drill.yaml" in command and "up" in command:
            report = tmp_path / LEASE["run_id"] / "restore-drill-report.json"
            report.write_text("{}\n", encoding="utf-8")
            return result()
        if "restore-admission" in command:
            return result(ADMISSION)
        if "complete" in command:
            return result({"status": "completed"})
        return result()

    receipt = controller.execute(
        owner="manual-operator", lease_seconds=7200, run_command=run
    )

    assert receipt["status"] == "completed"
    assert receipt["verification_id"] == ADMISSION["verification_id"]
    assert receipt["report_content_hash"] == ADMISSION["content_hash"]
    stages = [
        next(
            (
                action
                for action in (
                    "acquire", "up", "down", "restore-admission", "complete"
                )
                if action in call[0]
            ),
            None,
        )
        for call in calls
    ]
    assert stages == ["acquire", "up", "down", "restore-admission", "complete"]
    assert calls[1][2]["RESTORE_MANIFEST"] == LEASE["manifest_filename"]
    assert calls[1][2]["RESTORE_REPORT_DIR"] == str(tmp_path / LEASE["run_id"])
    assert ADMISSION["content_hash"] in calls[-1][0]
    assert ADMISSION["verification_id"] in calls[-1][0]


@pytest.mark.parametrize("failure_stage", ["drill", "admission", "completion"])
def test_every_post_lease_failure_closes_the_canonical_lease(
    monkeypatch, tmp_path, failure_stage
):
    calls = []
    monkeypatch.setattr(controller, "REPORT_ROOT", tmp_path)

    def run(command, *, cwd, environment=None):
        calls.append(command)
        if "acquire" in command:
            return result(LEASE)
        if "compose.restore-drill.yaml" in command and "up" in command:
            if failure_stage == "drill":
                raise subprocess.CalledProcessError(7, command)
            report = tmp_path / LEASE["run_id"] / "restore-drill-report.json"
            report.write_text("{}\n", encoding="utf-8")
            return result()
        if "restore-admission" in command and failure_stage == "admission":
            raise subprocess.CalledProcessError(8, command)
        if "restore-admission" in command:
            return result(ADMISSION)
        if "complete" in command and failure_stage == "completion":
            raise subprocess.CalledProcessError(9, command)
        return result({"status": "failed"})

    with pytest.raises(controller.RestoreDrillControllerError):
        controller.execute(owner="manual-operator", lease_seconds=7200, run_command=run)

    failure = calls[-1]
    assert "fail" in failure
    assert LEASE["run_id"] in failure
    assert LEASE["lease_token"] in failure
    assert not any("postgresql://" in part for part in failure)


def test_acquisition_failure_creates_no_failure_transition(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(controller, "REPORT_ROOT", tmp_path)

    def run(command, *, cwd, environment=None):
        calls.append(command)
        raise subprocess.CalledProcessError(5, command)

    with pytest.raises(controller.RestoreDrillControllerError):
        controller.execute(owner="manual-operator", lease_seconds=7200, run_command=run)

    assert len(calls) == 1
    assert "acquire" in calls[0]


@pytest.mark.parametrize(
    "field,value",
    [
        ("run_id", "../../outside"),
        ("lease_token", "not-a-uuid"),
        ("backup_id", "not-a-uuid"),
        ("manifest_filename", "../backup-set-20260717T140000Z.json"),
        ("status", "completed"),
    ],
)
def test_untrusted_lease_receipt_cannot_escape_canonical_bounds(
    monkeypatch, tmp_path, field, value
):
    calls = []
    monkeypatch.setattr(controller, "REPORT_ROOT", tmp_path)
    unsafe = {**LEASE, field: value}

    def run(command, *, cwd, environment=None):
        calls.append(command)
        return result(unsafe)

    with pytest.raises(controller.RestoreDrillControllerError):
        controller.execute(owner="manual-operator", lease_seconds=7200, run_command=run)

    assert len(calls) == 1
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "receipt",
    [
        {**ADMISSION, "status": "rejected"},
        {**ADMISSION, "verification_id": "not-a-uuid"},
        {**ADMISSION, "content_hash": "not-a-hash"},
    ],
)
def test_invalid_admission_receipt_fails_the_lease(
    monkeypatch, tmp_path, receipt
):
    calls = []
    monkeypatch.setattr(controller, "REPORT_ROOT", tmp_path)

    def run(command, *, cwd, environment=None):
        calls.append(command)
        if "acquire" in command:
            return result(LEASE)
        if "compose.restore-drill.yaml" in command and "up" in command:
            report = tmp_path / LEASE["run_id"] / "restore-drill-report.json"
            report.write_text("{}\n", encoding="utf-8")
            return result()
        if "restore-admission" in command:
            return result(receipt)
        return result({"status": "failed"})

    with pytest.raises(controller.RestoreDrillControllerError):
        controller.execute(owner="manual-operator", lease_seconds=7200, run_command=run)

    assert "fail" in calls[-1]


def test_cleanup_is_attempted_when_drill_fails(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(controller, "REPORT_ROOT", tmp_path)

    def run(command, *, cwd, environment=None):
        calls.append(command)
        if "acquire" in command:
            return result(LEASE)
        if "up" in command:
            raise subprocess.CalledProcessError(7, command)
        return result({"status": "failed"})

    with pytest.raises(controller.RestoreDrillControllerError):
        controller.execute(owner="manual-operator", lease_seconds=7200, run_command=run)

    assert any("down" in command for command in calls)


def test_operator_interrupt_attempts_cleanup_and_explicit_lease_failure(
    monkeypatch, tmp_path
):
    calls = []
    monkeypatch.setattr(controller, "REPORT_ROOT", tmp_path)

    def run(command, *, cwd, environment=None):
        calls.append(command)
        if "acquire" in command:
            return result(LEASE)
        if "up" in command:
            raise KeyboardInterrupt
        return result({"status": "failed"})

    with pytest.raises(KeyboardInterrupt):
        controller.execute(owner="manual-operator", lease_seconds=7200, run_command=run)

    assert any("down" in command for command in calls)
    assert "fail" in calls[-1]
    assert any("interrupted by the operator" in part for part in calls[-1])


def test_controller_is_host_only_and_does_not_accept_targets_or_secrets():
    source = CONTROLLER.read_text(encoding="utf-8")

    assert "shell=False" in source
    assert "--target" not in source
    assert "DATABASE_URL" not in source
    assert "private/" not in source
    assert "docker.sock" not in source
    assert "scheduler" not in source
    assert "subprocess.run" in source
