"""Canonical document acquisition contracts."""

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256


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
    source_definition_id: str | None = None
    query_family_id: str | None = None
    retrieval_method: str = "https_pdf"


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
    final_url: str | None = None
    http_status: int | None = None
    redirect_chain: tuple[str, ...] = ()
    declared_content_length: int | None = None
    retrieval_method: str | None = None
    source_definition_id: str | None = None
    query_family_id: str | None = None

    def __post_init__(self) -> None:
        if self.status is AcquisitionStatus.ACQUIRED:
            if (
                self.content is None
                or not self.content_hash
                or self.byte_size != len(self.content)
                or self.content_hash != sha256(self.content).hexdigest()
                or not self.media_type
                or not self.final_url
                or self.http_status is None
                or not self.retrieval_method
                or not self.source_definition_id
                or not self.query_family_id
            ):
                raise ValueError(
                    "Acquired representation provenance is incomplete"
                )
        elif self.content is not None or self.content_hash or self.byte_size:
            raise ValueError(
                "Non-acquired result must not carry representation bytes"
            )


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
    final_url: str | None = None
    http_status: int | None = None
    redirect_chain: tuple[str, ...] = ()
    declared_content_length: int | None = None
    retrieval_method: str | None = None
    source_definition_id: str | None = None
    query_family_id: str | None = None
    schema_version: str = "1.0"

    def __post_init__(self) -> None:
        object.__setattr__(self, "redirect_chain", tuple(self.redirect_chain))
