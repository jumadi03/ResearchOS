"""Storage-neutral canonical artifact lifecycle contracts."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ArtifactLifecycleEvent:
    lifecycle_event_id: str
    artifact_id: str
    from_status: str | None
    to_status: str
    actor_id: str
    rationale: str
    occurred_at: str
    provenance_id: str
