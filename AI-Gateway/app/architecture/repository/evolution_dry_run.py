"""Fail-closed, non-mutating orchestration for FMA-008 dry runs."""

from __future__ import annotations

from .evolution_dry_run_models import (
    RepositoryDryRunDirection,
    RepositoryDryRunStep,
    RepositoryEvolutionDryRun,
)
from .evolution_models import (
    RepositoryEvolutionPlan,
    RepositoryEvolutionPreflight,
    RepositoryPreflightOutcome,
)


class RepositoryEvolutionDryRunEngine:
    def simulate(
        self,
        plan: RepositoryEvolutionPlan,
        preflight: RepositoryEvolutionPreflight,
    ) -> RepositoryEvolutionDryRun:
        if not plan.verify():
            raise ValueError("A verified repository evolution plan is required")
        if not preflight.verify():
            raise ValueError("A verified repository evolution preflight is required")
        if preflight.outcome is not RepositoryPreflightOutcome.READY:
            raise ValueError(
                f"Repository evolution preflight is {preflight.outcome.value}"
            )
        if (
            preflight.project_name != plan.project_name
            or preflight.plan_id != plan.plan_id
            or preflight.plan_hash != plan.content_hash
            or preflight.current_revision != plan.source_revision
        ):
            raise ValueError("Dry-run plan and preflight provenance do not match")

        forward = tuple(
            RepositoryDryRunStep(
                sequence=index,
                direction=RepositoryDryRunDirection.FORWARD,
                file_id=move.file_id,
                source_path=move.source_path,
                target_path=move.target_path,
                content_hash=move.content_hash,
            )
            for index, move in enumerate(plan.moves, start=1)
        )
        rollback = tuple(
            RepositoryDryRunStep(
                sequence=index,
                direction=RepositoryDryRunDirection.ROLLBACK,
                file_id=move.file_id,
                source_path=move.source_path,
                target_path=move.target_path,
                content_hash=move.content_hash,
            )
            for index, move in enumerate(plan.rollback_moves, start=1)
        )
        result = RepositoryEvolutionDryRun(
            "", plan.project_name, plan.plan_id, plan.content_hash,
            preflight.preflight_id, preflight.content_hash,
            preflight.current_revision, forward, rollback,
        ).finalized()
        if not result.verify():
            raise ValueError("Repository evolution dry run integrity failed")
        return result
