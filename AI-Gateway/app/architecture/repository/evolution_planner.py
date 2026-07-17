"""Fail-closed planning boundary for repository evolution."""

from __future__ import annotations

from .evolution_models import RepositoryEvolutionPlan, RepositoryMove
from .file_registry_models import RepositoryFileRegistry


class RepositoryEvolutionPlanner:
    def plan(
        self,
        registry: RepositoryFileRegistry,
        moves: tuple[RepositoryMove, ...],
        *,
        proposed_by: str,
    ) -> RepositoryEvolutionPlan:
        if not registry.verify():
            raise ValueError("A verified canonical file registry is required")
        entries = {item.file_id: item for item in registry.entries}
        occupied = {item.current_path for item in registry.entries}
        for move in moves:
            entry = entries.get(move.file_id)
            if entry is None:
                raise ValueError(f"Unknown source file identity: {move.file_id}")
            if (
                entry.current_path != move.source_path
                or entry.content_hash != move.content_hash
            ):
                raise ValueError(
                    f"Stale source state for repository move: {move.file_id}"
                )
            if move.target_path in occupied and move.target_path not in {
                item.source_path for item in moves
            }:
                raise ValueError(
                    f"Repository move target is already occupied: {move.target_path}"
                )
        rollback = tuple(
            RepositoryMove(
                item.file_id, item.target_path, item.source_path,
                item.content_hash, f"Rollback: {item.rationale}",
            )
            for item in reversed(moves)
        )
        plan = RepositoryEvolutionPlan(
            "", registry.project_name, registry.source_revision,
            registry.registry_id, registry.content_hash, moves, rollback,
            proposed_by,
        ).finalized()
        if not plan.verify():
            raise ValueError("Repository evolution proposal is unsafe")
        return plan
