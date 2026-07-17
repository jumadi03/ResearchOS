"""Canonical post-recovery revalidation for FMA-008."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from hashlib import sha256
import json

from app.architecture.models import ArchitectureGraph
from app.architecture.schema import REPOSITORY_EVOLUTION_POST_RECOVERY_SCHEMA

from .evolution_models import RepositoryEvolutionPlan
from .evolution_recovery import (
    RepositoryEvolutionRecovery,
    RepositoryRecoveryExecution,
    RepositoryRecoveryExecutionStatus,
)
from .file_registry_models import RepositoryFileRegistry


def _valid_hash(value):
    return len(value) == 64 and all(c in "0123456789abcdef" for c in value)


class RepositoryPostRecoveryOutcome(StrEnum):
    RECOVERED_VERIFIED = "recovered_verified"
    RECOVERY_BLOCKED = "recovery_blocked"
    MANUAL_RECOVERY_REQUIRED = "manual_recovery_required"


@dataclass(frozen=True, slots=True)
class RepositoryPostRecoveryCheck:
    check_id: str
    passed: bool
    reason: str

    def verify(self):
        return bool(self.check_id.strip() and self.reason.strip())


@dataclass(frozen=True, slots=True)
class RepositoryPostRecoveryVerification:
    verification_id: str
    project_name: str
    plan_id: str
    plan_hash: str
    recovery_id: str
    recovery_hash: str
    recovery_execution_id: str
    recovery_execution_hash: str
    result_revision: str
    registry_id: str
    registry_hash: str
    graph_id: str
    graph_hash: str
    outcome: RepositoryPostRecoveryOutcome
    checks: tuple[RepositoryPostRecoveryCheck, ...]
    schema_version: str = "1.0"
    content_hash: str = ""

    @property
    def closes_migration_lifecycle(self):
        return False

    def canonical_payload(self):
        return {
            "schema_version": self.schema_version,
            "project_name": self.project_name,
            "plan_id": self.plan_id,
            "plan_hash": self.plan_hash,
            "recovery_id": self.recovery_id,
            "recovery_hash": self.recovery_hash,
            "recovery_execution_id": self.recovery_execution_id,
            "recovery_execution_hash": self.recovery_execution_hash,
            "result_revision": self.result_revision,
            "registry_id": self.registry_id,
            "registry_hash": self.registry_hash,
            "graph_id": self.graph_id,
            "graph_hash": self.graph_hash,
            "outcome": self.outcome,
            "checks": [asdict(item) for item in self.checks],
        }

    def finalized(self):
        candidate = replace(self, verification_id="", content_hash="")
        digest = sha256(json.dumps(
            candidate.canonical_payload(), ensure_ascii=False,
            separators=(",", ":"), sort_keys=True,
        ).encode()).hexdigest()
        return replace(
            candidate,
            verification_id=(
                f"repository-post-recovery:{self.project_name}:{digest[:16]}"
            ),
            content_hash=digest,
        )

    def verify(self):
        ids = [item.check_id for item in self.checks]
        status = next(
            (item.reason for item in self.checks
             if item.check_id == "recovery_execution_recovered"),
            "",
        )
        expected = (
            RepositoryPostRecoveryOutcome.RECOVERED_VERIFIED
            if all(item.passed for item in self.checks)
            else RepositoryPostRecoveryOutcome.MANUAL_RECOVERY_REQUIRED
            if status == "recovery_execution_requires_manual_recovery"
            else RepositoryPostRecoveryOutcome.RECOVERY_BLOCKED
        )
        return (
            bool(
                self.project_name.strip() and self.plan_id.strip()
                and _valid_hash(self.plan_hash) and self.recovery_id.strip()
                and _valid_hash(self.recovery_hash)
                and self.recovery_execution_id.strip()
                and _valid_hash(self.recovery_execution_hash)
                and self.result_revision.strip() and self.registry_id.strip()
                and _valid_hash(self.registry_hash) and self.graph_id.strip()
                and _valid_hash(self.graph_hash) and self.checks
            )
            and len(ids) == len(set(ids))
            and all(item.verify() for item in self.checks)
            and self.outcome is expected
            and not self.closes_migration_lifecycle
            and self == self.finalized()
        )


class RepositoryEvolutionPostRecoveryVerifier:
    def verify(self, plan, recovery, recovery_execution, registry, graph):
        if not all((
            plan.verify(), recovery.verify(), recovery_execution.verify(),
            registry.verify(), graph.verify(),
        )):
            raise ValueError("Verified post-recovery inputs are required")
        if not (
            recovery.project_name == plan.project_name == registry.project_name
            == graph.project_name
            and recovery_execution.recovery_id == recovery.recovery_id
            and recovery_execution.recovery_hash == recovery.content_hash
        ):
            raise ValueError("Post-recovery provenance does not match")
        entries = {item.file_id: item for item in registry.entries}
        paths = {item.current_path for item in registry.entries}
        events = registry.continuity_events
        nodes = {item.node_id: item for item in graph.nodes}
        project = nodes.get(f"project:{plan.project_name}")
        trace = (
            project.metadata.get("repository_traceability", {})
            if project else {}
        )
        recovered = (
            recovery_execution.status
            is RepositoryRecoveryExecutionStatus.RECOVERED
        )
        manual = (
            recovery_execution.status
            is RepositoryRecoveryExecutionStatus.RECOVERY_REQUIRED
        )
        checks = (
            self._check(
                "recovery_execution_recovered", recovered,
                "recovery_execution_recovered",
                "recovery_execution_requires_manual_recovery"
                if manual else "recovery_execution_not_recovered",
            ),
            self._check(
                "recovery_revision_advanced",
                registry.source_revision != plan.source_revision,
                "recovery_revision_advanced", "recovery_revision_is_stale",
            ),
            self._check(
                "original_file_state_restored",
                all(
                    move.file_id in entries
                    and entries[move.file_id].current_path == move.source_path
                    and entries[move.file_id].content_hash == move.content_hash
                    for move in plan.moves
                ),
                "original_paths_and_hashes_restored",
                "original_file_state_not_restored",
            ),
            self._check(
                "migration_targets_retired",
                all(move.target_path not in paths for move in plan.moves),
                "migration_targets_retired", "migration_target_remains",
            ),
            self._check(
                "rollback_continuity_complete",
                all(any(
                    event.file_id == move.file_id
                    and event.from_path == move.target_path
                    and event.to_path == move.source_path
                    and event.from_hash == move.content_hash
                    and event.to_hash == move.content_hash
                    and event.to_revision == registry.source_revision
                    for event in events
                ) for move in plan.moves),
                "rollback_continuity_complete",
                "rollback_continuity_missing_or_stale",
            ),
            self._check(
                "recovery_graph_current",
                graph.source_revision == registry.source_revision
                and all(
                    move.file_id in nodes
                    and nodes[move.file_id].source_path == move.source_path
                    and nodes[move.file_id].metadata.get("content_hash")
                    == move.content_hash
                    for move in plan.moves
                ),
                "recovery_graph_matches_registry",
                "recovery_graph_is_stale",
            ),
            self._check(
                "recovery_graph_provenance_current",
                trace.get("registry_id") == registry.registry_id
                and trace.get("registry_hash") == registry.content_hash,
                "recovery_graph_provenance_matches",
                "recovery_graph_provenance_is_stale",
            ),
        )
        outcome = (
            RepositoryPostRecoveryOutcome.RECOVERED_VERIFIED
            if all(item.passed for item in checks)
            else RepositoryPostRecoveryOutcome.MANUAL_RECOVERY_REQUIRED
            if manual else RepositoryPostRecoveryOutcome.RECOVERY_BLOCKED
        )
        result = RepositoryPostRecoveryVerification(
            "", plan.project_name, plan.plan_id, plan.content_hash,
            recovery.recovery_id, recovery.content_hash,
            recovery_execution.recovery_execution_id,
            recovery_execution.content_hash, registry.source_revision,
            registry.registry_id, registry.content_hash,
            graph.graph_id, graph.content_hash, outcome, checks,
        ).finalized()
        if not result.verify():
            raise ValueError("Post-recovery verification integrity failed")
        return result

    @staticmethod
    def _check(check_id, passed, success, failure):
        return RepositoryPostRecoveryCheck(
            check_id, passed, success if passed else failure,
        )
