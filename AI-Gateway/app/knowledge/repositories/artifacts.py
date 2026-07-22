"""Storage-neutral canonical artifact lifecycle contracts."""

from dataclasses import dataclass


ARTIFACT_LIFECYCLE_TRANSITIONS = {
    "planned": "draft",
    "draft": "review",
    "review": "validated",
    "validated": "ratified",
    "ratified": "published",
    "published": "deprecated",
    "deprecated": "archived",
}
ARTIFACT_LIFECYCLE_STATES = frozenset(
    (*ARTIFACT_LIFECYCLE_TRANSITIONS, "archived")
)


def next_artifact_status(status: str) -> str | None:
    """Return the sole SGF-040-permitted next state, if one exists."""
    return ARTIFACT_LIFECYCLE_TRANSITIONS.get(status)


def require_artifact_transition(from_status: str, to_status: str) -> None:
    """Fail closed unless the requested edge is the canonical next transition."""
    expected = next_artifact_status(from_status)
    if expected != to_status:
        raise ValueError(
            f"Invalid artifact transition: {from_status} -> {to_status}; "
            f"expected {expected}"
        )


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
