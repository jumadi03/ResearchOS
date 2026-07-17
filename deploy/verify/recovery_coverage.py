"""Report recovery coverage for one manifest-bound ResearchOS backup set."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
from typing import Any


REQUIRED_COMPONENTS = {
    "postgresql",
    "minio",
    "knowledge",
    "architecture",
    "configuration",
    "migration",
}
HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
COVERAGE_STATES = {"covered", "partial", "missing"}


class RecoveryCoverageError(ValueError):
    """Raised when a matrix, manifest, or backup artifact is unsafe."""


def _read_json(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RecoveryCoverageError(f"{path.name} is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise RecoveryCoverageError(f"{path.name} must contain a JSON object")
    return payload, sha256(raw).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_matrix(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    if matrix.get("schema_version") != "1.0":
        raise RecoveryCoverageError("Unsupported recovery matrix schema version")
    if matrix.get("matrix_id") != "researchos-recovery-coverage-v1":
        raise RecoveryCoverageError("Unknown recovery matrix identity")
    safety = matrix.get("safety")
    if not isinstance(safety, dict) or safety != {
        "active_target_prohibited": True,
        "restore_execution_in_scope": False,
        "secret_values_prohibited": True,
    }:
        raise RecoveryCoverageError("Recovery matrix safety contract is invalid")
    components = matrix.get("components")
    if not isinstance(components, list):
        raise RecoveryCoverageError("Recovery matrix components must be an array")
    by_name: dict[str, dict[str, Any]] = {}
    for item in components:
        if not isinstance(item, dict) or not isinstance(item.get("component"), str):
            raise RecoveryCoverageError("Every recovery component must be an object with a name")
        name = item["component"]
        if name in by_name:
            raise RecoveryCoverageError(f"Duplicate recovery component: {name}")
        if item.get("required") is not True:
            raise RecoveryCoverageError(f"Recovery component is not required: {name}")
        if item.get("coverage") not in COVERAGE_STATES:
            raise RecoveryCoverageError(f"Invalid coverage state for {name}")
        if not isinstance(item.get("canonical_authority"), str) or not item["canonical_authority"].strip():
            raise RecoveryCoverageError(f"Missing canonical authority for {name}")
        target = item.get("restore_target")
        if not isinstance(target, str) or "isolated" not in target.lower():
            raise RecoveryCoverageError(f"Restore target is not explicitly isolated for {name}")
        checks = item.get("verification_checks")
        if not isinstance(checks, list) or not checks or not all(
            isinstance(check, str) and check.strip() for check in checks
        ):
            raise RecoveryCoverageError(f"Verification checks are incomplete for {name}")
        backup_component = item.get("backup_component")
        if item["coverage"] == "covered":
            if not isinstance(backup_component, str) or not backup_component:
                raise RecoveryCoverageError(f"Covered component lacks backup binding: {name}")
        elif backup_component is not None:
            raise RecoveryCoverageError(f"Uncovered component claims a backup binding: {name}")
        by_name[name] = item
    if set(by_name) != REQUIRED_COMPONENTS:
        missing = sorted(REQUIRED_COMPONENTS - set(by_name))
        unknown = sorted(set(by_name) - REQUIRED_COMPONENTS)
        raise RecoveryCoverageError(
            f"Recovery component set is invalid; missing={missing}, unknown={unknown}"
        )
    configuration = by_name["configuration"]
    if configuration.get("secret_policy") != "structure_only_no_secret_values":
        raise RecoveryCoverageError("Configuration recovery could expose secret values")
    return [by_name[name] for name in sorted(by_name)]


def _validate_manifest(manifest: dict[str, Any]) -> dict[str, dict[str, str]]:
    if manifest.get("schema_version") != "1.0":
        raise RecoveryCoverageError("Unsupported backup manifest schema version")
    stamp = manifest.get("backup_stamp")
    if not isinstance(stamp, str) or not re.fullmatch(r"\d{8}T\d{6}Z", stamp):
        raise RecoveryCoverageError("Backup manifest stamp is invalid")
    components = manifest.get("components")
    if not isinstance(components, list) or not components:
        raise RecoveryCoverageError("Backup manifest components must be a non-empty array")
    by_name: dict[str, dict[str, str]] = {}
    for item in components:
        if not isinstance(item, dict) or set(item) != {"name", "file", "sha256"}:
            raise RecoveryCoverageError("Backup component contract is invalid")
        name, filename, digest = item["name"], item["file"], item["sha256"]
        if not all(isinstance(value, str) for value in (name, filename, digest)):
            raise RecoveryCoverageError("Backup component fields must be strings")
        if name in by_name:
            raise RecoveryCoverageError(f"Duplicate backup component: {name}")
        if Path(filename).name != filename or Path(filename).is_absolute():
            raise RecoveryCoverageError(f"Unsafe backup artifact path: {filename}")
        if not HASH_PATTERN.fullmatch(digest):
            raise RecoveryCoverageError(f"Invalid artifact hash for {name}")
        by_name[name] = item
    return by_name


def assess_recovery_coverage(
    matrix_path: Path,
    manifest_path: Path,
    backup_root: Path,
) -> dict[str, Any]:
    matrix, matrix_hash = _read_json(matrix_path)
    manifest, manifest_hash = _read_json(manifest_path)
    matrix_components = _validate_matrix(matrix)
    manifest_components = _validate_manifest(manifest)
    declared_covered = {
        item["backup_component"]
        for item in matrix_components
        if item["coverage"] == "covered"
    }
    if set(manifest_components) != declared_covered:
        raise RecoveryCoverageError(
            "Backup manifest components do not match the recovery coverage contract"
        )

    results = []
    for item in matrix_components:
        binding = item["backup_component"]
        artifact_present = False
        artifact_hash_verified = False
        if binding:
            manifest_item = manifest_components[binding]
            artifact = backup_root / manifest_item["file"]
            if artifact.is_symlink():
                raise RecoveryCoverageError(
                    f"Backup artifact cannot be a symbolic link: {manifest_item['file']}"
                )
            artifact_present = artifact.is_file()
            if not artifact_present:
                raise RecoveryCoverageError(f"Backup artifact is missing: {manifest_item['file']}")
            artifact_hash_verified = (
                _sha256_file(artifact) == manifest_item["sha256"]
            )
            if not artifact_hash_verified:
                raise RecoveryCoverageError(f"Backup artifact hash mismatch: {binding}")
        results.append(
            {
                "component": item["component"],
                "contract_coverage": item["coverage"],
                "artifact_present": artifact_present,
                "artifact_hash_verified": artifact_hash_verified,
                "restore_target": item["restore_target"],
                "verification_checks": item["verification_checks"],
                "ready_for_restore_drill": (
                    item["coverage"] == "covered"
                    and artifact_present
                    and artifact_hash_verified
                ),
            }
        )

    complete = all(item["ready_for_restore_drill"] for item in results)
    return {
        "schema_version": "1.0",
        "status": "COMPLETE" if complete else "INCOMPLETE",
        "matrix_id": matrix["matrix_id"],
        "matrix_hash": matrix_hash,
        "backup_stamp": manifest["backup_stamp"],
        "manifest_hash": manifest_hash,
        "restore_executed": False,
        "active_target_touched": False,
        "components": results,
        "missing_or_partial": [
            item["component"]
            for item in results
            if item["contract_coverage"] != "covered"
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--backup-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    try:
        report = assess_recovery_coverage(
            args.matrix.resolve(),
            args.manifest.resolve(),
            args.backup_root.resolve(),
        )
    except (OSError, RecoveryCoverageError) as exc:
        print(f"recovery coverage: failed: {exc}", file=sys.stderr)
        return 1
    rendered = json.dumps(report, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    else:
        print(rendered, end="")
    if args.require_complete and report["status"] != "COMPLETE":
        print("recovery coverage: incomplete", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
