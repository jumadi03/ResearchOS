from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "deploy/restore/restore_drill.py"
COMPOSE = ROOT / "deploy/restore/compose.restore-drill.yaml"
BACKUP = ROOT / "deploy/backup/backup.sh"
sys.path.insert(0, str(ROOT / "deploy/verify"))
SPEC = spec_from_file_location("researchos_restore_drill", SCRIPT)
assert SPEC and SPEC.loader
restore = module_from_spec(SPEC)
SPEC.loader.exec_module(restore)


def _archive(path: Path, members: dict[str, bytes]) -> None:
    with tarfile.open(path, "w:gz") as bundle:
        for name, content in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(content)
            bundle.addfile(info, io.BytesIO(content))


def test_backup_snapshot_declares_copied_manifest_in_the_correct_function():
    script = BACKUP.read_text(encoding="utf-8")
    tree = script.split("snapshot_tree() {", 1)[1].split("archive_tree() {", 1)[0]
    minio = script.split("snapshot_minio() {", 1)[1].split("verify_archive() {", 1)[0]

    assert "local before copied after attempt" in tree
    assert 'copied="$(mktemp)"' in tree
    assert "local before copied after attempt" not in minio


def test_restore_runtime_has_no_route_or_identifier_for_active_targets():
    compose = COMPOSE.read_text(encoding="utf-8")

    assert "internal: true" in compose
    assert "researchos_backup_data:/backups:ro" in compose
    assert "tmpfs:" in compose
    assert "postgres_data" not in compose
    assert "minio_data" not in compose
    assert "stack.env" not in compose
    assert "\n  postgres:" not in compose
    assert "\n  minio:" not in compose


def test_runtime_paths_reject_report_traversal_and_noncanonical_mounts():
    with pytest.raises(restore.RestoreDrillError, match="report path"):
        restore._validate_runtime_paths(
            Path("/contract/recovery-coverage-v1.json"),
            Path("/backups"),
            Path("/reports/../restore_drill.py"),
        )
    with pytest.raises(restore.RestoreDrillError, match="Backup root"):
        restore._validate_runtime_paths(
            Path("/contract/recovery-coverage-v1.json"),
            Path("/active-backups"),
            Path("/reports/restore-drill-report.json"),
        )


def test_unsafe_archive_members_are_rejected(tmp_path):
    archive = tmp_path / "unsafe.tar.gz"
    _archive(archive, {"../outside": b"unsafe"})

    with pytest.raises(restore.RestoreDrillError, match="Unsafe"):
        restore._safe_extract(archive, tmp_path / "output")


def test_archive_links_are_rejected(tmp_path):
    archive = tmp_path / "link.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        link = tarfile.TarInfo("linked")
        link.type = tarfile.SYMTYPE
        link.linkname = "outside"
        bundle.addfile(link)

    with pytest.raises(restore.RestoreDrillError, match="Unsafe"):
        restore._safe_extract(archive, tmp_path / "output")


def test_tree_manifest_detects_tampered_restored_content(tmp_path):
    root = tmp_path / "tree"
    root.mkdir()
    (root / "data.txt").write_text("changed", encoding="utf-8")
    (root / ".researchos-tree-manifest.txt").write_text(
        f"entry f data.txt\n{sha256(b'original').hexdigest()}  ./data.txt\n",
        encoding="utf-8",
    )

    with pytest.raises(restore.RestoreDrillError, match="does not match"):
        restore._verify_tree(root)


def test_cleanup_uses_only_fixed_executor_owned_targets():
    commands: list[list[str]] = []

    def runner(command, **kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    assert restore._cleanup(runner) is True
    rendered = "\n".join(" ".join(command) for command in commands)
    assert restore.POSTGRES_DATABASE in rendered
    assert restore.MINIO_BUCKET in rendered
    assert "researchos " not in rendered


def test_blocked_preflight_never_starts_restore_or_writes_ledger(tmp_path):
    matrix = tmp_path / "matrix.json"
    manifest = tmp_path / "backup-set-20260717T120752Z.json"
    matrix.write_text("{}", encoding="utf-8")
    manifest.write_text("{}", encoding="utf-8")

    report = restore.execute_restore_drill(matrix, manifest, tmp_path)

    assert report["outcome"] == "blocked"
    assert report["restore_executed"] is False
    assert report["active_target_touched"] is False
    assert report["ledger_written"] is False
    assert len(report["content_hash"]) == 64


def test_report_contract_contains_full_attributable_provenance(tmp_path):
    matrix = tmp_path / "matrix.json"
    manifest = tmp_path / "backup-set-20260717T120752Z.json"
    matrix.write_text("{}", encoding="utf-8")
    manifest.write_text("{}", encoding="utf-8")

    report = restore.execute_restore_drill(matrix, manifest, tmp_path)

    assert report["target_kind"] == "isolated"
    assert report["target_identifier"] == (
        f"{restore.POSTGRES_DATABASE}+{restore.MINIO_BUCKET}"
    )
    assert report["actor"] == "researchos-isolated-restore-drill"
    assert report["components"] == sorted(restore.COMPONENTS)
    assert report["started_at"]
    assert report["completed_at"]
