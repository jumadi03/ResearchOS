import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "Scripts/restore_drill_task.ps1"


@pytest.mark.skipif(
    sys.platform != "win32" or shutil.which("powershell") is None,
    reason="Windows PowerShell contract execution",
)
def test_plan_is_safe_deterministic_and_applies_no_changes():
    completed = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-Action",
            "Plan",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    receipt = json.loads(completed.stdout)

    assert receipt["action"] == "plan"
    assert receipt["changes_applied"] is False
    assert receipt["initial_task_state"] == "disabled"
    assert receipt["trigger_interval_minutes"] == 60
    assert receipt["database_schedule_authority"] is True
    assert receipt["logon_type"] == "interactive"
    assert receipt["run_level"] == "limited"
    assert receipt["executable"].endswith(
        r"AI-Gateway\.venv\Scripts\python.exe"
    )
    assert "--scheduled" in receipt["arguments"]
    assert "--lease-seconds 7200" in receipt["arguments"]


def test_task_contract_is_fixed_least_privilege_and_fail_closed():
    source = SCRIPT.read_text(encoding="utf-8")

    assert 'TaskName = "ResearchOS Canonical Restore Drill Trigger"' in source
    assert 'TaskPath = "\\ResearchOS\\"' in source
    assert "-LogonType Interactive" in source
    assert "-RunLevel Limited" in source
    assert "-MultipleInstances IgnoreNew" in source
    assert "-ExecutionTimeLimit (New-TimeSpan -Hours 3)" in source
    assert "Disable-ScheduledTask" in source
    assert "already exists; inspect or remove it first" in source
    assert 'if (-not $ConfirmRemoval)' in source
    assert "schedule_data_preserved = $true" in source
    assert "restore_evidence_preserved = $true" in source


def test_task_contract_contains_no_secret_or_mutable_authority_input():
    source = SCRIPT.read_text(encoding="utf-8")

    for prohibited in (
        "Password",
        "DATABASE_URL",
        "stack.env",
        "private/",
        "private\\",
        "--target",
        "--manifest",
        "--report",
        "--database-url",
        "--lease-token",
        "RunLevel Highest",
    ):
        assert prohibited not in source


@pytest.mark.skipif(
    sys.platform != "win32" or shutil.which("powershell") is None,
    reason="Windows PowerShell contract execution",
)
def test_status_is_read_only_for_any_external_task_state():
    completed = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(SCRIPT),
            "-Action",
            "Status",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    receipt = json.loads(completed.stdout)

    assert receipt["action"] == "status"
    assert isinstance(receipt["installed"], bool)
    assert receipt["task_name"] == "ResearchOS Canonical Restore Drill Trigger"
    assert receipt["task_path"] == "\\ResearchOS\\"
