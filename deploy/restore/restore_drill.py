"""Execute one manifest-bound ResearchOS restore drill against fixed isolated targets."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
from typing import Any, Callable

from recovery_coverage import RecoveryCoverageError, assess_recovery_coverage
try:
    from restore_attestation import sign_report
except ModuleNotFoundError:  # Local contract tests use the installed application package.
    from app.product.restore_attestation import sign_report


COMPONENTS = {
    "architecture",
    "configuration",
    "knowledge",
    "migration",
    "minio",
    "postgresql",
}
POSTGRES_HOST = "restore-postgres"
POSTGRES_ADMIN_DB = "postgres"
POSTGRES_DATABASE = "researchos_restore_drill"
POSTGRES_USER = "researchos_restore"
MINIO_ALIAS = "isolated"
MINIO_ENDPOINT = "http://restore-minio:9000"
MINIO_BUCKET = "researchos-restore-drill"
MINIO_USER = "researchos_restore"
MINIO_PASSWORD = "isolated-restore-drill-only"
PRIVATE_KEY_PATH = Path("/run/secrets/restore-attestation-private.pem")
Run = Callable[..., subprocess.CompletedProcess[str]]


class RestoreDrillError(RuntimeError):
    """Raised when an isolated restore or verification fails."""


def _validate_runtime_paths(
    matrix_path: Path,
    backup_root: Path,
    output_path: Path,
) -> None:
    if matrix_path != Path("/contract/recovery-coverage-v1.json"):
        raise RestoreDrillError("Recovery contract path is not fixed")
    if backup_root != Path("/backups"):
        raise RestoreDrillError("Backup root is not the fixed read-only mount")
    if output_path.parent != Path("/reports") or not re.fullmatch(
        r"restore-drill(?:-[A-Za-z0-9]+)*\.json",
        output_path.name,
    ):
        raise RestoreDrillError("Restore report path is unsafe")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_extract(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=False)
    seen: set[str] = set()
    with tarfile.open(archive, "r:gz") as bundle:
        for member in bundle.getmembers():
            normalized = member.name.removeprefix("./")
            if not normalized or normalized == ".":
                continue
            path = Path(normalized)
            if (
                path.is_absolute()
                or ".." in path.parts
                or member.issym()
                or member.islnk()
                or member.isdev()
                or not (member.isdir() or member.isfile())
            ):
                raise RestoreDrillError(f"Unsafe archive member: {member.name}")
            key = path.as_posix()
            if key in seen:
                raise RestoreDrillError(f"Duplicate archive member: {member.name}")
            seen.add(key)
            target = destination / path
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            source = bundle.extractfile(member)
            if source is None:
                raise RestoreDrillError(f"Unreadable archive member: {member.name}")
            with source, target.open("xb") as output:
                shutil.copyfileobj(source, output)


def _tree_manifest(root: Path) -> str:
    entries: list[str] = []
    hashes: list[str] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        if relative == ".researchos-tree-manifest.txt":
            continue
        if path.is_symlink() or not (path.is_dir() or path.is_file()):
            raise RestoreDrillError(f"Unsafe restored filesystem entry: {relative}")
        entries.append(f"entry {'d' if path.is_dir() else 'f'} {relative}")
        if path.is_file():
            hashes.append(f"{_sha256_file(path)}  ./{relative}")
    entries.sort()
    lines = entries + hashes
    return "\n".join(lines) + ("\n" if lines else "")


def _verify_tree(root: Path) -> dict[str, Any]:
    manifest = root / ".researchos-tree-manifest.txt"
    if not manifest.is_file() or manifest.is_symlink():
        raise RestoreDrillError("Filesystem archive lacks a safe tree manifest")
    if manifest.read_text(encoding="utf-8") != _tree_manifest(root):
        raise RestoreDrillError("Restored filesystem tree does not match its manifest")
    files = [
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path != manifest
    ]
    return {"tree_manifest_verified": True, "file_count": len(files)}


def _verify_configuration(root: Path) -> dict[str, Any]:
    result = _verify_tree(root)
    files = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name != ".researchos-tree-manifest.txt"
    }
    expected = {"compose.yaml", "stack.env.example", "recovery-coverage-v1.json"}
    if files != expected:
        raise RestoreDrillError("Configuration archive violates the non-secret allowlist")
    for line in (root / "stack.env.example").read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if re.search(r"(PASSWORD|TOKEN|SECRET|CREDENTIAL)", key, re.IGNORECASE):
            if value and "replace-with" not in value:
                raise RestoreDrillError(f"Configuration contains a secret-like value: {key}")
    json.loads((root / "recovery-coverage-v1.json").read_text(encoding="utf-8"))
    compose = (root / "compose.yaml").read_text(encoding="utf-8")
    if not re.search(r"(?m)^services:\s*$", compose) or not re.search(
        r"(?m)^  [a-z0-9][a-z0-9-]*:\s*$", compose
    ):
        raise RestoreDrillError("Compose reconstruction contract is invalid")
    result["allowlist_verified"] = True
    result["compose_contract_structurally_verified"] = True
    result["secret_values_absent"] = True
    return result


def _run(
    runner: Run,
    command: list[str],
    *,
    capture_output: bool = True,
) -> subprocess.CompletedProcess[str]:
    return runner(
        command,
        check=True,
        text=True,
        capture_output=capture_output,
    )


def _postgres_env_command(*args: str) -> list[str]:
    return [
        *args,
        "-h",
        POSTGRES_HOST,
        "-U",
        POSTGRES_USER,
    ]


def _restore_postgresql(
    dump: Path,
    migration_root: Path,
    runner: Run,
) -> dict[str, Any]:
    _run(
        runner,
        _postgres_env_command(
            "psql",
            "-d",
            POSTGRES_ADMIN_DB,
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            f'CREATE DATABASE "{POSTGRES_DATABASE}"',
        ),
    )
    _run(
        runner,
        _postgres_env_command(
            "pg_restore",
            "--exit-on-error",
            "--no-owner",
            "--no-privileges",
            "-d",
            POSTGRES_DATABASE,
            str(dump),
        ),
    )
    sql_files = sorted((migration_root / "sql").glob("*.sql"))
    if not sql_files:
        raise RestoreDrillError("Migration archive contains no SQL files")
    expected = {
        int(path.name.split("_", 1)[0]): (path.name, _sha256_file(path))
        for path in sql_files
    }
    ledger = _run(
        runner,
        _postgres_env_command(
            "psql",
            "-d",
            POSTGRES_DATABASE,
            "-At",
            "-F",
            "|",
            "-c",
            "SELECT version,filename,checksum_sha256 FROM schema_migrations ORDER BY version",
        ),
    ).stdout
    actual: dict[int, tuple[str, str]] = {}
    for line in ledger.splitlines():
        version, filename, checksum = line.split("|", 2)
        actual[int(version)] = (filename, checksum)
    if actual != expected:
        raise RestoreDrillError("Restored schema_migrations ledger does not match migration files")
    canonical_count = _run(
        runner,
        _postgres_env_command(
            "psql",
            "-d",
            POSTGRES_DATABASE,
            "-At",
            "-c",
            "SELECT count(*) FROM canonical_objects",
        ),
    ).stdout.strip()
    return {
        "database_created_by_executor": True,
        "pg_restore_completed": True,
        "schema_migrations_verified": True,
        "schema_version": max(actual),
        "canonical_object_count": int(canonical_count),
    }


def _restore_minio(root: Path, runner: Run) -> dict[str, Any]:
    object_manifest = root / ".researchos-object-manifest.jsonl"
    if not object_manifest.is_file() or object_manifest.is_symlink():
        raise RestoreDrillError("MinIO archive lacks its object manifest")
    object_manifest_hash = _sha256_file(object_manifest)
    object_manifest.unlink()
    local_objects = {
        path.relative_to(root).as_posix(): (path.stat().st_size, _sha256_file(path))
        for path in root.rglob("*")
        if path.is_file()
    }
    _run(
        runner,
        [
            "mc",
            "alias",
            "set",
            MINIO_ALIAS,
            MINIO_ENDPOINT,
            MINIO_USER,
            MINIO_PASSWORD,
            "--api",
            "S3v4",
        ],
    )
    _run(runner, ["mc", "mb", "--ignore-existing", f"{MINIO_ALIAS}/{MINIO_BUCKET}"])
    _run(
        runner,
        ["mc", "mirror", "--overwrite", "--remove", str(root), f"{MINIO_ALIAS}/{MINIO_BUCKET}"],
    )
    for name, (size, digest) in local_objects.items():
        stat = _run(
            runner,
            ["mc", "stat", "--json", f"{MINIO_ALIAS}/{MINIO_BUCKET}/{name}"],
        ).stdout
        payload = json.loads(stat)
        if payload.get("size") != size:
            raise RestoreDrillError(f"Restored MinIO object size mismatch: {name}")
        restored = runner(
            ["mc", "cat", f"{MINIO_ALIAS}/{MINIO_BUCKET}/{name}"],
            check=True,
            capture_output=True,
        ).stdout
        if not isinstance(restored, bytes) or sha256(restored).hexdigest() != digest:
            raise RestoreDrillError(f"Restored MinIO object hash mismatch: {name}")
    return {
        "bucket_created_by_executor": True,
        "object_manifest_hash": object_manifest_hash,
        "object_count": len(local_objects),
        "object_sizes_verified": True,
        "object_hashes_verified": True,
    }


def _cleanup(runner: Run) -> bool:
    ok = True
    for command in (
        _postgres_env_command(
            "psql",
            "-d",
            POSTGRES_ADMIN_DB,
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            (
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                f"WHERE datname='{POSTGRES_DATABASE}'"
            ),
        ),
        _postgres_env_command(
            "psql",
            "-d",
            POSTGRES_ADMIN_DB,
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            f'DROP DATABASE IF EXISTS "{POSTGRES_DATABASE}"',
        ),
        ["mc", "rm", "--recursive", "--force", f"{MINIO_ALIAS}/{MINIO_BUCKET}"],
    ):
        try:
            _run(runner, command)
        except (OSError, subprocess.CalledProcessError):
            ok = False
    return ok


def execute_restore_drill(
    matrix_path: Path,
    manifest_path: Path,
    backup_root: Path,
    *,
    actor: str = "researchos-isolated-restore-drill",
    runner: Run = subprocess.run,
) -> dict[str, Any]:
    started_at = _utcnow()
    restore_started = False
    checks: list[dict[str, Any]] = []
    outcome = "blocked"
    error: str | None = None
    cleanup_verified = True
    manifest_hash = ""
    backup_stamp = ""
    try:
        if manifest_path.parent.resolve() != backup_root.resolve():
            raise RestoreDrillError("Manifest must be located directly in the read-only backup root")
        if not re.fullmatch(r"backup-set-\d{8}T\d{6}Z\.json", manifest_path.name):
            raise RestoreDrillError("Manifest filename is not canonical")
        coverage = assess_recovery_coverage(matrix_path, manifest_path, backup_root)
        if coverage["status"] != "COMPLETE":
            raise RestoreDrillError("Backup set is not complete")
        manifest_hash = coverage["manifest_hash"]
        backup_stamp = coverage["backup_stamp"]
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        artifacts = {item["name"]: backup_root / item["file"] for item in manifest["components"]}
        if set(artifacts) != COMPONENTS:
            raise RestoreDrillError("Restore component set is not canonical")
        restore_started = True
        with tempfile.TemporaryDirectory(prefix="researchos-restore-", dir="/work") as raw:
            work = Path(raw)
            restored: dict[str, Path] = {}
            for name in ("knowledge", "architecture", "configuration", "migration", "minio"):
                target = work / name
                _safe_extract(artifacts[name], target)
                restored[name] = target
            for name in ("knowledge", "architecture"):
                checks.append({"component": name, **_verify_tree(restored[name])})
            checks.append(
                {"component": "configuration", **_verify_configuration(restored["configuration"])}
            )
            migration_check = _verify_tree(restored["migration"])
            if not (restored["migration"] / "migrate.sh").is_file():
                raise RestoreDrillError("Migration runner is missing")
            checks.append({"component": "migration", **migration_check})
            checks.append(
                {
                    "component": "postgresql",
                    **_restore_postgresql(artifacts["postgresql"], restored["migration"], runner),
                }
            )
            checks.append({"component": "minio", **_restore_minio(restored["minio"], runner)})
        outcome = "verified"
    except (
        OSError,
        ValueError,
        RestoreDrillError,
        RecoveryCoverageError,
        tarfile.TarError,
        subprocess.CalledProcessError,
    ) as exc:
        outcome = "failed" if restore_started else "blocked"
        error = str(exc)
    finally:
        if restore_started:
            cleanup_verified = _cleanup(runner)
            if not cleanup_verified:
                outcome = "failed"
                error = "Isolated restore target cleanup failed"
    completed_at = _utcnow()
    report: dict[str, Any] = {
        "schema_version": "1.0",
        "drill_id": f"restore-drill:{backup_stamp or 'blocked'}",
        "backup_stamp": backup_stamp or None,
        "manifest_hash": manifest_hash or None,
        "target_kind": "isolated",
        "target_identifier": f"{POSTGRES_DATABASE}+{MINIO_BUCKET}",
        "components": sorted(COMPONENTS),
        "outcome": outcome,
        "checks": checks,
        "actor": actor,
        "started_at": started_at,
        "completed_at": completed_at,
        "restore_executed": restore_started,
        "active_target_touched": False,
        "cleanup_verified": cleanup_verified,
        "ledger_written": False,
        "error": error,
    }
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
    report["content_hash"] = sha256(canonical).hexdigest()
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--backup-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    matrix_path = args.matrix.resolve()
    backup_root = args.backup_root.resolve()
    output_path = args.output.resolve()
    try:
        _validate_runtime_paths(matrix_path, backup_root, output_path)
    except RestoreDrillError as exc:
        parser.error(str(exc))
    report = execute_restore_drill(
        matrix_path,
        args.manifest.resolve(),
        backup_root,
    )
    if report["outcome"] == "verified":
        try:
            report = sign_report(report, PRIVATE_KEY_PATH.read_bytes())
        except (OSError, ValueError) as exc:
            report["outcome"] = "failed"
            report["error"] = f"Restore attestation failed: {exc}"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return 0 if report["outcome"] == "verified" else 1


if __name__ == "__main__":
    raise SystemExit(main())
