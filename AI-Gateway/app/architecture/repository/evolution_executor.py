"""Root-confined transactional file mover for isolated FMA-008 execution."""

from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path, PurePosixPath
from typing import Protocol

from .evolution_dry_run_models import RepositoryEvolutionDryRun
from .evolution_execution_models import (
    RepositoryEvolutionExecution,
    RepositoryExecutionAction,
    RepositoryExecutionEvent,
    RepositoryExecutionOutcome,
    RepositoryExecutionStatus,
)
from .evolution_models import (
    RepositoryEvolutionPlan,
    RepositoryEvolutionPreflight,
    RepositoryPreflightOutcome,
)


class RepositoryFileMover(Protocol):
    def move(self, source: Path, target: Path) -> None: ...


class NoOverwriteFileMover:
    """Move one regular file without ever replacing an existing target."""

    def move(self, source: Path, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        os.link(source, target)
        try:
            source.unlink()
        except Exception:
            target.unlink(missing_ok=True)
            raise


class RepositoryEvolutionExecutor:
    def __init__(
        self,
        root: Path,
        *,
        mover: RepositoryFileMover | None = None,
    ) -> None:
        if not root.exists() or not root.is_dir() or root.is_symlink():
            raise ValueError("Execution root must be an existing real directory")
        self._root = root.resolve(strict=True)
        self._mover = mover or NoOverwriteFileMover()

    def execute(
        self,
        plan: RepositoryEvolutionPlan,
        preflight: RepositoryEvolutionPreflight,
        dry_run: RepositoryEvolutionDryRun,
    ) -> RepositoryEvolutionExecution:
        self._validate_contracts(plan, preflight, dry_run)
        resolved = tuple(
            (step, self._resolve(step.source_path), self._resolve(step.target_path))
            for step in dry_run.forward_steps
        )
        self._validate_workspace(resolved)
        fingerprint = self._workspace_fingerprint(resolved)
        events: list[RepositoryExecutionEvent] = []
        completed: list[tuple[object, Path, Path, bool]] = []
        for step, source, target in resolved:
            target_parent_existed = target.parent.exists()
            try:
                self._mover.move(source, target)
                completed.append(
                    (step, source, target, target_parent_existed)
                )
                if self._hash(target) != step.content_hash:
                    raise OSError("moved_content_hash_mismatch")
                events.append(self._event(
                    events, RepositoryExecutionAction.FORWARD, step,
                    RepositoryExecutionOutcome.MOVED, "move_completed",
                ))
            except Exception:
                if target.exists() and not source.exists() and not any(
                    item[1] == source and item[2] == target
                    for item in completed
                ):
                    completed.append(
                        (step, source, target, target_parent_existed)
                    )
                events.append(self._event(
                    events, RepositoryExecutionAction.FORWARD, step,
                    RepositoryExecutionOutcome.FAILED, "move_failed",
                ))
                self._rollback(completed, events)
                if source.exists() and not target.exists():
                    self._cleanup_empty_parents(target.parent)
                break
        status = self._status(events)
        result = RepositoryEvolutionExecution(
            "", plan.project_name, plan.plan_id, plan.content_hash,
            preflight.preflight_id, preflight.content_hash,
            dry_run.dry_run_id, dry_run.content_hash, plan.source_revision,
            fingerprint, status, tuple(events),
        ).finalized()
        if not result.verify():
            raise ValueError("Repository evolution execution audit is invalid")
        return result

    def _validate_contracts(self, plan, preflight, dry_run) -> None:
        if not plan.verify() or not preflight.verify() or not dry_run.verify():
            raise ValueError("Verified plan, preflight, and dry run are required")
        if preflight.outcome is not RepositoryPreflightOutcome.READY:
            raise ValueError("A ready preflight is required")
        if not (
            preflight.plan_id == plan.plan_id
            and preflight.plan_hash == plan.content_hash
            and dry_run.plan_id == plan.plan_id
            and dry_run.plan_hash == plan.content_hash
            and dry_run.preflight_id == preflight.preflight_id
            and dry_run.preflight_hash == preflight.content_hash
            and dry_run.source_revision == plan.source_revision
        ):
            raise ValueError("Execution provenance does not match")

    def _resolve(self, value: str) -> Path:
        parts = PurePosixPath(value).parts
        if not parts or any(part in {"", ".", ".."} for part in parts):
            raise ValueError(f"Unsafe repository path: {value}")
        candidate = self._root.joinpath(*parts)
        current = self._root
        for part in parts:
            current = current / part
            if current.exists() and current.is_symlink():
                raise ValueError(f"Symlink path is not allowed: {value}")
        resolved = candidate.resolve(strict=False)
        if not resolved.is_relative_to(self._root):
            raise ValueError(f"Repository path escapes execution root: {value}")
        return resolved

    def _validate_workspace(self, resolved) -> None:
        for step, source, target in resolved:
            if (
                not source.exists()
                or not source.is_file()
                or source.is_symlink()
            ):
                raise ValueError(f"Source is not a regular file: {step.source_path}")
            if target.exists() or target.is_symlink():
                raise ValueError(f"Target already exists: {step.target_path}")
            if self._hash(source) != step.content_hash:
                raise ValueError(f"Source hash is stale: {step.source_path}")

    def _workspace_fingerprint(self, resolved) -> str:
        payload = "\n".join(
            f"{step.file_id}:{step.source_path}:{step.target_path}:"
            f"{step.content_hash}"
            for step, _, _ in resolved
        )
        return sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _hash(path: Path) -> str:
        digest = sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _rollback(self, completed, events) -> None:
        for step, source, target, target_parent_existed in reversed(completed):
            try:
                self._mover.move(target, source)
                if not target_parent_existed:
                    self._cleanup_empty_parents(target.parent)
                outcome = RepositoryExecutionOutcome.MOVED
                reason = "rollback_completed"
            except Exception:
                outcome = RepositoryExecutionOutcome.FAILED
                reason = "rollback_failed"
            events.append(self._event(
                events, RepositoryExecutionAction.ROLLBACK, step,
                outcome, reason, source_path=step.target_path,
                target_path=step.source_path,
            ))

    def _cleanup_empty_parents(self, directory: Path) -> None:
        current = directory
        while current != self._root and current.is_relative_to(self._root):
            try:
                current.rmdir()
            except OSError:
                break
            current = current.parent

    @staticmethod
    def _event(
        events,
        action,
        step,
        outcome,
        reason,
        *,
        source_path=None,
        target_path=None,
    ) -> RepositoryExecutionEvent:
        return RepositoryExecutionEvent(
            len(events) + 1, action, step.file_id,
            source_path or step.source_path,
            target_path or step.target_path,
            step.content_hash, outcome, reason,
        )

    @staticmethod
    def _status(events) -> RepositoryExecutionStatus:
        failures = [
            item for item in events
            if item.outcome is RepositoryExecutionOutcome.FAILED
        ]
        forward = sum(
            item.action is RepositoryExecutionAction.FORWARD
            and item.outcome is RepositoryExecutionOutcome.MOVED
            for item in events
        )
        rolled_back = sum(
            item.action is RepositoryExecutionAction.ROLLBACK
            and item.outcome is RepositoryExecutionOutcome.MOVED
            for item in events
        )
        if not failures:
            return RepositoryExecutionStatus.COMPLETED
        if forward == 0:
            return RepositoryExecutionStatus.FAILED_SAFE
        if rolled_back == forward:
            return RepositoryExecutionStatus.ROLLED_BACK
        return RepositoryExecutionStatus.RECOVERY_REQUIRED
