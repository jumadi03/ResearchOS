"""PostgreSQL-backed worker for parsing, normalization, and vector indexing."""

import json
import multiprocessing
import os
from pathlib import Path
from queue import Empty
import signal
import socket
from threading import Thread
from time import sleep
from uuid import uuid4

DATABASE_URL = os.getenv("DATABASE_URL")
KNOWLEDGE_ROOT = Path(os.getenv("KNOWLEDGE_OUTPUT_ROOT", "/data/knowledge"))
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))
JOB_MAX_ATTEMPTS = int(os.getenv("JOB_MAX_ATTEMPTS", "3"))
JOB_LEASE_SECONDS = int(os.getenv("JOB_LEASE_SECONDS", "660"))
JOB_RETRY_BASE_SECONDS = int(os.getenv("JOB_RETRY_BASE_SECONDS", "5"))
JOB_TIMEOUT_SECONDS = int(os.getenv("JOB_TIMEOUT_SECONDS", "600"))
WORKER_ID = os.getenv("WORKER_ID", f"{socket.gethostname()}:{uuid4()}")
_stop_requested = False


def record_heartbeat(connection) -> None:
    with connection.transaction(), connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO worker_heartbeats(worker_id, last_seen_at)
            VALUES (%s, now())
            ON CONFLICT(worker_id) DO UPDATE SET last_seen_at=excluded.last_seen_at
            """,
            (WORKER_ID,),
        )
        cursor.execute(
            "DELETE FROM worker_heartbeats WHERE last_seen_at < now() - interval '7 days'"
        )


def heartbeat_loop(database_url: str) -> None:
    """Publish liveness independently while the worker executes long-running jobs."""
    import psycopg

    while not _stop_requested:
        try:
            with psycopg.connect(database_url, autocommit=True) as connection:
                record_heartbeat(connection)
        except psycopg.Error:
            pass
        for _ in range(5):
            if _stop_requested:
                return
            sleep(1)


def request_stop(_signum=None, _frame=None):
    global _stop_requested
    _stop_requested = True


def retry_delay(attempts: int) -> int:
    """Return bounded exponential backoff for the next retry."""
    return min(JOB_RETRY_BASE_SECONDS * (2 ** max(attempts - 1, 0)), 3600)


def failure_disposition(attempts: int) -> tuple[str, int | None]:
    if attempts >= JOB_MAX_ATTEMPTS:
        return "dead_letter", None
    return "pending", retry_delay(attempts)


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
            UPDATE background_jobs SET status='pending', locked_by=NULL,
                lease_expires_at=NULL, available_at=now(),
                error=COALESCE(error, 'worker lease expired')
            WHERE status='running' AND lease_expires_at < now()
        """)
        cursor.execute("""
            SELECT job_id, job_type, payload FROM background_jobs
            WHERE status='pending' AND available_at <= now()
            ORDER BY available_at, created_at
            FOR UPDATE SKIP LOCKED LIMIT 1
        """)
        row = cursor.fetchone()
        if row:
            cursor.execute("""
                UPDATE background_jobs SET status='running', attempts=attempts+1,
                started_at=now(), completed_at=NULL, locked_by=%s,
                lease_expires_at=now() + (%s * interval '1 second')
                WHERE job_id=%s
            """, (WORKER_ID, JOB_LEASE_SECONDS, row[0]))
        return row


def mark_complete(connection, job_id):
    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE background_jobs SET status='complete', completed_at=now(),
                error=NULL, locked_by=NULL, lease_expires_at=NULL
            WHERE job_id=%s AND status='running' AND locked_by=%s
        """, (job_id, WORKER_ID))


def mark_failed(connection, job_id, error: Exception):
    with connection.transaction(), connection.cursor() as cursor:
        cursor.execute(
            "SELECT attempts FROM background_jobs WHERE job_id=%s FOR UPDATE",
            (job_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return
        attempts = row[0]
        status, delay = failure_disposition(attempts)
        terminal = status == "dead_letter"
        cursor.execute("""
            UPDATE background_jobs SET status=%s,
                completed_at=CASE WHEN %s THEN now() ELSE NULL END,
                available_at=CASE WHEN %s THEN available_at
                    ELSE now() + (%s * interval '1 second') END,
                error=%s, locked_by=NULL, lease_expires_at=NULL
            WHERE job_id=%s AND locked_by=%s
        """, (
            status, terminal, terminal, delay or 0, str(error)[:4000],
            job_id, WORKER_ID,
        ))


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


def _execute_isolated(database_url: str, job_type: str, payload: dict, result_queue):
    """Run one job with a connection owned exclusively by the child process."""
    try:
        import psycopg

        with psycopg.connect(database_url, autocommit=True) as connection:
            execute(connection, job_type, payload)
        result_queue.put(("complete", None))
    except BaseException as exc:
        result_queue.put(("failed", f"{type(exc).__name__}: {exc}"))


def execute_with_timeout(database_url: str, job_type: str, payload: dict) -> None:
    context = multiprocessing.get_context("spawn")
    result_queue = context.Queue(maxsize=1)
    process = context.Process(
        target=_execute_isolated,
        args=(database_url, job_type, payload, result_queue),
        name=f"researchos-job-{job_type}",
    )
    process.start()
    process.join(JOB_TIMEOUT_SECONDS)
    if process.is_alive():
        process.terminate()
        process.join(10)
        if process.is_alive():
            process.kill()
            process.join()
        raise TimeoutError(
            f"Job {job_type} exceeded {JOB_TIMEOUT_SECONDS} seconds"
        )
    try:
        status, error = result_queue.get(timeout=1)
    except Empty:
        raise RuntimeError(
            f"Job process exited without a result (exit code {process.exitcode})"
        )
    if status != "complete":
        raise RuntimeError(error or f"Job {job_type} failed")


def main():
    import psycopg

    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is required for the background worker")
    if JOB_LEASE_SECONDS <= JOB_TIMEOUT_SECONDS:
        raise RuntimeError("JOB_LEASE_SECONDS must be greater than JOB_TIMEOUT_SECONDS")
    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    Thread(
        target=heartbeat_loop,
        args=(DATABASE_URL,),
        name="researchos-worker-heartbeat",
        daemon=True,
    ).start()
    while not _stop_requested:
        try:
            with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
                while not _stop_requested:
                    job = claim(connection)
                    if not job:
                        sleep(2)
                        continue
                    job_id, job_type, payload = job
                    try:
                        execute_with_timeout(DATABASE_URL, job_type, payload)
                        mark_complete(connection, job_id)
                    except Exception as exc:
                        mark_failed(connection, job_id, exc)
        except psycopg.Error:
            if not _stop_requested:
                sleep(5)


if __name__ == "__main__":
    main()
