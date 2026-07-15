"""PostgreSQL-backed worker for parsing, normalization, and vector indexing."""

import json
import os
from pathlib import Path
from time import sleep

import psycopg


DATABASE_URL = os.environ["DATABASE_URL"]
KNOWLEDGE_ROOT = Path(os.getenv("KNOWLEDGE_OUTPUT_ROOT", "/data/knowledge"))
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))


def validate_semantic_source(cursor, payload):
    canonical_object_id = payload["canonical_object_id"]
    content_hash = payload["content_hash"]
    object_type = payload["object_type"]
    object_id = payload["object_id"]
    if object_type == "evidence":
        cursor.execute("""
            SELECT e.content_hash,e.human_review_status,c.stable_key
            FROM canonical_objects c JOIN evidence_objects e ON e.evidence_id=c.object_id
            WHERE c.object_id=%s
        """, (canonical_object_id,))
        row = cursor.fetchone()
        if row is None or row[2] != f"evidence:{object_id}":
            raise ValueError("Canonical evidence identity does not match embedding job")
        if row[1] != "accepted" or row[0] != content_hash:
            raise ValueError("Embedding source evidence is not accepted or content hash changed")
    elif object_type == "artifact":
        cursor.execute("""
            SELECT r.content_hash,r.status,c.stable_key
            FROM canonical_objects c JOIN research_artifacts r ON r.artifact_id=c.object_id
            WHERE c.object_id=%s
        """, (canonical_object_id,))
        row = cursor.fetchone()
        if row is None or row[2] != f"artifact:{object_id}":
            raise ValueError("Canonical artifact identity does not match embedding job")
        expected_hash = row[0]
        if row[1] not in {"validated", "ratified", "published"} or expected_hash != content_hash:
            raise ValueError("Embedding source artifact is ineligible or content hash changed")
    else:
        raise ValueError(f"Unsupported semantic object type: {object_type}")


def claim(connection):
    with connection.transaction(), connection.cursor() as cursor:
        cursor.execute("""
            SELECT job_id, job_type, payload FROM background_jobs
            WHERE status = 'pending' ORDER BY created_at
            FOR UPDATE SKIP LOCKED LIMIT 1
        """)
        row = cursor.fetchone()
        if row:
            cursor.execute("""
                UPDATE background_jobs SET status='running', attempts=attempts+1,
                started_at=now() WHERE job_id=%s
            """, (row[0],))
        return row


def execute(connection, job_type, payload):
    if job_type == "normalize_metadata":
        record_id = payload["record_id"]
        metadata = {str(key).strip().lower(): value for key, value in payload["metadata"].items()}
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO normalized_metadata(record_id, metadata, source_hash)
                VALUES (%s, %s, %s) ON CONFLICT(record_id) DO UPDATE SET
                metadata=excluded.metadata, source_hash=excluded.source_hash, updated_at=now()
            """, (record_id, json.dumps(metadata), payload["source_hash"]))
    elif job_type == "index_embedding":
        canonical_object_id = payload.get("canonical_object_id")
        content_hash = payload.get("content_hash")
        if not canonical_object_id or not content_hash:
            raise ValueError(
                "index_embedding requires canonical_object_id and content_hash"
            )
        if len(payload["embedding"]) != EMBEDDING_DIMENSIONS:
            raise ValueError(
                f"Embedding must contain {EMBEDDING_DIMENSIONS} dimensions"
            )
        vector = "[" + ",".join(str(float(value)) for value in payload["embedding"]) + "]"
        with connection.cursor() as cursor:
            validate_semantic_source(cursor, payload)
            cursor.execute("""
                INSERT INTO embedding_index(object_type, object_id, model, dimensions, embedding, metadata, canonical_object_id, content_hash)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(canonical_object_id,content_hash,model) DO NOTHING
            """, (
                payload["object_type"], payload["object_id"], payload["model"],
                len(payload["embedding"]), vector,
                json.dumps(payload.get("metadata", {})), canonical_object_id,
                content_hash,
            ))
    elif job_type == "parse_document":
        from app.knowledge.extraction.engine import EvidenceExtractionEngine
        from app.knowledge.extraction.persistence import ExtractionManifestStore
        from app.knowledge.ingestion.registry import DocumentRegistry
        document_id = payload.get("document_id")
        if not document_id:
            raise ValueError("parse_document requires document_id")
        registry = DocumentRegistry(KNOWLEDGE_ROOT / "documents")
        document = registry.get(document_id)
        content = registry.read_verified_content(document)
        manifest = EvidenceExtractionEngine().extract(
            document, content, created_at=payload.get("created_at", "worker"),
        )
        ExtractionManifestStore(KNOWLEDGE_ROOT / "extractions").save(manifest)
    else:
        raise ValueError(f"Unsupported job type: {job_type}")


def main():
    while True:
        try:
            with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
                while True:
                    job = claim(connection)
                    if not job:
                        sleep(2)
                        continue
                    job_id, job_type, payload = job
                    try:
                        execute(connection, job_type, payload)
                        with connection.cursor() as cursor:
                            cursor.execute("UPDATE background_jobs SET status='complete', completed_at=now(), error=NULL WHERE job_id=%s", (job_id,))
                    except Exception as exc:
                        with connection.cursor() as cursor:
                            cursor.execute("UPDATE background_jobs SET status='failed', completed_at=now(), error=%s WHERE job_id=%s", (str(exc), job_id))
        except psycopg.Error:
            sleep(5)


if __name__ == "__main__":
    main()
