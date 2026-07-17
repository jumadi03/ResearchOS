from copy import deepcopy
from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "deploy/verify/recovery_coverage.py"
MATRIX = ROOT / "deploy/backup/recovery-coverage-v1.json"
SPEC = spec_from_file_location("researchos_recovery_coverage", SCRIPT)
assert SPEC and SPEC.loader
coverage = module_from_spec(SPEC)
SPEC.loader.exec_module(coverage)


def write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def backup_fixture(tmp_path: Path):
    components = []
    for name in ("knowledge", "minio", "postgresql"):
        filename = f"{name}.archive"
        content = f"{name}-content".encode()
        (tmp_path / filename).write_bytes(content)
        components.append(
            {
                "name": name,
                "file": filename,
                "sha256": sha256(content).hexdigest(),
            }
        )
    manifest = {
        "schema_version": "1.0",
        "backup_stamp": "20260717T120752Z",
        "components": components,
    }
    manifest_path = tmp_path / "backup-set.json"
    write_json(manifest_path, manifest)
    return manifest_path, manifest


def test_matrix_is_explicit_safe_and_complete_as_an_inventory():
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))

    assert matrix["safety"] == {
        "active_target_prohibited": True,
        "restore_execution_in_scope": False,
        "secret_values_prohibited": True,
    }
    assert {item["component"] for item in matrix["components"]} == {
        "postgresql",
        "minio",
        "knowledge",
        "architecture",
        "configuration",
        "migration",
    }
    assert all(item["required"] is True for item in matrix["components"])
    assert all("isolated" in item["restore_target"].lower() for item in matrix["components"])


def test_current_backup_set_reports_known_gaps_without_claiming_restore(tmp_path):
    manifest_path, _ = backup_fixture(tmp_path)

    report = coverage.assess_recovery_coverage(MATRIX, manifest_path, tmp_path)

    assert report["status"] == "INCOMPLETE"
    assert report["restore_executed"] is False
    assert report["active_target_touched"] is False
    assert report["missing_or_partial"] == [
        "architecture",
        "configuration",
        "migration",
    ]
    readiness = {
        item["component"]: item["ready_for_restore_drill"]
        for item in report["components"]
    }
    assert readiness == {
        "architecture": False,
        "configuration": False,
        "knowledge": True,
        "migration": False,
        "minio": True,
        "postgresql": True,
    }


def test_tampered_backup_artifact_fails_closed(tmp_path):
    manifest_path, _ = backup_fixture(tmp_path)
    (tmp_path / "postgresql.archive").write_text("tampered", encoding="utf-8")

    with pytest.raises(coverage.RecoveryCoverageError, match="hash mismatch"):
        coverage.assess_recovery_coverage(MATRIX, manifest_path, tmp_path)


def test_manifest_path_traversal_is_rejected(tmp_path):
    manifest_path, manifest = backup_fixture(tmp_path)
    manifest["components"][0]["file"] = "../knowledge.archive"
    write_json(manifest_path, manifest)

    with pytest.raises(coverage.RecoveryCoverageError, match="Unsafe"):
        coverage.assess_recovery_coverage(MATRIX, manifest_path, tmp_path)


def test_symbolic_link_backup_artifact_is_rejected(tmp_path):
    manifest_path, _ = backup_fixture(tmp_path)
    artifact = tmp_path / "knowledge.archive"
    target = tmp_path / "outside.archive"
    target.write_bytes(artifact.read_bytes())
    artifact.unlink()
    try:
        artifact.symlink_to(target)
    except OSError:
        pytest.skip("Symbolic links are unavailable in this test environment")

    with pytest.raises(coverage.RecoveryCoverageError, match="symbolic link"):
        coverage.assess_recovery_coverage(MATRIX, manifest_path, tmp_path)


def test_unknown_manifest_component_is_rejected(tmp_path):
    manifest_path, manifest = backup_fixture(tmp_path)
    content = b"unexpected"
    (tmp_path / "unexpected.archive").write_bytes(content)
    manifest["components"].append(
        {
            "name": "unexpected",
            "file": "unexpected.archive",
            "sha256": sha256(content).hexdigest(),
        }
    )
    write_json(manifest_path, manifest)

    with pytest.raises(coverage.RecoveryCoverageError, match="do not match"):
        coverage.assess_recovery_coverage(MATRIX, manifest_path, tmp_path)


def test_configuration_secret_policy_cannot_be_weakened(tmp_path):
    manifest_path, _ = backup_fixture(tmp_path)
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    unsafe = deepcopy(matrix)
    configuration = next(
        item for item in unsafe["components"] if item["component"] == "configuration"
    )
    configuration["secret_policy"] = "include_values"
    unsafe_path = tmp_path / "unsafe-matrix.json"
    write_json(unsafe_path, unsafe)

    with pytest.raises(coverage.RecoveryCoverageError, match="secret"):
        coverage.assess_recovery_coverage(unsafe_path, manifest_path, tmp_path)


def test_covered_component_requires_an_artifact_binding(tmp_path):
    manifest_path, _ = backup_fixture(tmp_path)
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    unsafe = deepcopy(matrix)
    architecture = next(
        item for item in unsafe["components"] if item["component"] == "architecture"
    )
    architecture["coverage"] = "covered"
    unsafe_path = tmp_path / "invalid-matrix.json"
    write_json(unsafe_path, unsafe)

    with pytest.raises(coverage.RecoveryCoverageError, match="lacks backup binding"):
        coverage.assess_recovery_coverage(unsafe_path, manifest_path, tmp_path)
