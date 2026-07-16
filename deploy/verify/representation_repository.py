"""Repeatable DATA-002C PostgreSQL + MinIO acceptance check."""

from __future__ import annotations

from hashlib import sha256
import os
from dataclasses import replace

from app.knowledge.ingestion.models import AcquisitionResult, AcquisitionStatus
from app.knowledge.repositories.minio import MinioScientificObjectStore
from app.knowledge.repositories.postgres import PostgresScientificDataRepository
from canonical_repository import discovery_run


def result(content: bytes, acquired_at: str) -> AcquisitionResult:
    return AcquisitionResult(
        record_id="repository-healthcheck",
        status=AcquisitionStatus.ACQUIRED,
        acquired_at=acquired_at,
        source_url="https://example.test/researchos-healthcheck.pdf",
        source_provider="openalex",
        source_response_hash="repository-healthcheck-source-v1",
        license="CC-BY-4.0",
        media_type="application/pdf",
        content_hash=sha256(content).hexdigest(),
        byte_size=len(content),
        reason=None,
        content=content,
        final_url="https://example.test/researchos-healthcheck.pdf",
        http_status=200,
        redirect_chain=(),
        declared_content_length=len(content),
        retrieval_method="https_pdf",
        source_definition_id="source-openalex",
        query_family_id="repository-healthcheck-query-family",
        response_headers=(
            ("content-type", "application/pdf"),
            ("etag", '"researchos-scan-001f"'),
        ),
        content_encoding="binary",
    )


def main() -> None:
    repository = PostgresScientificDataRepository(os.environ["DATABASE_URL"])
    record = discovery_run().records[0]
    store = MinioScientificObjectStore(
        endpoint=os.environ["MINIO_ENDPOINT"],
        access_key=os.environ["MINIO_ACCESS_KEY"],
        secret_key=os.environ["MINIO_SECRET_KEY"],
        bucket=os.getenv("MINIO_DOCUMENT_BUCKET", "researchos-documents"),
    )
    source = record.source_records[0]
    first = replace(
        result(
            b"%PDF-1.7\nResearchOS SCAN-001F header capture v1\n",
            "2026-07-15T13:00:00Z",
        ),
        source_definition_id=source.source_definition_id,
        query_family_id=source.query_family_id,
        capture_manifest_hash=None,
    )
    second = replace(
        result(
            b"%PDF-1.7\nResearchOS SCAN-001F header capture v2\n",
            "2026-07-15T13:05:00Z",
        ),
        source_definition_id=source.source_definition_id,
        query_family_id=source.query_family_id,
        capture_manifest_hash=None,
    )
    first_uri = store.put(first)
    first_id = repository.persist_representation(record, first, first_uri)
    assert repository.persist_representation(record, first, store.put(first)) == first_id
    second_uri = store.put(second)
    second_id = repository.persist_representation(record, second, second_uri)

    assert second_id[1] == first_id[1] + 1, (first_id, second_id)
    with repository._connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT document_version, checksum_sha256, storage_uri,
                       final_url,http_status,redirect_chain,response_headers,
                       content_encoding,license,source_definition_id,
                       query_family_id,capture_manifest_hash,retrieval_method
                FROM scientific_representations r
                JOIN canonical_objects c ON c.object_id=r.object_id
                WHERE c.stable_key='doi:10.0000/researchos.repository-healthcheck'
                  AND representation_type='pdf'
                  AND checksum_sha256 IN (%s,%s)
                ORDER BY document_version
            """, (first.content_hash, second.content_hash))
            rows = cursor.fetchall()
    assert rows == [
        (
            first_id[1], first.content_hash, first_uri, first.final_url, 200, [],
            dict(first.response_headers), "binary", first.license,
            first.source_definition_id,
            first.query_family_id, first.capture_manifest_hash,
            first.retrieval_method,
        ),
        (
            second_id[1], second.content_hash, second_uri, second.final_url, 200, [],
            dict(second.response_headers), "binary", second.license,
            second.source_definition_id,
            second.query_family_id, second.capture_manifest_hash,
            second.retrieval_method,
        ),
    ], rows
    stored = repository.get_representation(record, second.content_hash)
    assert store.read_verified(stored) == second.content
    try:
        store.read_verified(replace(stored, checksum_sha256="0" * 64))
    except ValueError:
        pass
    else:
        raise AssertionError("Checksum mismatch was not rejected")
    try:
        store.read_verified(replace(stored, storage_uri="s3://researchos-documents/missing.pdf"))
    except KeyError:
        pass
    else:
        raise AssertionError("Missing object was not rejected")
    try:
        repository.persist_representation(
            record, second,
            f"s3://researchos-documents/arbitrary/{second.content_hash}.pdf",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Non-canonical storage URI was accepted")
    try:
        repository.persist_representation(
            record, replace(
                second, source_definition_id="source-invented",
                capture_manifest_hash=None,
            ), second_uri,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Invented discovery provenance was accepted")
    print("representation repository healthcheck: passed")


if __name__ == "__main__":
    main()
