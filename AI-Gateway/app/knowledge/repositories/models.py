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
