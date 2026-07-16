"""Immutable content-addressed SourceDocument registry."""

from dataclasses import asdict, replace
from hashlib import sha256
import json
from pathlib import Path

from app.architecture.persistence import atomic_write
from app.knowledge.ingestion.models import AcquisitionResult, SourceDocument


class DocumentRegistry:
    def __init__(self, root: Path) -> None:
        self.root = root

    def register(
        self, result: AcquisitionResult, *, storage_uri: str | None = None,
    ) -> tuple[SourceDocument, Path]:
        versions = sorted((self.root / "records" / result.record_id).glob("v*.json"))
        for path in versions:
            data = json.loads(path.read_text(encoding="utf-8"))
            if result.content_hash and data.get("content_hash") == result.content_hash:
                document = SourceDocument(**data)
                if not self.verify(document):
                    raise ValueError("SourceDocument integrity verification failed")
                return document, path
        version = len(versions) + 1
        blob_path = None
        if result.content is not None and result.content_hash:
            blob = self.root / "blobs" / result.content_hash[:2] / f"{result.content_hash}.pdf"
            if blob.exists() and sha256(blob.read_bytes()).hexdigest() != result.content_hash:
                raise RuntimeError("Document blob integrity conflict")
            if not blob.exists():
                atomic_write(blob, result.content)
            blob_path = str(blob.relative_to(self.root)).replace("\\", "/")
        identity = f"{result.record_id}:{version}:{result.content_hash or result.status.value}"
        document = SourceDocument(
            f"document-{sha256(identity.encode()).hexdigest()[:24]}", result.record_id,
            version, result.status, result.acquired_at, result.source_url,
            result.source_provider, result.source_response_hash, result.license,
            result.media_type, result.content_hash, result.byte_size, blob_path,
            result.reason, result.final_url, result.http_status,
            result.redirect_chain, result.declared_content_length,
            result.retrieval_method, result.source_definition_id,
            result.query_family_id,
            result.response_headers, result.content_encoding,
            result.capture_manifest_hash, storage_uri,
            schema_version="1.1",
        )
        document = replace(document, manifest_hash=document.expected_manifest_hash())
        path = self.root / "records" / result.record_id / f"v{version:05d}.json"
        payload = json.dumps(asdict(document), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        atomic_write(path, payload)
        return document, path

    def verify(self, document: SourceDocument) -> bool:
        if document.schema_version != "1.0":
            if (
                not document.manifest_hash
                or document.manifest_hash != document.expected_manifest_hash()
            ):
                return False
        if document.status.value != "acquired":
            return (
                document.status.value in {"metadata_only", "failed"}
                and not document.blob_path
                and not document.storage_uri
                and not document.content_hash
            )
        if not document.content_hash or not document.blob_path:
            return False
        blob = self.root / document.blob_path
        return (
            blob.is_file()
            and sha256(blob.read_bytes()).hexdigest() == document.content_hash
            and document.capture_manifest_hash is not None
        )

    def get(self, document_id: str) -> SourceDocument:
        for path in (self.root / "records").rglob("v*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("document_id") == document_id:
                document = SourceDocument(**data)
                if not self.verify(document):
                    raise ValueError("SourceDocument integrity verification failed")
                return document
        raise KeyError(f"Unknown source document: {document_id}")

    def read_verified_content(self, document: SourceDocument) -> bytes:
        if not document.blob_path or not self.verify(document):
            raise ValueError("SourceDocument has no verified acquired content")
        return (self.root / document.blob_path).read_bytes()
