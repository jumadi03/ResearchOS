"""Immutable audit result contracts for isolated FMA-008 execution."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from hashlib import sha256
import json

from app.architecture.schema import REPOSITORY_EVOLUTION_EXECUTION_SCHEMA


def _valid_hash(value: str) -> bool:
    return len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


class RepositoryExecutionStatus(StrEnum):
    COMPLETED = "completed"
    ROLLED_BACK = "rolled_back"
    FAILED_SAFE = "failed_safe"
    RECOVERY_REQUIRED = "recovery_required"


class RepositoryExecutionAction(StrEnum):
    FORWARD = "forward"
    ROLLBACK = "rollback"


class RepositoryExecutionOutcome(StrEnum):
    MOVED = "moved"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class RepositoryExecutionEvent:
    sequence: int
    action: RepositoryExecutionAction
    file_id: str
    source_path: str
    target_path: str
    content_hash: str
    outcome: RepositoryExecutionOutcome
    reason: str

    def verify(self) -> bool:
        return (
            self.sequence >= 1
            and self.file_id.startswith("file:")
            and bool(
                self.source_path.strip()
                and self.target_path.strip()
                and self.source_path != self.target_path
                and _valid_hash(self.content_hash)
                and self.reason.strip()
            )
        )


@dataclass(frozen=True, slots=True)
class RepositoryEvolutionExecution:
    execution_id: str
    project_name: str
    plan_id: str
    plan_hash: str
    preflight_id: str
    preflight_hash: str
    dry_run_id: str
    dry_run_hash: str
    source_revision: str
    workspace_fingerprint: str
    status: RepositoryExecutionStatus
    events: tuple[RepositoryExecutionEvent, ...]
    schema_version: str = "1.0"
    content_hash: str = ""

    @property
    def requires_recovery(self) -> bool:
        return self.status is RepositoryExecutionStatus.RECOVERY_REQUIRED

    def canonical_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "project_name": self.project_name,
            "plan_id": self.plan_id,
            "plan_hash": self.plan_hash,
            "preflight_id": self.preflight_id,
            "preflight_hash": self.preflight_hash,
            "dry_run_id": self.dry_run_id,
            "dry_run_hash": self.dry_run_hash,
            "source_revision": self.source_revision,
            "workspace_fingerprint": self.workspace_fingerprint,
            "status": self.status,
            "events": [asdict(item) for item in self.events],
        }

    def calculate_content_hash(self) -> str:
        return sha256(json.dumps(
            self.canonical_payload(),
            ensure_ascii=False, separators=(",", ":"), sort_keys=True,
        ).encode("utf-8")).hexdigest()

    def finalized(self) -> "RepositoryEvolutionExecution":
        candidate = replace(self, execution_id="", content_hash="")
        content_hash = candidate.calculate_content_hash()
        return replace(
            candidate,
            execution_id=(
                f"repository-execution:{self.project_name}:{content_hash[:16]}"
            ),
            content_hash=content_hash,
        )

    def verify(self) -> bool:
        sequences = [item.sequence for item in self.events]
        forward_moved = sum(
            item.action is RepositoryExecutionAction.FORWARD
            and item.outcome is RepositoryExecutionOutcome.MOVED
            for item in self.events
        )
        rollback_moved = sum(
            item.action is RepositoryExecutionAction.ROLLBACK
            and item.outcome is RepositoryExecutionOutcome.MOVED
            for item in self.events
        )
        failures = sum(
            item.outcome is RepositoryExecutionOutcome.FAILED
            for item in self.events
        )
        expected_status = (
            RepositoryExecutionStatus.COMPLETED
            if failures == 0
            else RepositoryExecutionStatus.FAILED_SAFE
            if forward_moved == 0
            else RepositoryExecutionStatus.ROLLED_BACK
            if rollback_moved == forward_moved
            else RepositoryExecutionStatus.RECOVERY_REQUIRED
        )
        return (
            bool(
                self.project_name.strip()
                and self.plan_id.strip()
                and _valid_hash(self.plan_hash)
                and self.preflight_id.strip()
                and _valid_hash(self.preflight_hash)
                and self.dry_run_id.strip()
                and _valid_hash(self.dry_run_hash)
                and self.source_revision.strip()
                and _valid_hash(self.workspace_fingerprint)
                and self.events
            )
            and sequences == list(range(1, len(self.events) + 1))
            and all(item.verify() for item in self.events)
            and self.status is expected_status
            and self == self.finalized()
        )

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(
            {
                "execution_id": self.execution_id,
                "content_hash": self.content_hash,
                "requires_recovery": self.requires_recovery,
                **self.canonical_payload(),
            },
            ensure_ascii=False, indent=indent, sort_keys=True,
        )

    @classmethod
    def from_json(cls, value: str) -> "RepositoryEvolutionExecution":
        payload = json.loads(value)
        REPOSITORY_EVOLUTION_EXECUTION_SCHEMA.require_readable(
            payload.get("schema_version", "")
        )
        result = cls(
            execution_id=payload.get("execution_id", ""),
            project_name=payload["project_name"],
            plan_id=payload["plan_id"],
            plan_hash=payload["plan_hash"],
            preflight_id=payload["preflight_id"],
            preflight_hash=payload["preflight_hash"],
            dry_run_id=payload["dry_run_id"],
            dry_run_hash=payload["dry_run_hash"],
            source_revision=payload["source_revision"],
            workspace_fingerprint=payload["workspace_fingerprint"],
            status=RepositoryExecutionStatus(payload["status"]),
            events=tuple(
                RepositoryExecutionEvent(
                    **{
                        **item,
                        "action": RepositoryExecutionAction(item["action"]),
                        "outcome": RepositoryExecutionOutcome(item["outcome"]),
                    }
                )
                for item in payload["events"]
            ),
            schema_version=payload.get("schema_version", ""),
            content_hash=payload.get("content_hash", ""),
        )
        if (
            payload.get("requires_recovery") is not result.requires_recovery
            or not result.verify()
        ):
            raise ValueError("Repository evolution execution is invalid")
        return result
