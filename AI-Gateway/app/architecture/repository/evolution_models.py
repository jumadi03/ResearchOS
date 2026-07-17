"""Immutable, non-executable structural migration plans for FMA-008."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from hashlib import sha256
import json
from pathlib import PurePosixPath

from app.architecture.schema import (
    REPOSITORY_EVOLUTION_PREFLIGHT_SCHEMA,
    REPOSITORY_EVOLUTION_SCHEMA,
)


def _valid_path(path: str) -> bool:
    item = PurePosixPath(path)
    return bool(
        path
        and "\\" not in path
        and not item.is_absolute()
        and all(part not in {"", ".", ".."} for part in item.parts)
    )


def _valid_hash(value: str) -> bool:
    return len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


class RepositoryEvolutionDecision(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"


class RepositoryPreflightOutcome(StrEnum):
    READY = "ready"
    BLOCKED = "blocked"
    STALE = "stale"


@dataclass(frozen=True, slots=True)
class RepositoryMove:
    file_id: str
    source_path: str
    target_path: str
    content_hash: str
    rationale: str

    def verify(self) -> bool:
        return (
            self.file_id.startswith("file:")
            and _valid_path(self.source_path)
            and _valid_path(self.target_path)
            and self.source_path != self.target_path
            and _valid_hash(self.content_hash)
            and bool(self.rationale.strip())
        )


@dataclass(frozen=True, slots=True)
class RepositoryEvolutionPlan:
    plan_id: str
    project_name: str
    source_revision: str
    registry_id: str
    registry_hash: str
    moves: tuple[RepositoryMove, ...]
    rollback_moves: tuple[RepositoryMove, ...]
    proposed_by: str
    decision: RepositoryEvolutionDecision = RepositoryEvolutionDecision.PROPOSED
    decided_by: str | None = None
    decision_rationale: str | None = None
    schema_version: str = "1.0"
    content_hash: str = ""

    @property
    def is_executable(self) -> bool:
        return False

    def canonical_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "project_name": self.project_name,
            "source_revision": self.source_revision,
            "registry_id": self.registry_id,
            "registry_hash": self.registry_hash,
            "moves": [asdict(item) for item in self.moves],
            "rollback_moves": [asdict(item) for item in self.rollback_moves],
            "proposed_by": self.proposed_by,
            "decision": self.decision,
            "decided_by": self.decided_by,
            "decision_rationale": self.decision_rationale,
        }

    def calculate_content_hash(self) -> str:
        return sha256(json.dumps(
            self.canonical_payload(),
            ensure_ascii=False, separators=(",", ":"), sort_keys=True,
        ).encode("utf-8")).hexdigest()

    def finalized(self) -> "RepositoryEvolutionPlan":
        candidate = replace(self, plan_id="", content_hash="")
        content_hash = candidate.calculate_content_hash()
        return replace(
            candidate,
            plan_id=f"repository-evolution:{self.project_name}:{content_hash[:16]}",
            content_hash=content_hash,
        )

    def verify(self) -> bool:
        sources = [item.source_path for item in self.moves]
        targets = [item.target_path for item in self.moves]
        expected_rollback = tuple(
            RepositoryMove(
                item.file_id, item.target_path, item.source_path,
                item.content_hash, f"Rollback: {item.rationale}",
            )
            for item in reversed(self.moves)
        )
        has_decision = bool(
            self.decided_by and self.decided_by.strip()
            and self.decision_rationale and self.decision_rationale.strip()
        )
        decision_is_valid = (
            self.decision is RepositoryEvolutionDecision.PROPOSED
            and self.decided_by is None
            and self.decision_rationale is None
        ) or (
            self.decision in {
                RepositoryEvolutionDecision.APPROVED,
                RepositoryEvolutionDecision.REJECTED,
            }
            and has_decision
        )
        return (
            bool(
                self.project_name.strip()
                and self.source_revision.strip()
                and self.registry_id.strip()
                and _valid_hash(self.registry_hash)
                and self.moves
                and self.proposed_by.strip()
            )
            and all(item.verify() for item in self.moves)
            and len(sources) == len(set(sources))
            and len(targets) == len(set(targets))
            and not set(targets).intersection(set(sources) - set(targets))
            and self.rollback_moves == expected_rollback
            and decision_is_valid
            and not self.is_executable
            and self == self.finalized()
        )

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(
            {
                "plan_id": self.plan_id,
                "content_hash": self.content_hash,
                "is_executable": self.is_executable,
                **self.canonical_payload(),
            },
            ensure_ascii=False, indent=indent, sort_keys=True,
        )

    @classmethod
    def from_json(cls, value: str) -> "RepositoryEvolutionPlan":
        payload = json.loads(value)
        REPOSITORY_EVOLUTION_SCHEMA.require_readable(
            payload.get("schema_version", "")
        )
        plan = cls(
            plan_id=payload.get("plan_id", ""),
            project_name=payload["project_name"],
            source_revision=payload["source_revision"],
            registry_id=payload["registry_id"],
            registry_hash=payload["registry_hash"],
            moves=tuple(RepositoryMove(**item) for item in payload["moves"]),
            rollback_moves=tuple(
                RepositoryMove(**item) for item in payload["rollback_moves"]
            ),
            proposed_by=payload["proposed_by"],
            decision=RepositoryEvolutionDecision(payload["decision"]),
            decided_by=payload.get("decided_by"),
            decision_rationale=payload.get("decision_rationale"),
            schema_version=payload.get("schema_version", ""),
            content_hash=payload.get("content_hash", ""),
        )
        if payload.get("is_executable") is not False or not plan.verify():
            raise ValueError("Repository evolution plan is invalid")
        return plan


@dataclass(frozen=True, slots=True)
class RepositoryPreflightCheck:
    check_id: str
    passed: bool
    reason: str

    def verify(self) -> bool:
        return bool(self.check_id.strip() and self.reason.strip())


@dataclass(frozen=True, slots=True)
class RepositoryEvolutionPreflight:
    preflight_id: str
    project_name: str
    plan_id: str
    plan_hash: str
    current_revision: str
    registry_id: str
    registry_hash: str
    policy_bundle_id: str
    policy_bundle_hash: str
    graph_id: str
    graph_hash: str
    outcome: RepositoryPreflightOutcome
    checks: tuple[RepositoryPreflightCheck, ...]
    schema_version: str = "1.0"
    content_hash: str = ""

    @property
    def is_execution_authorization(self) -> bool:
        return False

    def canonical_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "project_name": self.project_name,
            "plan_id": self.plan_id,
            "plan_hash": self.plan_hash,
            "current_revision": self.current_revision,
            "registry_id": self.registry_id,
            "registry_hash": self.registry_hash,
            "policy_bundle_id": self.policy_bundle_id,
            "policy_bundle_hash": self.policy_bundle_hash,
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

    def finalized(self) -> "RepositoryEvolutionPreflight":
        candidate = replace(self, preflight_id="", content_hash="")
        content_hash = candidate.calculate_content_hash()
        return replace(
            candidate,
            preflight_id=(
                f"repository-preflight:{self.project_name}:{content_hash[:16]}"
            ),
            content_hash=content_hash,
        )

    def verify(self) -> bool:
        ids = [item.check_id for item in self.checks]
        failed = [item for item in self.checks if not item.passed]
        stale_ids = {
            "source_revision_current",
            "registry_identity_current",
            "source_state_current",
            "architecture_graph_current",
        }
        expected = (
            RepositoryPreflightOutcome.READY
            if not failed
            else RepositoryPreflightOutcome.STALE
            if any(item.check_id in stale_ids for item in failed)
            else RepositoryPreflightOutcome.BLOCKED
        )
        return (
            bool(
                self.project_name.strip()
                and self.plan_id.strip()
                and _valid_hash(self.plan_hash)
                and self.current_revision.strip()
                and self.registry_id.strip()
                and _valid_hash(self.registry_hash)
                and self.policy_bundle_id.strip()
                and _valid_hash(self.policy_bundle_hash)
                and self.graph_id.strip()
                and _valid_hash(self.graph_hash)
                and self.checks
            )
            and len(ids) == len(set(ids))
            and all(item.verify() for item in self.checks)
            and self.outcome is expected
            and not self.is_execution_authorization
            and self == self.finalized()
        )

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(
            {
                "preflight_id": self.preflight_id,
                "content_hash": self.content_hash,
                "is_execution_authorization": self.is_execution_authorization,
                **self.canonical_payload(),
            },
            ensure_ascii=False, indent=indent, sort_keys=True,
        )

    @classmethod
    def from_json(cls, value: str) -> "RepositoryEvolutionPreflight":
        payload = json.loads(value)
        REPOSITORY_EVOLUTION_PREFLIGHT_SCHEMA.require_readable(
            payload.get("schema_version", "")
        )
        report = cls(
            preflight_id=payload.get("preflight_id", ""),
            project_name=payload["project_name"],
            plan_id=payload["plan_id"],
            plan_hash=payload["plan_hash"],
            current_revision=payload["current_revision"],
            registry_id=payload["registry_id"],
            registry_hash=payload["registry_hash"],
            policy_bundle_id=payload["policy_bundle_id"],
            policy_bundle_hash=payload["policy_bundle_hash"],
            graph_id=payload["graph_id"],
            graph_hash=payload["graph_hash"],
            outcome=RepositoryPreflightOutcome(payload["outcome"]),
            checks=tuple(
                RepositoryPreflightCheck(**item) for item in payload["checks"]
            ),
            schema_version=payload.get("schema_version", ""),
            content_hash=payload.get("content_hash", ""),
        )
        if (
            payload.get("is_execution_authorization") is not False
            or not report.verify()
        ):
            raise ValueError("Repository evolution preflight is invalid")
        return report
