"""Non-mutating recovery governance for FMA-008."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from hashlib import sha256
import json

from app.architecture.schema import (
    REPOSITORY_EVOLUTION_RECOVERY_EXECUTION_SCHEMA,
    REPOSITORY_EVOLUTION_RECOVERY_SCHEMA,
)

from .evolution_dry_run_models import (
    RepositoryDryRunDirection,
    RepositoryDryRunStep,
    RepositoryEvolutionDryRun,
)
from .evolution_execution_models import (
    RepositoryEvolutionExecution,
    RepositoryExecutionStatus,
)
from .evolution_post_verification import (
    RepositoryEvolutionPostVerification,
    RepositoryPostVerificationOutcome,
)


def _valid_hash(value: str) -> bool:
    return len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


class RepositoryRecoveryDecision(StrEnum):
    NO_ACTION = "no_action"
    AUTOMATIC_ROLLBACK_ELIGIBLE = "automatic_rollback_eligible"
    MANUAL_RECOVERY_REQUIRED = "manual_recovery_required"
    CANONICAL_REVALIDATION_REQUIRED = "canonical_revalidation_required"
    BLOCKED = "blocked"


class RepositoryRecoveryExecutionStatus(StrEnum):
    RECOVERED = "recovered"
    FAILED_SAFE = "failed_safe"
    RESTORED_MIGRATED_STATE = "restored_migrated_state"
    RECOVERY_REQUIRED = "recovery_required"


@dataclass(frozen=True, slots=True)
class RepositoryEvolutionRecovery:
    recovery_id: str
    project_name: str
    execution_id: str
    execution_hash: str
    execution_status: RepositoryExecutionStatus
    dry_run_id: str
    dry_run_hash: str
    post_verification_id: str | None
    post_verification_hash: str | None
    post_verification_outcome: RepositoryPostVerificationOutcome | None
    decision: RepositoryRecoveryDecision
    reasons: tuple[str, ...]
    rollback_steps: tuple[RepositoryDryRunStep, ...] = ()
    schema_version: str = "1.0"
    content_hash: str = ""

    @property
    def authorizes_recovery_execution(self) -> bool:
        return False

    def canonical_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "project_name": self.project_name,
            "execution_id": self.execution_id,
            "execution_hash": self.execution_hash,
            "execution_status": self.execution_status,
            "dry_run_id": self.dry_run_id,
            "dry_run_hash": self.dry_run_hash,
            "post_verification_id": self.post_verification_id,
            "post_verification_hash": self.post_verification_hash,
            "post_verification_outcome": self.post_verification_outcome,
            "decision": self.decision,
            "reasons": list(self.reasons),
            "rollback_steps": [
                asdict(item) for item in self.rollback_steps
            ],
        }

    def calculate_content_hash(self) -> str:
        return sha256(json.dumps(
            self.canonical_payload(),
            ensure_ascii=False, separators=(",", ":"), sort_keys=True,
        ).encode("utf-8")).hexdigest()

    def finalized(self) -> "RepositoryEvolutionRecovery":
        candidate = replace(
            self, recovery_id="", reasons=tuple(sorted(set(self.reasons))),
            content_hash="",
        )
        content_hash = candidate.calculate_content_hash()
        return replace(
            candidate,
            recovery_id=(
                f"repository-recovery:{self.project_name}:{content_hash[:16]}"
            ),
            content_hash=content_hash,
        )

    def verify(self) -> bool:
        has_post = bool(
            self.post_verification_id
            and self.post_verification_hash
            and self.post_verification_outcome is not None
        )
        no_post = (
            self.post_verification_id is None
            and self.post_verification_hash is None
            and self.post_verification_outcome is None
        )
        expected = self._expected_decision(has_post)
        needs_steps = (
            expected is RepositoryRecoveryDecision.AUTOMATIC_ROLLBACK_ELIGIBLE
        )
        return (
            bool(
                self.project_name.strip()
                and self.execution_id.strip()
                and _valid_hash(self.execution_hash)
                and self.dry_run_id.strip()
                and _valid_hash(self.dry_run_hash)
                and self.reasons
                and all(reason.strip() for reason in self.reasons)
            )
            and (has_post or no_post)
            and (
                self.post_verification_hash is None
                or _valid_hash(self.post_verification_hash)
            )
            and self.decision is expected
            and bool(self.rollback_steps) is needs_steps
            and all(
                item.verify()
                and item.direction is RepositoryDryRunDirection.ROLLBACK
                for item in self.rollback_steps
            )
            and not self.authorizes_recovery_execution
            and self == self.finalized()
        )

    def _expected_decision(self, has_post: bool) -> RepositoryRecoveryDecision:
        if self.execution_status is RepositoryExecutionStatus.RECOVERY_REQUIRED:
            return RepositoryRecoveryDecision.MANUAL_RECOVERY_REQUIRED
        if self.execution_status in {
            RepositoryExecutionStatus.ROLLED_BACK,
            RepositoryExecutionStatus.FAILED_SAFE,
        }:
            return RepositoryRecoveryDecision.CANONICAL_REVALIDATION_REQUIRED
        if not has_post:
            return RepositoryRecoveryDecision.BLOCKED
        if (
            self.post_verification_outcome
            is RepositoryPostVerificationOutcome.VERIFIED
        ):
            return RepositoryRecoveryDecision.NO_ACTION
        return RepositoryRecoveryDecision.AUTOMATIC_ROLLBACK_ELIGIBLE

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(
            {
                "recovery_id": self.recovery_id,
                "content_hash": self.content_hash,
                "authorizes_recovery_execution": (
                    self.authorizes_recovery_execution
                ),
                **self.canonical_payload(),
            },
            ensure_ascii=False, indent=indent, sort_keys=True,
        )

    @classmethod
    def from_json(cls, value: str) -> "RepositoryEvolutionRecovery":
        payload = json.loads(value)
        REPOSITORY_EVOLUTION_RECOVERY_SCHEMA.require_readable(
            payload.get("schema_version", "")
        )
        result = cls(
            recovery_id=payload.get("recovery_id", ""),
            project_name=payload["project_name"],
            execution_id=payload["execution_id"],
            execution_hash=payload["execution_hash"],
            execution_status=RepositoryExecutionStatus(
                payload["execution_status"]
            ),
            dry_run_id=payload["dry_run_id"],
            dry_run_hash=payload["dry_run_hash"],
            post_verification_id=payload.get("post_verification_id"),
            post_verification_hash=payload.get("post_verification_hash"),
            post_verification_outcome=(
                RepositoryPostVerificationOutcome(
                    payload["post_verification_outcome"]
                )
                if payload.get("post_verification_outcome") else None
            ),
            decision=RepositoryRecoveryDecision(payload["decision"]),
            reasons=tuple(payload["reasons"]),
            rollback_steps=tuple(
                RepositoryDryRunStep(
                    **{
                        **item,
                        "direction": RepositoryDryRunDirection(
                            item["direction"]
                        ),
                    }
                )
                for item in payload.get("rollback_steps", ())
            ),
            schema_version=payload.get("schema_version", ""),
            content_hash=payload.get("content_hash", ""),
        )
        if (
            payload.get("authorizes_recovery_execution") is not False
            or not result.verify()
        ):
            raise ValueError("Repository recovery decision is invalid")
        return result


class RepositoryEvolutionRecoveryPlanner:
    def decide(
        self,
        execution: RepositoryEvolutionExecution,
        dry_run: RepositoryEvolutionDryRun,
        post_verification: RepositoryEvolutionPostVerification | None = None,
    ) -> RepositoryEvolutionRecovery:
        if not execution.verify() or not dry_run.verify():
            raise ValueError("Verified execution and dry run are required")
        if not (
            execution.project_name == dry_run.project_name
            and execution.dry_run_id == dry_run.dry_run_id
            and execution.dry_run_hash == dry_run.content_hash
        ):
            raise ValueError("Recovery execution and dry-run provenance do not match")
        if post_verification is not None:
            if not post_verification.verify():
                raise ValueError("Verified post-migration result is required")
            if not (
                post_verification.project_name == execution.project_name
                and post_verification.execution_id == execution.execution_id
                and post_verification.execution_hash == execution.content_hash
            ):
                raise ValueError(
                    "Recovery post-verification provenance does not match"
                )

        post_outcome = (
            post_verification.outcome if post_verification else None
        )
        decision, reasons = self._decision(execution.status, post_outcome)
        steps = (
            dry_run.rollback_steps
            if decision
            is RepositoryRecoveryDecision.AUTOMATIC_ROLLBACK_ELIGIBLE
            else ()
        )
        result = RepositoryEvolutionRecovery(
            "", execution.project_name, execution.execution_id,
            execution.content_hash, execution.status, dry_run.dry_run_id,
            dry_run.content_hash,
            post_verification.verification_id if post_verification else None,
            post_verification.content_hash if post_verification else None,
            post_outcome, decision, reasons, steps,
        ).finalized()
        if not result.verify():
            raise ValueError("Repository recovery decision integrity failed")
        return result

    @staticmethod
    def _decision(status, post_outcome):
        if status is RepositoryExecutionStatus.RECOVERY_REQUIRED:
            return (
                RepositoryRecoveryDecision.MANUAL_RECOVERY_REQUIRED,
                ("rollback_incomplete_manual_recovery_required",),
            )
        if status in {
            RepositoryExecutionStatus.ROLLED_BACK,
            RepositoryExecutionStatus.FAILED_SAFE,
        }:
            return (
                RepositoryRecoveryDecision.CANONICAL_REVALIDATION_REQUIRED,
                ("execution_did_not_complete_revalidate_canonical_state",),
            )
        if post_outcome is None:
            return (
                RepositoryRecoveryDecision.BLOCKED,
                ("post_migration_verification_required",),
            )
        if post_outcome is RepositoryPostVerificationOutcome.VERIFIED:
            return (
                RepositoryRecoveryDecision.NO_ACTION,
                ("migration_verified_no_recovery_needed",),
            )
        return (
            RepositoryRecoveryDecision.AUTOMATIC_ROLLBACK_ELIGIBLE,
            ("post_migration_verification_blocked",),
        )


@dataclass(frozen=True, slots=True)
class RepositoryRecoveryExecution:
    recovery_execution_id: str
    project_name: str
    recovery_id: str
    recovery_hash: str
    execution_id: str
    execution_hash: str
    dry_run_id: str
    dry_run_hash: str
    workspace_fingerprint: str
    status: RepositoryRecoveryExecutionStatus
    events: tuple["RepositoryExecutionEvent", ...]
    schema_version: str = "1.0"
    content_hash: str = ""

    @property
    def requires_manual_recovery(self) -> bool:
        return self.status is RepositoryRecoveryExecutionStatus.RECOVERY_REQUIRED

    def canonical_payload(self):
        return {
            "schema_version": self.schema_version,
            "project_name": self.project_name,
            "recovery_id": self.recovery_id,
            "recovery_hash": self.recovery_hash,
            "execution_id": self.execution_id,
            "execution_hash": self.execution_hash,
            "dry_run_id": self.dry_run_id,
            "dry_run_hash": self.dry_run_hash,
            "workspace_fingerprint": self.workspace_fingerprint,
            "status": self.status,
            "events": [asdict(item) for item in self.events],
        }

    def calculate_content_hash(self):
        return sha256(json.dumps(
            self.canonical_payload(), ensure_ascii=False,
            separators=(",", ":"), sort_keys=True,
        ).encode("utf-8")).hexdigest()

    def finalized(self):
        candidate = replace(
            self, recovery_execution_id="", content_hash="",
        )
        content_hash = candidate.calculate_content_hash()
        return replace(
            candidate,
            recovery_execution_id=(
                f"repository-recovery-execution:{self.project_name}:"
                f"{content_hash[:16]}"
            ),
            content_hash=content_hash,
        )

    def verify(self):
        from .evolution_execution_models import (
            RepositoryExecutionAction,
            RepositoryExecutionOutcome,
        )
        rollback = sum(
            item.action is RepositoryExecutionAction.ROLLBACK
            and item.outcome is RepositoryExecutionOutcome.MOVED
            for item in self.events
        )
        compensated = sum(
            item.action is RepositoryExecutionAction.FORWARD
            and item.outcome is RepositoryExecutionOutcome.MOVED
            for item in self.events
        )
        failures = sum(
            item.outcome is RepositoryExecutionOutcome.FAILED
            for item in self.events
        )
        expected = (
            RepositoryRecoveryExecutionStatus.RECOVERED
            if failures == 0
            else RepositoryRecoveryExecutionStatus.FAILED_SAFE
            if rollback == 0
            else RepositoryRecoveryExecutionStatus.RESTORED_MIGRATED_STATE
            if compensated == rollback
            else RepositoryRecoveryExecutionStatus.RECOVERY_REQUIRED
        )
        return (
            bool(
                self.project_name.strip()
                and self.recovery_id.strip()
                and _valid_hash(self.recovery_hash)
                and self.execution_id.strip()
                and _valid_hash(self.execution_hash)
                and self.dry_run_id.strip()
                and _valid_hash(self.dry_run_hash)
                and _valid_hash(self.workspace_fingerprint)
                and self.events
            )
            and [item.sequence for item in self.events]
            == list(range(1, len(self.events) + 1))
            and all(item.verify() for item in self.events)
            and self.status is expected
            and self == self.finalized()
        )

    def to_json(self, *, indent=2):
        return json.dumps(
            {
                "recovery_execution_id": self.recovery_execution_id,
                "content_hash": self.content_hash,
                "requires_manual_recovery": self.requires_manual_recovery,
                **self.canonical_payload(),
            },
            ensure_ascii=False, indent=indent, sort_keys=True,
        )

    @classmethod
    def from_json(cls, value):
        from .evolution_execution_models import (
            RepositoryExecutionAction,
            RepositoryExecutionEvent,
            RepositoryExecutionOutcome,
        )
        payload = json.loads(value)
        REPOSITORY_EVOLUTION_RECOVERY_EXECUTION_SCHEMA.require_readable(
            payload.get("schema_version", "")
        )
        result = cls(
            payload.get("recovery_execution_id", ""),
            payload["project_name"], payload["recovery_id"],
            payload["recovery_hash"], payload["execution_id"],
            payload["execution_hash"], payload["dry_run_id"],
            payload["dry_run_hash"], payload["workspace_fingerprint"],
            RepositoryRecoveryExecutionStatus(payload["status"]),
            tuple(
                RepositoryExecutionEvent(
                    **{
                        **item,
                        "action": RepositoryExecutionAction(item["action"]),
                        "outcome": RepositoryExecutionOutcome(item["outcome"]),
                    }
                )
                for item in payload["events"]
            ),
            payload.get("schema_version", ""),
            payload.get("content_hash", ""),
        )
        if (
            payload.get("requires_manual_recovery")
            is not result.requires_manual_recovery
            or not result.verify()
        ):
            raise ValueError("Repository recovery execution is invalid")
        return result
