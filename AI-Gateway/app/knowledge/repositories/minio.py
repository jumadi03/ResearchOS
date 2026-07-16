"""Immutable content-addressed object storage for scientific representations."""

from __future__ import annotations

from hashlib import sha256
from urllib.parse import urlparse

from app.knowledge.ingestion.models import AcquisitionResult, AcquisitionStatus
from app.knowledge.repositories.models import StoredRepresentation


class MinioScientificObjectStore:
    def __init__(
        self, *, endpoint: str, access_key: str, secret_key: str,
        bucket: str = "researchos-documents", secure: bool = False,
    ) -> None:
        if not endpoint or not access_key or not secret_key or not bucket:
            raise ValueError("Complete MinIO configuration is required")
        import boto3
        self.bucket = bucket
        self.client = boto3.client(
            "s3", endpoint_url=endpoint,
            aws_access_key_id=access_key, aws_secret_access_key=secret_key,
            use_ssl=secure,
        )

    def put(self, result: AcquisitionResult) -> str:
        if result.status is not AcquisitionStatus.ACQUIRED:
            raise ValueError("Only acquired content can be stored")
        if result.content is None or not result.content_hash or not result.media_type:
            raise ValueError("Acquired content or integrity metadata is missing")
        extension = {"application/pdf": "pdf"}.get(result.media_type, "bin")
        return self.put_bytes(
            result.content, media_type=result.media_type,
            checksum_sha256=result.content_hash, extension=extension,
            namespace="representations",
        )

    def verify_capture(self, result: AcquisitionResult, storage_uri: str) -> None:
        representation = StoredRepresentation(
            representation_id="capture-verification",
            object_id=result.record_id,
            representation_type="pdf",
            storage_uri=storage_uri,
            media_type=result.media_type or "",
            checksum_sha256=result.content_hash or "",
            file_size=result.byte_size or 0,
            document_version=1,
        )
        if self.read_verified(representation) != result.content:
            raise ValueError("Stored raw capture differs from acquired payload")

    def put_bytes(
        self, content: bytes, *, media_type: str, checksum_sha256: str,
        extension: str, namespace: str,
    ) -> str:
        if not content or sha256(content).hexdigest() != checksum_sha256:
            raise ValueError("Object payload checksum does not match supplied checksum")
        if not extension.isalnum() or not namespace.replace("-", "").isalnum():
            raise ValueError("Object namespace or extension is invalid")
        key = f"{namespace}/{checksum_sha256[:2]}/{checksum_sha256}.{extension}"
        try:
            existing = self.client.head_object(Bucket=self.bucket, Key=key)
            metadata_hash = existing.get("Metadata", {}).get("sha256")
            if existing.get("ContentLength") != len(content) or metadata_hash != checksum_sha256:
                raise RuntimeError("Object storage integrity conflict")
        except self.client.exceptions.ClientError as exc:
            if exc.response.get("Error", {}).get("Code") not in {"404", "NoSuchKey", "NotFound"}:
                raise
            self.client.put_object(
                Bucket=self.bucket, Key=key, Body=content,
                ContentType=media_type,
                Metadata={"sha256": checksum_sha256},
            )
        return f"s3://{self.bucket}/{key}"

    def read_verified(self, representation: StoredRepresentation) -> bytes:
        parsed = urlparse(representation.storage_uri)
        bucket = parsed.netloc
        key = parsed.path.lstrip("/")
        if parsed.scheme != "s3" or bucket != self.bucket or not key:
            raise ValueError("Representation storage URI is outside the configured bucket")
        try:
            response = self.client.get_object(Bucket=bucket, Key=key)
        except self.client.exceptions.ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code in {"404", "NoSuchKey", "NotFound"}:
                raise KeyError(f"Representation object is missing: {representation.storage_uri}") from exc
            raise
        declared_size = response.get("ContentLength")
        metadata_hash = response.get("Metadata", {}).get("sha256")
        media_type = response.get("ContentType")
        if declared_size != representation.file_size:
            raise ValueError("Representation object size does not match canonical metadata")
        if metadata_hash != representation.checksum_sha256:
            raise ValueError("Representation object metadata checksum does not match")
        if media_type != representation.media_type:
            raise ValueError("Representation object media type does not match")
        content = response["Body"].read(representation.file_size + 1)
        if len(content) != representation.file_size:
            raise ValueError("Representation object payload size does not match")
        if sha256(content).hexdigest() != representation.checksum_sha256:
            raise ValueError("Representation object payload checksum does not match")
        return content
