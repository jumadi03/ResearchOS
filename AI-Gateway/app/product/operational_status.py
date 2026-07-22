"""Read-only operational status projection for authenticated workspace users."""

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from typing import Any


def _read_monitor(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError, TypeError):
        return {"status": "unavailable", "checked_at": None, "checks": []}
    if not isinstance(payload, dict):
        return {"status": "unavailable", "checked_at": None, "checks": []}
    return {
        "status": str(payload.get("status", "unavailable")),
        "checked_at": payload.get("checked_at"),
        "checks": payload.get("checks") if isinstance(payload.get("checks"), list) else [],
    }


def _latest_backup(root: Path) -> dict[str, Any]:
    manifests = sorted(
        [*root.glob("backup-set-*.json"), *root.glob("*/backup-set-*.json")],
        key=lambda path: path.name,
        reverse=True,
    )
    if not manifests:
        return {"status": "unavailable", "stamp": None}
    name = manifests[0].name
    return {
        "status": "available",
        "stamp": name.removeprefix("backup-set-").removesuffix(".json"),
    }


def _deployment_revision(path: Path) -> str | None:
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return value if value and len(value) <= 128 else None


def build_operational_status(
    *,
    monitor_path: Path,
    backup_root: Path,
    deployed_commit_path: Path,
    disk_root: Path = Path("/"),
    now: datetime | None = None,
) -> dict[str, Any]:
    checked_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    monitor = _read_monitor(monitor_path)
    disk = shutil.disk_usage(disk_root)
    used_percent = round((disk.used / disk.total) * 100, 1) if disk.total else 0.0
    backup = _latest_backup(backup_root)
    revision = _deployment_revision(deployed_commit_path)
    overall = (
        "passed"
        if monitor["status"] == "passed" and backup["status"] == "available"
        and revision is not None and used_percent < 85
        else "attention"
    )
    return {
        "schema_version": "1.0",
        "status": overall,
        "checked_at": checked_at.isoformat(),
        "monitor": monitor,
        "backup": backup,
        "disk": {
            "used_percent": used_percent,
            "available_bytes": disk.free,
            "threshold_percent": 85,
        },
        "deployment": {"revision": revision},
    }
