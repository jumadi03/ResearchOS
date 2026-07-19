from dataclasses import asdict
import json
from pathlib import Path

from app.knowledge.ingestion.acquisition import DocumentAcquirer
from app.knowledge.ingestion.models import (
    AccessStatus, AcquisitionStatus, DocumentCandidate,
)
from app.knowledge.ingestion.registry import DocumentRegistry


class Response:
    headers = {
        "Content-Type": "application/pdf; charset=binary",
        "ETag": '"capture-v1"',
        "Set-Cookie": "must-not-be-retained=secret",
    }
    content = b"%PDF-1.7\nvalid"
    url = "https://example.test/paper.pdf"
    status_code = 200
    history = ()

    def raise_for_status(self):
        return None


def candidate(**changes):
    values = dict(
        record_id="record", url="https://example.test/paper.pdf",
        access_status=AccessStatus.OPEN, license="CC-BY-4.0",
        source_provider="openalex", source_response_hash="hash",
        source_definition_id="source-openalex",
        query_family_id="query-family-1",
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
    assert first.content_encoding == "binary"
    assert first.response_headers == (
        ("content-type", "application/pdf; charset=binary"),
        ("etag", '"capture-v1"'),
    )
    assert first.capture_manifest_hash
    assert first.manifest_hash


def test_document_manifest_tampering_is_rejected(tmp_path: Path) -> None:
    registry = DocumentRegistry(tmp_path)
    result = DocumentAcquirer(
        transport=lambda *args, **kwargs: Response(),
    ).acquire(candidate(), acquired_at="time")
    document, path = registry.register(result)
    tampered = asdict(document)
    tampered["final_url"] = "https://attacker.test/replaced.pdf"
    path.write_text(json.dumps(tampered), encoding="utf-8")

    try:
        registry.get(document.document_id)
    except ValueError as exc:
        assert "integrity verification failed" in str(exc)
    else:
        raise AssertionError("Tampered raw-capture manifest was accepted")


def test_fresh_capture_supersedes_unverifiable_legacy_record(tmp_path: Path) -> None:
    result = DocumentAcquirer(
        transport=lambda *args, **kwargs: Response(),
    ).acquire(candidate(), acquired_at="new-time")
    legacy_blob = tmp_path / "blobs" / result.content_hash[:2] / (
        result.content_hash + ".pdf"
    )
    legacy_blob.parent.mkdir(parents=True)
    legacy_blob.write_bytes(result.content)
    legacy_path = tmp_path / "records" / result.record_id / "v00001.json"
    legacy_path.parent.mkdir(parents=True)
    legacy_path.write_text(json.dumps({
        "document_id": "document-legacy",
        "record_id": result.record_id,
        "version": 1,
        "status": "acquired",
        "acquired_at": "old-time",
        "source_url": result.source_url,
        "source_provider": result.source_provider,
        "source_response_hash": result.source_response_hash,
        "license": result.license,
        "media_type": result.media_type,
        "content_hash": result.content_hash,
        "byte_size": result.byte_size,
        "blob_path": str(legacy_blob.relative_to(tmp_path)).replace("\\", "/"),
        "reason": None,
        "schema_version": "1.0",
    }), encoding="utf-8")

    upgraded, upgraded_path = DocumentRegistry(tmp_path).register(result)

    assert upgraded.version == 2
    assert upgraded.document_id != "document-legacy"
    assert upgraded.capture_manifest_hash == result.capture_manifest_hash
    assert upgraded.schema_version == "1.1"
    assert upgraded_path.name == "v00002.json"
    assert legacy_path.exists()
    assert DocumentRegistry(tmp_path).verify(upgraded)


def test_same_bytes_with_new_capture_create_a_new_document_version(
    tmp_path: Path,
) -> None:
    acquirer = DocumentAcquirer(
        transport=lambda *args, **kwargs: Response(),
    )
    first, _ = DocumentRegistry(tmp_path).register(
        acquirer.acquire(candidate(), acquired_at="first-time")
    )
    second, _ = DocumentRegistry(tmp_path).register(
        acquirer.acquire(candidate(), acquired_at="second-time")
    )

    assert first.content_hash == second.content_hash
    assert first.capture_manifest_hash != second.capture_manifest_hash
    assert second.version == 2
    assert second.document_id != first.document_id


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


def test_declared_oversize_is_rejected_before_content_is_read() -> None:
    class Oversized(Response):
        headers = {
            "Content-Type": "application/pdf",
            "Content-Length": "1000",
        }

        @property
        def content(self):
            raise AssertionError("Oversized body must not be read")

    result = DocumentAcquirer(
        transport=lambda *args, **kwargs: Oversized(), max_bytes=100,
    ).acquire(candidate(), acquired_at="time")

    assert result.status is AcquisitionStatus.FAILED
    assert result.reason == "Declared content length exceeds size limit"
    assert result.declared_content_length == 1000


def test_redirect_to_unsafe_url_is_rejected_and_recorded() -> None:
    class UnsafeRedirect(Response):
        headers = {"Location": "http://127.0.0.1/private.pdf"}
        status_code = 302

    requested = []
    result = DocumentAcquirer(
        transport=lambda url, **kwargs: (
            requested.append((url, kwargs)) or UnsafeRedirect()
        ),
    ).acquire(candidate(), acquired_at="time")

    assert result.status is AcquisitionStatus.FAILED
    assert result.reason == "Redirect or final URL is not a safe HTTPS URL"
    assert result.redirect_chain == ("https://example.test/paper.pdf",)
    assert result.final_url == "http://127.0.0.1/private.pdf"
    assert requested == [(
        "https://example.test/paper.pdf",
        {"timeout": 30.0, "allow_redirects": False},
    )]
