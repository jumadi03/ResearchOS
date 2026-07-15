"""PostgreSQL semantic indexing and retrieval operations."""

from hashlib import sha256
import json

from app.knowledge.discovery.normalization import canonical_json
from app.knowledge.repositories.semantic import SemanticIndexJob, SemanticSearchHit


class PostgresSemanticRepositoryMixin:
    """Semantic-index behavior shared by the PostgreSQL repository façade."""

    def enqueue_semantic_index(
        self, *, object_type: str, object_id: str, model: str,
        embedding: tuple[float, ...], metadata: dict,
    ) -> SemanticIndexJob:
        if object_type not in {"evidence", "artifact"}:
            raise ValueError("Semantic object type must be evidence or artifact")
        if len(embedding) != 1536:
            raise ValueError("Embedding must contain 1536 dimensions")
        if not object_id.strip() or not model.strip():
            raise ValueError("Semantic object identity and model are required")
        with self._connect() as connection:
            with connection.cursor() as cursor:
                if object_type == "evidence":
                    cursor.execute("""
                        SELECT c.object_id,e.content_hash,e.human_review_status
                        FROM canonical_objects c
                        JOIN evidence_objects e ON e.evidence_id=c.object_id
                        WHERE c.stable_key=%s
                    """, (f"evidence:{object_id}",))
                    source = cursor.fetchone()
                    if source is None:
                        raise KeyError(f"Unknown canonical evidence: {object_id}")
                    canonical_id, content_hash, status = source
                    if status != "accepted":
                        raise ValueError(f"Evidence is not accepted: {object_id}")
                else:
                    cursor.execute("""
                        SELECT c.object_id,r.content_hash,r.status
                        FROM canonical_objects c
                        JOIN research_artifacts r ON r.artifact_id=c.object_id
                        WHERE c.stable_key=%s
                    """, (f"artifact:{object_id}",))
                    source = cursor.fetchone()
                    if source is None:
                        raise KeyError(f"Unknown canonical artifact: {object_id}")
                    canonical_id, content_hash, status = source
                    if status not in {"validated", "ratified", "published"}:
                        raise ValueError(f"Artifact is not eligible for indexing: {object_id}")
                deduplication_key = sha256(canonical_json({
                    "canonical_object_id": str(canonical_id),
                    "content_hash": content_hash, "model": model.strip(),
                }).encode()).hexdigest()
                payload = {
                    "object_type": object_type, "object_id": object_id,
                    "model": model.strip(), "embedding": embedding,
                    "metadata": metadata, "canonical_object_id": str(canonical_id),
                    "content_hash": content_hash,
                }
                cursor.execute("""
                    INSERT INTO background_jobs(job_type,payload,deduplication_key)
                    VALUES ('index_embedding',%s,%s)
                    ON CONFLICT(deduplication_key)
                    WHERE deduplication_key IS NOT NULL DO NOTHING
                    RETURNING job_id,status
                """, (json.dumps(payload), deduplication_key))
                job = cursor.fetchone()
                if job is None:
                    cursor.execute("""
                        SELECT job_id,status FROM background_jobs
                        WHERE deduplication_key=%s
                    """, (deduplication_key,))
                    job = cursor.fetchone()
        return SemanticIndexJob(
            str(job[0]), object_type, object_id, str(canonical_id), content_hash,
            model.strip(), len(embedding), job[1],
        )

    def semantic_search(
        self, *, model: str, query_embedding: tuple[float, ...], limit: int,
        object_types: tuple[str, ...],
    ) -> tuple[SemanticSearchHit, ...]:
        if len(query_embedding) != 1536:
            raise ValueError("Query embedding must contain 1536 dimensions")
        normalized_types = tuple(dict.fromkeys(object_types))
        if not normalized_types or any(item not in {"evidence", "artifact"} for item in normalized_types):
            raise ValueError("Semantic search object types must be evidence or artifact")
        if not 1 <= limit <= 100 or not model.strip():
            raise ValueError("Semantic search requires a model and limit from 1 to 100")
        vector = "[" + ",".join(str(float(value)) for value in query_embedding) + "]"
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT i.canonical_object_id,c.stable_key,i.object_type,i.object_id,
                           i.content_hash,i.model,
                           1-(i.embedding <=> %s::vector) AS similarity,
                           i.metadata,
                           COALESCE(er.provenance_id,al.provenance_id,a.provenance_id),
                           COALESCE(er.reviewer_id,al.actor_id)
                    FROM embedding_index i
                    JOIN canonical_objects c ON c.object_id=i.canonical_object_id
                    LEFT JOIN evidence_objects e ON e.evidence_id=i.canonical_object_id
                    LEFT JOIN research_artifacts a ON a.artifact_id=i.canonical_object_id
                    LEFT JOIN LATERAL (
                        SELECT provenance_id,reviewer_id
                        FROM evidence_review_events
                        WHERE evidence_id=e.evidence_id AND decision='accepted'
                        ORDER BY occurred_at DESC,created_at DESC LIMIT 1
                    ) er ON i.object_type='evidence'
                    LEFT JOIN LATERAL (
                        SELECT provenance_id,actor_id
                        FROM artifact_lifecycle_events
                        WHERE artifact_id=a.artifact_id
                        ORDER BY occurred_at DESC LIMIT 1
                    ) al ON i.object_type='artifact'
                    WHERE i.model=%s AND i.object_type=ANY(%s)
                      AND (
                        (i.object_type='evidence' AND e.human_review_status='accepted'
                         AND e.content_hash=i.content_hash)
                        OR
                        (i.object_type='artifact'
                         AND a.status IN ('validated','ratified','published')
                         AND a.content_hash=i.content_hash)
                      )
                    ORDER BY i.embedding <=> %s::vector, i.embedding_id
                    LIMIT %s
                """, (vector, model.strip(), list(normalized_types), vector, limit))
                rows = cursor.fetchall()
        return tuple(SemanticSearchHit(
            canonical_object_id=str(row[0]), stable_key=row[1],
            object_type=row[2], object_id=row[3], content_hash=row[4],
            model=row[5], similarity=float(row[6]), metadata=row[7],
            provenance_id=str(row[8]) if row[8] else None,
            attributed_actor=row[9],
        ) for row in rows)
