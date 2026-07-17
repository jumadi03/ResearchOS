"""Live, fail-closed preflight revalidation for repository evolution."""

from __future__ import annotations

from app.architecture.models import ArchitectureGraph

from .evolution_models import (
    RepositoryEvolutionDecision,
    RepositoryEvolutionPlan,
    RepositoryEvolutionPreflight,
    RepositoryPreflightCheck,
    RepositoryPreflightOutcome,
)
from .file_registry_models import RepositoryFileRegistry


class RepositoryEvolutionPreflightEngine:
    def evaluate(
        self,
        plan: RepositoryEvolutionPlan,
        registry: RepositoryFileRegistry,
        graph: ArchitectureGraph,
    ) -> RepositoryEvolutionPreflight:
        if not plan.verify():
            raise ValueError("A verified repository evolution plan is required")
        if not registry.verify():
            raise ValueError("A verified current file registry is required")
        if not graph.verify():
            raise ValueError("A verified current Architecture Graph is required")

        entries = {item.file_id: item for item in registry.entries}
        sources = {item.source_path for item in plan.moves}
        occupied = {item.current_path for item in registry.entries}
        checks = (
            self._check(
                "human_approval_valid",
                plan.decision is RepositoryEvolutionDecision.APPROVED,
                "plan_has_attributed_human_approval",
                f"plan_decision_is_{plan.decision.value}",
            ),
            self._check(
                "source_revision_current",
                registry.source_revision == plan.source_revision,
                "source_revision_matches_plan",
                "source_revision_changed_after_planning",
            ),
            self._check(
                "registry_identity_current",
                registry.registry_id == plan.registry_id
                and registry.content_hash == plan.registry_hash,
                "registry_identity_matches_plan",
                "registry_identity_changed_after_planning",
            ),
            self._check(
                "source_state_current",
                all(
                    move.file_id in entries
                    and entries[move.file_id].current_path == move.source_path
                    and entries[move.file_id].content_hash == move.content_hash
                    for move in plan.moves
                ),
                "all_source_paths_and_hashes_match",
                "source_path_or_content_changed_after_planning",
            ),
            self._check(
                "targets_available",
                all(
                    move.target_path not in occupied
                    or move.target_path in sources
                    for move in plan.moves
                ),
                "all_targets_are_available",
                "one_or_more_targets_are_occupied",
            ),
            self._check(
                "rollback_complete",
                bool(plan.rollback_moves)
                and len(plan.rollback_moves) == len(plan.moves),
                "rollback_is_complete",
                "rollback_is_incomplete",
            ),
            self._check(
                "architecture_graph_current",
                graph.project_name == plan.project_name
                and graph.source_revision == registry.source_revision,
                "architecture_graph_matches_current_revision",
                "architecture_graph_is_missing_or_stale",
            ),
        )
        failed = [item for item in checks if not item.passed]
        stale_ids = {
            "source_revision_current",
            "registry_identity_current",
            "source_state_current",
            "architecture_graph_current",
        }
        outcome = (
            RepositoryPreflightOutcome.READY
            if not failed
            else RepositoryPreflightOutcome.STALE
            if any(item.check_id in stale_ids for item in failed)
            else RepositoryPreflightOutcome.BLOCKED
        )
        result = RepositoryEvolutionPreflight(
            "", plan.project_name, plan.plan_id, plan.content_hash,
            registry.source_revision, registry.registry_id,
            registry.content_hash, registry.policy_bundle_id,
            registry.policy_bundle_hash, graph.graph_id, graph.content_hash,
            outcome, checks,
        ).finalized()
        if not result.verify():
            raise ValueError("Repository evolution preflight integrity failed")
        return result

    @staticmethod
    def _check(
        check_id: str,
        passed: bool,
        success_reason: str,
        failure_reason: str,
    ) -> RepositoryPreflightCheck:
        return RepositoryPreflightCheck(
            check_id, passed, success_reason if passed else failure_reason,
        )
