"""Canonical document acquisition contracts."""

from dataclasses import dataclass
from enum import StrEnum


class AccessStatus(StrEnum):
    OPEN = "open"
    RESTRICTED = "restricted"
    UNKNOWN = "unknown"


class AcquisitionStatus(StrEnum):
    ACQUIRED = "acquired"
    METADATA_ONLY = "metadata_only"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class DocumentCandidate:
    record_id: str
    url: str | None
    access_status: AccessStatus
    license: str | None
    source_provider: str
    source_response_hash: str


@dataclass(frozen=True, slots=True)
class AcquisitionResult:
    record_id: str
    status: AcquisitionStatus
    acquired_at: str
    source_url: str | None
    source_provider: str
    source_response_hash: str
    license: str | None
    media_type: str | None
    content_hash: str | None
    byte_size: int | None
    reason: str | None
    content: bytes | None = None


@dataclass(frozen=True, slots=True)
class SourceDocument:
    document_id: str
    record_id: str
    version: int
    status: AcquisitionStatus
    acquired_at: str
    source_url: str | None
    source_provider: str
    source_response_hash: str
    license: str | None
    media_type: str | None
    content_hash: str | None
    byte_size: int | None
    blob_path: str | None
    reason: str | None
    schema_version: str = "1.0"
