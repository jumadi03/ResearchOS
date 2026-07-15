"""Canonical semantic indexing job contract."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SemanticIndexJob:
    job_id: str
    object_type: str
    object_id: str
    canonical_object_id: str
    content_hash: str
    model: str
    dimensions: int
    status: str


@dataclass(frozen=True, slots=True)
class SemanticSearchHit:
    canonical_object_id: str
    stable_key: str
    object_type: str
    object_id: str
    content_hash: str
    model: str
    similarity: float
    metadata: dict
    provenance_id: str | None
    attributed_actor: str | None
