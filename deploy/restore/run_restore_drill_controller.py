"""Run the canonical restore-drill workflow from an operator-controlled host."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Callable
from uuid import UUID


class RestoreDrillControllerError(RuntimeError):
    """Raised when one canonical restore-drill stage fails."""


ROOT = Path(__file__).resolve().parents[2]
DEPLOY_ROOT = ROOT / "deploy"
RESTORE_ROOT = DEPLOY_ROOT / "restore"
REPORT_ROOT = RESTORE_ROOT / "reports"
ACTOR = "restore-drill-controller"
MANIFEST_PATTERN = re.compile(r"backup-set-\d{8}T\d{6}Z\.json")
HASH_PATTERN = re.compile(r"[0-9a-f]{64}")


def _json_receipt(output: str, stage: str) -> dict:
    for line in reversed(output.splitlines()):
        try:
            receipt = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(receipt, dict):
            return receipt
    raise RestoreDrillControllerError(f"{stage} returned no JSON receipt")


def _run(
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )


def _coordinator_command(action: str, arguments: list[str]) -> list[str]:
    return [
        "docker", "compose", "--env-file", "stack.env", "-f", "compose.yaml",
        "--profile", "restore-coordinator", "run", "--rm",
        "restore-coordinator", action, *arguments,
    ]


def _validated_lease(receipt: dict) -> dict:
    try:
        UUID(str(receipt["run_id"]))
        UUID(str(receipt["lease_token"]))
        UUID(str(receipt["backup_id"]))
        manifest_filename = str(receipt["manifest_filename"])
    except (KeyError, ValueError) as exc:
        raise RestoreDrillControllerError(
            "lease receipt has invalid canonical identity"
        ) from exc
    if receipt.get("status") != "running":
        raise RestoreDrillControllerError("lease receipt is not running")
    if MANIFEST_PATTERN.fullmatch(manifest_filename) is None:
        raise RestoreDrillControllerError(
            "lease receipt has unsafe manifest filename"
        )
    return receipt


def _validated_admission(receipt: dict) -> dict:
    try:
        UUID(str(receipt["verification_id"]))
        content_hash = str(receipt["content_hash"])
    except (KeyError, ValueError) as exc:
        raise RestoreDrillControllerError(
            "admission receipt has invalid canonical identity"
        ) from exc
    if receipt.get("status") != "admitted":
        raise RestoreDrillControllerError("restore evidence was not admitted")
    if HASH_PATTERN.fullmatch(content_hash) is None:
        raise RestoreDrillControllerError(
            "admission receipt has invalid report content hash"
        )
    return receipt


def _failure_reason(stage: str, exc: BaseException) -> str:
    if isinstance(exc, subprocess.CalledProcessError):
        return f"restore drill {stage} failed with exit code {exc.returncode}"
    if isinstance(exc, KeyboardInterrupt):
        return f"restore drill {stage} was interrupted by the operator"
    return f"restore drill {stage} failed: {type(exc).__name__}"


def _fail_lease(
    run_command: Callable[..., subprocess.CompletedProcess[str]],
    lease: dict,
    reason: str,
) -> None:
    run_command(
        _coordinator_command(
            "fail",
            [
                "--run-id", str(lease["run_id"]),
                "--lease-token", str(lease["lease_token"]),
                "--error", reason,
                "--actor", ACTOR,
            ],
        ),
        cwd=DEPLOY_ROOT,
    )


def execute(
    *,
    owner: str,
    lease_seconds: int,
    scheduled: bool = False,
    run_command: Callable[..., subprocess.CompletedProcess[str]] = _run,
) -> dict:
    lease: dict | None = None
    stage = "lease acquisition"
    try:
        acquired = run_command(
            _coordinator_command(
                "acquire-due" if scheduled else "acquire",
                ["--owner", owner, "--lease-seconds", str(lease_seconds)],
            ),
            cwd=DEPLOY_ROOT,
        )
        acquisition = _json_receipt(acquired.stdout, stage)
        if scheduled and acquisition.get("status") in {
            "paused", "not_due", "running"
        }:
            return acquisition
        lease = _validated_lease(acquisition)
        run_id = str(lease["run_id"])
        lease_token = str(lease["lease_token"])
        manifest_filename = str(lease["manifest_filename"])

        REPORT_ROOT.mkdir(parents=True, exist_ok=True)
        if REPORT_ROOT.is_symlink():
            raise RestoreDrillControllerError("restore report root must not be a link")
        report_directory = REPORT_ROOT / run_id
        if report_directory.exists():
            raise RestoreDrillControllerError(
                "run-specific restore report directory already exists"
            )
        report_directory.mkdir(parents=True)
        report_path = report_directory / "restore-drill-report.json"

        drill_environment = os.environ.copy()
        drill_environment.update(
            {
                "RESTORE_MANIFEST": manifest_filename,
                "RESTORE_REPORT_DIR": str(report_directory),
                "RESTORE_REPORT": report_path.name,
            }
        )
        stage = "isolated execution"
        try:
            run_command(
                [
                    "docker", "compose", "-f", "compose.restore-drill.yaml",
                    "--profile", "restore-drill", "up", "--build",
                    "--abort-on-container-exit", "--exit-code-from", "restore-drill",
                ],
                cwd=RESTORE_ROOT,
                environment=drill_environment,
            )
        finally:
            run_command(
                [
                    "docker", "compose", "-f", "compose.restore-drill.yaml",
                    "--profile", "restore-drill", "down", "--remove-orphans",
                ],
                cwd=RESTORE_ROOT,
                environment=drill_environment,
            )

        if report_path.is_symlink() or not report_path.is_file():
            raise RestoreDrillControllerError(
                "isolated execution produced no safe regular report"
            )

        admission_environment = os.environ.copy()
        admission_environment["RESTORE_REPORT_PATH"] = str(report_path)
        stage = "evidence admission"
        admitted = run_command(
            [
                "docker", "compose", "--env-file", "stack.env",
                "-f", "compose.yaml", "--profile", "restore-admission",
                "run", "--rm", "restore-admission",
            ],
            cwd=DEPLOY_ROOT,
            environment=admission_environment,
        )
        admission = _validated_admission(_json_receipt(admitted.stdout, stage))

        stage = "lease completion"
        completed = run_command(
            _coordinator_command(
                "complete",
                [
                    "--run-id", run_id,
                    "--lease-token", lease_token,
                    "--report-content-hash", str(admission["content_hash"]),
                    "--verification-id", str(admission["verification_id"]),
                    "--actor", ACTOR,
                ],
            ),
            cwd=DEPLOY_ROOT,
        )
        completion = _json_receipt(completed.stdout, stage)
        return {
            "status": "completed",
            "run_id": run_id,
            "backup_id": lease["backup_id"],
            "report_content_hash": admission["content_hash"],
            "verification_id": admission["verification_id"],
            "completion": completion["status"],
        }
    except (KeyError, OSError, subprocess.SubprocessError, RestoreDrillControllerError) as exc:
        reason = _failure_reason(stage, exc)
        if lease is not None:
            try:
                _fail_lease(run_command, lease, reason)
            except (KeyError, OSError, subprocess.SubprocessError) as close_exc:
                raise RestoreDrillControllerError(
                    f"{reason}; canonical lease closure also failed"
                ) from close_exc
        raise RestoreDrillControllerError(reason) from exc
    except KeyboardInterrupt as exc:
        if lease is not None:
            try:
                _fail_lease(run_command, lease, _failure_reason(stage, exc))
            except (KeyError, OSError, subprocess.SubprocessError):
                pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--lease-seconds", type=int, default=7200)
    parser.add_argument(
        "--scheduled",
        action="store_true",
        help="Run only when the canonical PostgreSQL schedule is due",
    )
    args = parser.parse_args()
    try:
        receipt = execute(
            owner=args.owner,
            lease_seconds=args.lease_seconds,
            scheduled=args.scheduled,
        )
    except RestoreDrillControllerError as exc:
        print(f"restore drill controller: rejected: {exc}")
        return 1
    except KeyboardInterrupt:
        print("restore drill controller: interrupted")
        return 130
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
