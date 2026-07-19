from hashlib import sha256
from types import SimpleNamespace

import pytest

from app.knowledge.repositories.minio import MinioScientificObjectStore
from app.knowledge.repositories.models import StoredRepresentation


class UnavailableObjectStorage:
    exceptions = SimpleNamespace(ClientError=RuntimeError)

    def head_object(self, **_values):
        raise ConnectionError("object storage unavailable")

    def get_object(self, **_values):
        raise ConnectionError("object storage unavailable")


def unavailable_store() -> MinioScientificObjectStore:
    store = object.__new__(MinioScientificObjectStore)
    store.bucket = "researchos-documents"
    store.client = UnavailableObjectStorage()
    return store


def test_object_storage_write_outage_creates_no_success_uri() -> None:
    content = b"canonical scientific representation"
    with pytest.raises(ConnectionError, match="object storage unavailable"):
        unavailable_store().put_bytes(
            content,
            media_type="application/pdf",
            checksum_sha256=sha256(content).hexdigest(),
            extension="pdf",
            namespace="representations",
        )


def test_object_storage_read_outage_creates_no_fallback_payload() -> None:
    content = b"canonical scientific representation"
    digest = sha256(content).hexdigest()
    representation = StoredRepresentation(
        representation_id="representation-outage-test",
        object_id="document-outage-test",
        representation_type="pdf",
        storage_uri=f"s3://researchos-documents/representations/{digest[:2]}/{digest}.pdf",
        media_type="application/pdf",
        checksum_sha256=digest,
        file_size=len(content),
        document_version=1,
    )

    with pytest.raises(ConnectionError, match="object storage unavailable"):
        unavailable_store().read_verified(representation)
