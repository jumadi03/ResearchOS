"""Isolated automatic rollback executor with compensation."""

from __future__ import annotations

from pathlib import Path

from .evolution_dry_run_models import RepositoryEvolutionDryRun
from .evolution_execution_models import (
    RepositoryEvolutionExecution,
    RepositoryExecutionAction,
    RepositoryExecutionEvent,
    RepositoryExecutionOutcome,
)
from .evolution_executor import (
    RepositoryEvolutionExecutor,
    RepositoryFileMover,
)
from .evolution_recovery import (
    RepositoryEvolutionRecovery,
    RepositoryRecoveryDecision,
    RepositoryRecoveryExecution,
    RepositoryRecoveryExecutionStatus,
)


class RepositoryEvolutionRecoveryExecutor(RepositoryEvolutionExecutor):
    def __init__(
        self, root: Path, *, mover: RepositoryFileMover | None = None,
    ) -> None:
        super().__init__(root, mover=mover)

    def recover(
        self,
        recovery: RepositoryEvolutionRecovery,
        execution: RepositoryEvolutionExecution,
        dry_run: RepositoryEvolutionDryRun,
    ) -> RepositoryRecoveryExecution:
        if not recovery.verify() or not execution.verify() or not dry_run.verify():
            raise ValueError("Verified recovery inputs are required")
        if recovery.decision is not (
            RepositoryRecoveryDecision.AUTOMATIC_ROLLBACK_ELIGIBLE
        ):
            raise ValueError("Recovery is not eligible for automatic rollback")
        if not (
            recovery.execution_id == execution.execution_id
            and recovery.execution_hash == execution.content_hash
            and recovery.dry_run_id == dry_run.dry_run_id
            and recovery.dry_run_hash == dry_run.content_hash
            and recovery.rollback_steps == dry_run.rollback_steps
        ):
            raise ValueError("Recovery execution provenance does not match")

        resolved = tuple(
            (step, self._resolve(step.source_path), self._resolve(step.target_path))
            for step in recovery.rollback_steps
        )
        self._validate_workspace(resolved)
        fingerprint = self._workspace_fingerprint(resolved)
        events = []
        completed = []
        for step, source, target in resolved:
            try:
                self._mover.move(source, target)
                completed.append((step, source, target))
                if self._hash(target) != step.content_hash:
                    raise OSError("recovered_content_hash_mismatch")
                events.append(self._event_for(
                    events, RepositoryExecutionAction.ROLLBACK, step,
                    RepositoryExecutionOutcome.MOVED, "recovery_move_completed",
                ))
            except Exception:
                events.append(self._event_for(
                    events, RepositoryExecutionAction.ROLLBACK, step,
                    RepositoryExecutionOutcome.FAILED, "recovery_move_failed",
                ))
                self._compensate(completed, events)
                break
        status = self._recovery_status(events)
        result = RepositoryRecoveryExecution(
            "", recovery.project_name, recovery.recovery_id,
            recovery.content_hash, execution.execution_id,
            execution.content_hash, dry_run.dry_run_id,
            dry_run.content_hash, fingerprint, status, tuple(events),
        ).finalized()
        if not result.verify():
            raise ValueError("Repository recovery execution audit is invalid")
        return result

    def _compensate(self, completed, events):
        for step, source, target in reversed(completed):
            try:
                self._mover.move(target, source)
                outcome = RepositoryExecutionOutcome.MOVED
                reason = "recovery_compensation_completed"
            except Exception:
                outcome = RepositoryExecutionOutcome.FAILED
                reason = "recovery_compensation_failed"
            events.append(self._event_for(
                events, RepositoryExecutionAction.FORWARD, step,
                outcome, reason, source_path=step.target_path,
                target_path=step.source_path,
            ))

    @staticmethod
    def _event_for(
        events, action, step, outcome, reason,
        *, source_path=None, target_path=None,
    ):
        return RepositoryExecutionEvent(
            len(events) + 1, action, step.file_id,
            source_path or step.source_path,
            target_path or step.target_path,
            step.content_hash, outcome, reason,
        )

    @staticmethod
    def _recovery_status(events):
        rollback = sum(
            item.action is RepositoryExecutionAction.ROLLBACK
            and item.outcome is RepositoryExecutionOutcome.MOVED
            for item in events
        )
        compensated = sum(
            item.action is RepositoryExecutionAction.FORWARD
            and item.outcome is RepositoryExecutionOutcome.MOVED
            for item in events
        )
        failures = sum(
            item.outcome is RepositoryExecutionOutcome.FAILED
            for item in events
        )
        if not failures:
            return RepositoryRecoveryExecutionStatus.RECOVERED
        if rollback == 0:
            return RepositoryRecoveryExecutionStatus.FAILED_SAFE
        if compensated == rollback:
            return RepositoryRecoveryExecutionStatus.RESTORED_MIGRATED_STATE
        return RepositoryRecoveryExecutionStatus.RECOVERY_REQUIRED
