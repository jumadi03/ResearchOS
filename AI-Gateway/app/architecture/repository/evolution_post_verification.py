"""Canonical-state post-migration verification for FMA-008."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from hashlib import sha256
import json

from app.architecture.models import ArchitectureGraph
from app.architecture.schema import (
    REPOSITORY_EVOLUTION_POST_VERIFICATION_SCHEMA,
)

from .evolution_execution_models import (
    RepositoryEvolutionExecution,
    RepositoryExecutionStatus,
)
from .evolution_models import RepositoryEvolutionPlan
from .file_registry_models import RepositoryFileRegistry


def _valid_hash(value: str) -> bool:
    return len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


class RepositoryPostVerificationOutcome(StrEnum):
    VERIFIED = "verified"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class RepositoryPostVerificationCheck:
    check_id: str
    passed: bool
    reason: str

    def verify(self) -> bool:
        return bool(self.check_id.strip() and self.reason.strip())


@dataclass(frozen=True, slots=True)
class RepositoryEvolutionPostVerification:
    verification_id: str
    project_name: str
    plan_id: str
    plan_hash: str
    execution_id: str
    execution_hash: str
    source_revision: str
    result_revision: str
    registry_id: str
    registry_hash: str
    graph_id: str
    graph_hash: str
    outcome: RepositoryPostVerificationOutcome
    checks: tuple[RepositoryPostVerificationCheck, ...]
    schema_version: str = "1.0"
    content_hash: str = ""

    @property
    def authorizes_production_activation(self) -> bool:
        return False

    def canonical_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "project_name": self.project_name,
            "plan_id": self.plan_id,
            "plan_hash": self.plan_hash,
            "execution_id": self.execution_id,
            "execution_hash": self.execution_hash,
            "source_revision": self.source_revision,
            "result_revision": self.result_revision,
            "registry_id": self.registry_id,
            "registry_hash": self.registry_hash,
            "graph_id": self.graph_id,
            "graph_hash": self.graph_hash,
            "outcome": self.outcome,
            "checks": [asdict(item) for item in self.checks],
        }

    def calculate_content_hash(self) -> str:
        return sha256(json.dumps(
            self.canonical_payload(),
            ensure_ascii=False, separators=(",", ":"), sort_keys=True,
        ).encode("utf-8")).hexdigest()

    def finalized(self) -> "RepositoryEvolutionPostVerification":
        candidate = replace(self, verification_id="", content_hash="")
        content_hash = candidate.calculate_content_hash()
        return replace(
            candidate,
            verification_id=(
                f"repository-post-verification:{self.project_name}:"
                f"{content_hash[:16]}"
            ),
            content_hash=content_hash,
        )

    def verify(self) -> bool:
        ids = [item.check_id for item in self.checks]
        expected = (
            RepositoryPostVerificationOutcome.VERIFIED
            if all(item.passed for item in self.checks)
            else RepositoryPostVerificationOutcome.BLOCKED
        )
        return (
            bool(
                self.project_name.strip()
                and self.plan_id.strip()
                and _valid_hash(self.plan_hash)
                and self.execution_id.strip()
                and _valid_hash(self.execution_hash)
                and self.source_revision.strip()
                and self.result_revision.strip()
                and self.registry_id.strip()
                and _valid_hash(self.registry_hash)
                and self.graph_id.strip()
                and _valid_hash(self.graph_hash)
                and self.checks
            )
            and len(ids) == len(set(ids))
            and all(item.verify() for item in self.checks)
            and self.outcome is expected
            and not self.authorizes_production_activation
            and self == self.finalized()
        )

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(
            {
                "verification_id": self.verification_id,
                "content_hash": self.content_hash,
                "authorizes_production_activation": (
                    self.authorizes_production_activation
                ),
                **self.canonical_payload(),
            },
            ensure_ascii=False, indent=indent, sort_keys=True,
        )

    @classmethod
    def from_json(cls, value: str) -> "RepositoryEvolutionPostVerification":
        payload = json.loads(value)
        REPOSITORY_EVOLUTION_POST_VERIFICATION_SCHEMA.require_readable(
            payload.get("schema_version", "")
        )
        result = cls(
            verification_id=payload.get("verification_id", ""),
            project_name=payload["project_name"],
            plan_id=payload["plan_id"],
            plan_hash=payload["plan_hash"],
            execution_id=payload["execution_id"],
            execution_hash=payload["execution_hash"],
            source_revision=payload["source_revision"],
            result_revision=payload["result_revision"],
            registry_id=payload["registry_id"],
            registry_hash=payload["registry_hash"],
            graph_id=payload["graph_id"],
            graph_hash=payload["graph_hash"],
            outcome=RepositoryPostVerificationOutcome(payload["outcome"]),
            checks=tuple(
                RepositoryPostVerificationCheck(**item)
                for item in payload["checks"]
            ),
            schema_version=payload.get("schema_version", ""),
            content_hash=payload.get("content_hash", ""),
        )
        if (
            payload.get("authorizes_production_activation") is not False
            or not result.verify()
        ):
            raise ValueError("Repository post-migration verification is invalid")
        return result


class RepositoryEvolutionPostVerifier:
    def verify(
        self,
        plan: RepositoryEvolutionPlan,
        execution: RepositoryEvolutionExecution,
        registry: RepositoryFileRegistry,
        graph: ArchitectureGraph,
    ) -> RepositoryEvolutionPostVerification:
        if not all((
            plan.verify(), execution.verify(), registry.verify(), graph.verify(),
        )):
            raise ValueError("Verified post-migration inputs are required")
        if not (
            execution.project_name == plan.project_name
            and execution.plan_id == plan.plan_id
            and execution.plan_hash == plan.content_hash
            and registry.project_name == plan.project_name
            and graph.project_name == plan.project_name
        ):
            raise ValueError("Post-migration provenance does not match")

        entries = {item.file_id: item for item in registry.entries}
        paths = {item.current_path for item in registry.entries}
        events = {
            (
                item.file_id, item.from_path, item.to_path,
                item.from_hash, item.to_hash,
                item.from_revision, item.to_revision,
            )
            for item in registry.continuity_events
        }
        nodes = {item.node_id: item for item in graph.nodes}
        project = nodes.get(f"project:{plan.project_name}")
        traceability = (
            project.metadata.get("repository_traceability", {})
            if project is not None else {}
        )
        checks = (
            self._check(
                "execution_completed",
                execution.status is RepositoryExecutionStatus.COMPLETED,
                "execution_completed",
                f"execution_status_is_{execution.status.value}",
            ),
            self._check(
                "result_revision_advanced",
                registry.source_revision != plan.source_revision,
                "result_revision_differs_from_source",
                "result_revision_did_not_advance",
            ),
            self._check(
                "file_identity_and_hash_preserved",
                all(
                    move.file_id in entries
                    and entries[move.file_id].current_path == move.target_path
                    and entries[move.file_id].content_hash == move.content_hash
                    for move in plan.moves
                ),
                "all_file_identities_paths_and_hashes_match",
                "file_identity_path_or_hash_mismatch",
            ),
            self._check(
                "source_paths_retired",
                all(move.source_path not in paths for move in plan.moves),
                "all_source_paths_are_retired",
                "one_or_more_source_paths_remain_canonical",
            ),
            self._check(
                "continuity_complete",
                all(
                    (
                        move.file_id, move.source_path, move.target_path,
                        move.content_hash, move.content_hash,
                        plan.source_revision, registry.source_revision,
                    ) in events
                    for move in plan.moves
                ),
                "all_moves_have_exact_continuity_events",
                "continuity_event_is_missing_or_stale",
            ),
            self._check(
                "graph_revision_current",
                graph.source_revision == registry.source_revision,
                "graph_matches_result_revision",
                "graph_revision_does_not_match_result",
            ),
            self._check(
                "graph_file_traceability_current",
                all(
                    move.file_id in nodes
                    and nodes[move.file_id].node_type == "File"
                    and nodes[move.file_id].source_path == move.target_path
                    and nodes[move.file_id].metadata.get("content_hash")
                    == move.content_hash
                    for move in plan.moves
                ),
                "graph_file_nodes_match_migration_result",
                "graph_file_traceability_is_missing_or_stale",
            ),
            self._check(
                "graph_registry_provenance_current",
                traceability.get("registry_id") == registry.registry_id
                and traceability.get("registry_hash") == registry.content_hash,
                "graph_registry_provenance_matches",
                "graph_registry_provenance_is_missing_or_stale",
            ),
        )
        outcome = (
            RepositoryPostVerificationOutcome.VERIFIED
            if all(item.passed for item in checks)
            else RepositoryPostVerificationOutcome.BLOCKED
        )
        result = RepositoryEvolutionPostVerification(
            "", plan.project_name, plan.plan_id, plan.content_hash,
            execution.execution_id, execution.content_hash,
            plan.source_revision, registry.source_revision,
            registry.registry_id, registry.content_hash,
            graph.graph_id, graph.content_hash, outcome, checks,
        ).finalized()
        if not result.verify():
            raise ValueError("Post-migration verification integrity failed")
        return result

    @staticmethod
    def _check(check_id, passed, success, failure):
        return RepositoryPostVerificationCheck(
            check_id, passed, success if passed else failure,
        )
