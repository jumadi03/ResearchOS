from datetime import datetime, timezone
import json
from pathlib import Path

from app.product.operational_status import build_operational_status


def test_operational_status_projects_only_safe_read_only_facts(tmp_path: Path) -> None:
    monitor = tmp_path / "state" / "health.json"
    monitor.parent.mkdir()
    monitor.write_text(json.dumps({
        "status": "passed",
        "checked_at": "2026-07-20T04:34:22+00:00",
        "checks": [
            {"name": "api", "status": "passed"},
            {"name": "minio", "status": "passed"},
            {
                "name": "postgresql", "status": "passed",
                "schema_version": 41, "canonical_object_count": 325,
            },
        ],
        "failures": [],
    }), encoding="utf-8")
    backups = tmp_path / "backups"
    backups.mkdir()
    (backups / "backup-set-20260720T031629Z.json").write_text(
        "{}", encoding="utf-8"
    )
    revision = tmp_path / "DEPLOYED_COMMIT"
    revision.write_text("7381412014d7e4c3ea369b9971e49a76a6f50238\n", encoding="utf-8")

    result = build_operational_status(
        monitor_path=monitor,
        backup_root=backups,
        deployed_commit_path=revision,
        disk_root=tmp_path,
        now=datetime(2026, 7, 20, 5, 0, tzinfo=timezone.utc),
    )

    assert result["status"] == "passed"
    assert result["backup"]["stamp"] == "20260720T031629Z"
    assert result["deployment"]["revision"].startswith("7381412")
    assert result["monitor"]["checks"][2]["canonical_object_count"] == 325
    serialized = json.dumps(result)
    assert "password" not in serialized
    assert "token" not in serialized


def test_operational_status_fails_to_attention_when_evidence_is_missing(
    tmp_path: Path,
) -> None:
    result = build_operational_status(
        monitor_path=tmp_path / "missing.json",
        backup_root=tmp_path / "missing-backups",
        deployed_commit_path=tmp_path / "missing-commit",
        disk_root=tmp_path,
    )

    assert result["status"] == "attention"
    assert result["monitor"]["status"] == "unavailable"
    assert result["backup"]["status"] == "unavailable"
    assert result["deployment"]["revision"] is None
