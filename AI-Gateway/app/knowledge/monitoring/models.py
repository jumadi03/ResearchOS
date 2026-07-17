"""Canonical contracts for continuous scientific source monitoring."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from enum import StrEnum
from hashlib import sha256

from app.knowledge.discovery.normalization import canonical_json


class SourceWatchStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    EXPIRED = "expired"


class ScientificChangeKind(StrEnum):
    NEW_CANDIDATE = "new_candidate"
    METADATA_CHANGED = "metadata_changed"
    CITATION_CHANGED = "citation_changed"
    CORRECTED = "corrected"
    RETRACTED = "retracted"
    UNAVAILABLE = "unavailable"
    PROVIDER_FAILURE = "provider_failure"


@dataclass(frozen=True, slots=True)
class ScientificSourceWatch:
    watch_id: str
    project_id: str
    discovery_contract_id: str
    research_question_id: str
    search_plan_id: str
    cadence_minutes: int
    owner_id: str
    human_review_policy: str
    created_at: str
    next_run_at: str
    status: SourceWatchStatus = SourceWatchStatus.ACTIVE
    maximum_runs: int | None = None
    ends_at: str | None = None
    completed_runs: int = 0
    definition_hash: str = ""
    schema_version: str = "1.0"

    def expected_definition_hash(self) -> str:
        def timestamp(value: str | None) -> str | None:
            if value is None:
                return None
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.astimezone(timezone.utc).isoformat()

        immutable = {
            "watch_id": self.watch_id,
            "project_id": self.project_id,
            "discovery_contract_id": self.discovery_contract_id,
            "research_question_id": self.research_question_id,
            "search_plan_id": self.search_plan_id,
            "cadence_minutes": self.cadence_minutes,
            "owner_id": self.owner_id,
            "human_review_policy": self.human_review_policy,
            "created_at": timestamp(self.created_at),
            "maximum_runs": self.maximum_runs,
            "ends_at": timestamp(self.ends_at),
            "schema_version": self.schema_version,
        }
        return sha256(canonical_json(immutable).encode("utf-8")).hexdigest()

    def finalized(self) -> "ScientificSourceWatch":
        return replace(self, definition_hash=self.expected_definition_hash())

    def verify(self) -> bool:
        return (
            bool(self.watch_id.strip() and self.owner_id.strip())
            and self.cadence_minutes >= 15
            and (self.maximum_runs is None or self.maximum_runs > 0)
            and self.completed_runs >= 0
            and self.definition_hash == self.expected_definition_hash()
        )


@dataclass(frozen=True, slots=True)
class ScientificChange:
    change_id: str
    kind: ScientificChangeKind
    record_key: str
    provider: str | None
    before_hash: str | None
    after_hash: str | None
    details: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class MonitoringRun:
    monitoring_run_id: str
    watch_id: str
    scheduled_at: str
    started_at: str
    completed_at: str
    previous_discovery_run_id: str
    current_discovery_run_id: str
    changes: tuple[ScientificChange, ...]
    provider_failures: tuple[tuple[str, str, bool], ...]
    stopping_reason: str
    manifest_hash: str = ""
    schema_version: str = "1.0"

    def expected_manifest_hash(self) -> str:
        return sha256(canonical_json(
            asdict(replace(self, manifest_hash=""))
        ).encode("utf-8")).hexdigest()

    def finalized(self) -> "MonitoringRun":
        return replace(self, manifest_hash=self.expected_manifest_hash())

    def verify(self) -> bool:
        return (
            self.stopping_reason in {"complete", "partial_provider_failure"}
            and self.manifest_hash == self.expected_manifest_hash()
            and len({item.change_id for item in self.changes}) == len(self.changes)
        )
