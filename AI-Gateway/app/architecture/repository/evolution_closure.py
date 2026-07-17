"""Attributable, fail-closed lifecycle closure audit for FMA-008."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
import json

from app.architecture.schema import REPOSITORY_EVOLUTION_CLOSURE_SCHEMA

from .evolution_execution_models import (
    RepositoryEvolutionExecution,
    RepositoryExecutionStatus,
)
from .evolution_models import RepositoryEvolutionPlan
from .evolution_post_recovery import (
    RepositoryPostRecoveryOutcome,
    RepositoryPostRecoveryVerification,
)
from .evolution_post_verification import (
    RepositoryEvolutionPostVerification,
    RepositoryPostVerificationOutcome,
)
from .evolution_recovery import (
    RepositoryEvolutionRecovery,
    RepositoryRecoveryDecision,
    RepositoryRecoveryExecution,
    RepositoryRecoveryExecutionStatus,
)


def _valid_hash(value: str | None) -> bool:
    return bool(
        value
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _attributed(decided_by: str, rationale: str, decided_at: str) -> bool:
    if not decided_by.strip() or not rationale.strip() or not decided_at.strip():
        return False
    try:
        timestamp = datetime.fromisoformat(decided_at)
    except ValueError:
        return False
    return timestamp.tzinfo is not None and timestamp.utcoffset() is not None


class RepositoryClosurePath(StrEnum):
    MIGRATION = "migration"
    RECOVERY = "recovery"


class RepositoryClosureOutcome(StrEnum):
    CLOSED = "closed"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class RepositoryClosureCheck:
    check_id: str
    passed: bool
    reason: str

    def verify(self) -> bool:
        return bool(self.check_id.strip() and self.reason.strip())


@dataclass(frozen=True, slots=True)
class RepositoryEvolutionClosure:
    closure_id: str
    project_name: str
    plan_id: str
    plan_hash: str
    execution_id: str
    execution_hash: str
    post_verification_id: str
    post_verification_hash: str
    closure_path: RepositoryClosurePath
    recovery_id: str | None
    recovery_hash: str | None
    recovery_execution_id: str | None
    recovery_execution_hash: str | None
    post_recovery_id: str | None
    post_recovery_hash: str | None
    decided_by: str
    decision_rationale: str
    decided_at: str
    outcome: RepositoryClosureOutcome
    checks: tuple[RepositoryClosureCheck, ...]
    schema_version: str = "1.0"
    content_hash: str = ""

    @property
    def closes_migration_lifecycle(self) -> bool:
        return self.outcome is RepositoryClosureOutcome.CLOSED

    @property
    def authorizes_production_activation(self) -> bool:
        return False

    @property
    def mutates_repository(self) -> bool:
        return False

    def canonical_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "project_name": self.project_name,
            "plan_id": self.plan_id,
            "plan_hash": self.plan_hash,
            "execution_id": self.execution_id,
            "execution_hash": self.execution_hash,
            "post_verification_id": self.post_verification_id,
            "post_verification_hash": self.post_verification_hash,
            "closure_path": self.closure_path,
            "recovery_id": self.recovery_id,
            "recovery_hash": self.recovery_hash,
            "recovery_execution_id": self.recovery_execution_id,
            "recovery_execution_hash": self.recovery_execution_hash,
            "post_recovery_id": self.post_recovery_id,
            "post_recovery_hash": self.post_recovery_hash,
            "decided_by": self.decided_by,
            "decision_rationale": self.decision_rationale,
            "decided_at": self.decided_at,
            "outcome": self.outcome,
            "checks": [asdict(item) for item in self.checks],
        }

    def finalized(self) -> "RepositoryEvolutionClosure":
        candidate = replace(self, closure_id="", content_hash="")
        digest = sha256(json.dumps(
            candidate.canonical_payload(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")).hexdigest()
        return replace(
            candidate,
            closure_id=(
                f"repository-evolution-closure:{self.project_name}:"
                f"{digest[:16]}"
            ),
            content_hash=digest,
        )

    def verify(self) -> bool:
        check_ids = [item.check_id for item in self.checks]
        expected_checks = {
            "artifact_set_complete",
            "plan_execution_provenance_current",
            "verification_chain_current",
            "final_state_eligible",
            "human_decision_attributed",
        }
        expected_outcome = (
            RepositoryClosureOutcome.CLOSED
            if all(item.passed for item in self.checks)
            else RepositoryClosureOutcome.BLOCKED
        )
        recovery_values = (
            self.recovery_id,
            self.recovery_hash,
            self.recovery_execution_id,
            self.recovery_execution_hash,
            self.post_recovery_id,
            self.post_recovery_hash,
        )
        recovery_shape = (
            all(value is None for value in recovery_values)
            if self.closure_path is RepositoryClosurePath.MIGRATION
            else all(value is not None for value in recovery_values)
            and all(
                _valid_hash(value)
                for value in (
                    self.recovery_hash,
                    self.recovery_execution_hash,
                    self.post_recovery_hash,
                )
            )
        )
        return (
            bool(
                self.project_name.strip()
                and self.plan_id.strip()
                and _valid_hash(self.plan_hash)
                and self.execution_id.strip()
                and _valid_hash(self.execution_hash)
                and self.post_verification_id.strip()
                and _valid_hash(self.post_verification_hash)
                and _attributed(
                    self.decided_by,
                    self.decision_rationale,
                    self.decided_at,
                )
                and self.checks
            )
            and recovery_shape
            and set(check_ids) == expected_checks
            and len(check_ids) == len(expected_checks)
            and all(item.verify() for item in self.checks)
            and self.outcome is expected_outcome
            and not self.authorizes_production_activation
            and not self.mutates_repository
            and self == self.finalized()
        )

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(
            {
                "closure_id": self.closure_id,
                "content_hash": self.content_hash,
                "closes_migration_lifecycle": self.closes_migration_lifecycle,
                "authorizes_production_activation": (
                    self.authorizes_production_activation
                ),
                "mutates_repository": self.mutates_repository,
                **self.canonical_payload(),
            },
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    @classmethod
    def from_json(cls, value: str) -> "RepositoryEvolutionClosure":
        payload = json.loads(value)
        REPOSITORY_EVOLUTION_CLOSURE_SCHEMA.require_readable(
            payload.get("schema_version", "")
        )
        result = cls(
            closure_id=payload.get("closure_id", ""),
            project_name=payload["project_name"],
            plan_id=payload["plan_id"],
            plan_hash=payload["plan_hash"],
            execution_id=payload["execution_id"],
            execution_hash=payload["execution_hash"],
            post_verification_id=payload["post_verification_id"],
            post_verification_hash=payload["post_verification_hash"],
            closure_path=RepositoryClosurePath(payload["closure_path"]),
            recovery_id=payload.get("recovery_id"),
            recovery_hash=payload.get("recovery_hash"),
            recovery_execution_id=payload.get("recovery_execution_id"),
            recovery_execution_hash=payload.get("recovery_execution_hash"),
            post_recovery_id=payload.get("post_recovery_id"),
            post_recovery_hash=payload.get("post_recovery_hash"),
            decided_by=payload["decided_by"],
            decision_rationale=payload["decision_rationale"],
            decided_at=payload["decided_at"],
            outcome=RepositoryClosureOutcome(payload["outcome"]),
            checks=tuple(
                RepositoryClosureCheck(**item) for item in payload["checks"]
            ),
            schema_version=payload.get("schema_version", ""),
            content_hash=payload.get("content_hash", ""),
        )
        if (
            payload.get("closes_migration_lifecycle")
            is not result.closes_migration_lifecycle
            or payload.get("authorizes_production_activation") is not False
            or payload.get("mutates_repository") is not False
            or not result.verify()
        ):
            raise ValueError("Repository evolution closure is invalid")
        return result


class RepositoryEvolutionClosureAuditor:
    def audit(
        self,
        plan: RepositoryEvolutionPlan,
        execution: RepositoryEvolutionExecution,
        post_verification: RepositoryEvolutionPostVerification,
        *,
        decided_by: str,
        decision_rationale: str,
        decided_at: str,
        recovery: RepositoryEvolutionRecovery | None = None,
        recovery_execution: RepositoryRecoveryExecution | None = None,
        post_recovery: RepositoryPostRecoveryVerification | None = None,
    ) -> RepositoryEvolutionClosure:
        if not _attributed(decided_by, decision_rationale, decided_at):
            raise ValueError(
                "Attributable closure decision with timezone is required"
            )
        supplied = (recovery, recovery_execution, post_recovery)
        if not all((
            plan.verify(),
            execution.verify(),
            post_verification.verify(),
        )):
            raise ValueError("Verified closure inputs are required")
        if any(item is not None for item in supplied) and not all(
            item is not None for item in supplied
        ):
            raise ValueError("Complete recovery closure artifacts are required")
        if not all(item.verify() for item in supplied if item is not None):
            raise ValueError("Verified recovery closure artifacts are required")

        closure_path = (
            RepositoryClosurePath.RECOVERY
            if recovery is not None
            else RepositoryClosurePath.MIGRATION
        )
        base_provenance = (
            execution.project_name == plan.project_name
            and execution.plan_id == plan.plan_id
            and execution.plan_hash == plan.content_hash
        )
        post_chain = (
            post_verification.project_name == plan.project_name
            and post_verification.plan_id == plan.plan_id
            and post_verification.plan_hash == plan.content_hash
            and post_verification.execution_id == execution.execution_id
            and post_verification.execution_hash == execution.content_hash
        )
        recovery_chain = self._recovery_chain_current(
            plan,
            execution,
            post_verification,
            recovery,
            recovery_execution,
            post_recovery,
        )
        complete = (
            all(item is None for item in supplied)
            if closure_path is RepositoryClosurePath.MIGRATION
            else all(item is not None for item in supplied)
        )
        eligible = (
            execution.status is RepositoryExecutionStatus.COMPLETED
            and post_verification.outcome
            is RepositoryPostVerificationOutcome.VERIFIED
            and closure_path is RepositoryClosurePath.MIGRATION
            or closure_path is RepositoryClosurePath.RECOVERY
            and recovery is not None
            and recovery.decision
            is RepositoryRecoveryDecision.AUTOMATIC_ROLLBACK_ELIGIBLE
            and recovery_execution is not None
            and recovery_execution.status
            is RepositoryRecoveryExecutionStatus.RECOVERED
            and post_recovery is not None
            and post_recovery.outcome
            is RepositoryPostRecoveryOutcome.RECOVERED_VERIFIED
        )
        checks = (
            self._check(
                "artifact_set_complete",
                complete,
                "closure_artifact_set_complete",
                "closure_artifact_set_incomplete",
            ),
            self._check(
                "plan_execution_provenance_current",
                base_provenance,
                "plan_execution_provenance_matches",
                "plan_execution_provenance_is_stale",
            ),
            self._check(
                "verification_chain_current",
                post_chain and recovery_chain,
                "verification_chain_provenance_matches",
                "verification_chain_provenance_is_stale",
            ),
            self._check(
                "final_state_eligible",
                eligible,
                "final_state_is_eligible_for_closure",
                "final_state_is_not_eligible_for_closure",
            ),
            self._check(
                "human_decision_attributed",
                True,
                "closure_decision_is_attributed",
                "closure_decision_is_not_attributed",
            ),
        )
        outcome = (
            RepositoryClosureOutcome.CLOSED
            if all(item.passed for item in checks)
            else RepositoryClosureOutcome.BLOCKED
        )
        result = RepositoryEvolutionClosure(
            "",
            plan.project_name,
            plan.plan_id,
            plan.content_hash,
            execution.execution_id,
            execution.content_hash,
            post_verification.verification_id,
            post_verification.content_hash,
            closure_path,
            recovery.recovery_id if recovery else None,
            recovery.content_hash if recovery else None,
            (
                recovery_execution.recovery_execution_id
                if recovery_execution else None
            ),
            recovery_execution.content_hash if recovery_execution else None,
            post_recovery.verification_id if post_recovery else None,
            post_recovery.content_hash if post_recovery else None,
            decided_by,
            decision_rationale,
            decided_at,
            outcome,
            checks,
        ).finalized()
        if not result.verify():
            raise ValueError("Repository evolution closure integrity failed")
        return result

    @staticmethod
    def _recovery_chain_current(
        plan,
        execution,
        post_verification,
        recovery,
        recovery_execution,
        post_recovery,
    ) -> bool:
        if recovery is None:
            return recovery_execution is None and post_recovery is None
        if recovery_execution is None or post_recovery is None:
            return False
        return (
            recovery.project_name == plan.project_name
            and recovery.execution_id == execution.execution_id
            and recovery.execution_hash == execution.content_hash
            and recovery.post_verification_id
            == post_verification.verification_id
            and recovery.post_verification_hash
            == post_verification.content_hash
            and recovery_execution.project_name == plan.project_name
            and recovery_execution.recovery_id == recovery.recovery_id
            and recovery_execution.recovery_hash == recovery.content_hash
            and recovery_execution.execution_id == execution.execution_id
            and recovery_execution.execution_hash == execution.content_hash
            and post_recovery.project_name == plan.project_name
            and post_recovery.plan_id == plan.plan_id
            and post_recovery.plan_hash == plan.content_hash
            and post_recovery.recovery_id == recovery.recovery_id
            and post_recovery.recovery_hash == recovery.content_hash
            and post_recovery.recovery_execution_id
            == recovery_execution.recovery_execution_id
            and post_recovery.recovery_execution_hash
            == recovery_execution.content_hash
        )

    @staticmethod
    def _check(check_id, passed, success, failure):
        return RepositoryClosureCheck(
            check_id,
            passed,
            success if passed else failure,
        )
