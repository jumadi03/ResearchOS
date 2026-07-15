"""Canonical SK-001B metadata contracts."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.knowledge.models import ProviderFailure


class LifecycleSignal(StrEnum):
    ACTIVE = "active"
    CORRECTED = "corrected"
    RETRACTED = "retracted"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class MetadataObservation:
    record_id: str
    provider: str
    source_id: str
    response_hash: str
    values: dict[str, Any]


@dataclass(frozen=True, slots=True)
class MetadataConflict:
    record_id: str
    field: str
    values_by_provider: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class CitationEdge:
    citing_record_id: str
    cited_identifier: str
    provider: str
    response_hash: str


@dataclass(frozen=True, slots=True)
class EnrichedMetadata:
    record_id: str
    identifiers: tuple[tuple[str, str], ...]
    concepts: tuple[str, ...]
    citation_count: int | None
    open_access: bool | None
    lifecycle: LifecycleSignal
    observations: tuple[MetadataObservation, ...]
    conflicts: tuple[MetadataConflict, ...]


@dataclass(frozen=True, slots=True)
class MetadataRun:
    metadata_run_id: str
    discovery_run_id: str
    created_at: str
    records: tuple[EnrichedMetadata, ...]
    citation_edges: tuple[CitationEdge, ...]
    failures: tuple[ProviderFailure, ...] = ()
    schema_version: str = "1.0"
