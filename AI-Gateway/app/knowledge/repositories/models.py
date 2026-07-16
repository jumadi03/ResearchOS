"""Storage-neutral representation contracts."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StoredRepresentation:
    representation_id: str
    object_id: str
    representation_type: str
    storage_uri: str
    media_type: str
    checksum_sha256: str
    file_size: int
    document_version: int
    source_url: str | None = None
    final_url: str | None = None
    retrieval_method: str | None = None
    retrieved_at: str | None = None
    http_status: int | None = None
    redirect_chain: tuple[str, ...] = ()
    response_headers: tuple[tuple[str, str], ...] = ()
    content_encoding: str | None = None
    license: str | None = None
    source_definition_id: str | None = None
    query_family_id: str | None = None
    capture_manifest_hash: str | None = None
