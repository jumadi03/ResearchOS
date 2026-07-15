from pathlib import Path

from app.knowledge.ingestion.acquisition import DocumentAcquirer
from app.knowledge.ingestion.models import (
    AccessStatus, AcquisitionStatus, DocumentCandidate,
)
from app.knowledge.ingestion.registry import DocumentRegistry


class Response:
    headers = {"Content-Type": "application/pdf; charset=binary"}
    content = b"%PDF-1.7\nvalid"

    def raise_for_status(self):
        return None


def candidate(**changes):
    values = dict(
        record_id="record", url="https://example.test/paper.pdf",
        access_status=AccessStatus.OPEN, license="CC-BY-4.0",
        source_provider="openalex", source_response_hash="hash",
    )
    values.update(changes)
    return DocumentCandidate(**values)


def test_acquisition_is_content_addressed_versioned_and_verified(tmp_path: Path) -> None:
    acquirer = DocumentAcquirer(transport=lambda *args, **kwargs: Response())
    registry = DocumentRegistry(tmp_path)
    result = acquirer.acquire(candidate(), acquired_at="time")
    first, path = registry.register(result)
    repeated, repeated_path = registry.register(result)

    assert first.status is AcquisitionStatus.ACQUIRED
    assert first.version == 1
    assert first == repeated and path == repeated_path
    assert registry.verify(first)
    assert len(tuple((tmp_path / "blobs").rglob("*.pdf"))) == 1


def test_unknown_rights_create_metadata_only_entry_without_transport(tmp_path: Path) -> None:
    called = []
    result = DocumentAcquirer(transport=lambda *args, **kwargs: called.append(True)).acquire(
        candidate(access_status=AccessStatus.UNKNOWN, license=None), acquired_at="time"
    )
    document, _ = DocumentRegistry(tmp_path).register(result)
    assert result.status is AcquisitionStatus.METADATA_ONLY
    assert called == []
    assert document.blob_path is None
    assert DocumentRegistry(tmp_path).verify(document)


def test_invalid_pdf_is_failed_and_not_stored(tmp_path: Path) -> None:
    class Invalid(Response):
        content = b"html"

    result = DocumentAcquirer(transport=lambda *args, **kwargs: Invalid()).acquire(
        candidate(), acquired_at="time"
    )
    document, _ = DocumentRegistry(tmp_path).register(result)
    assert document.status is AcquisitionStatus.FAILED
    assert not (tmp_path / "blobs").exists()
