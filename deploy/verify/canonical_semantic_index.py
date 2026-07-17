"""DATA-002J canonical semantic indexing acceptance check."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from time import sleep

from app.knowledge.repositories.postgres import PostgresScientificDataRepository
from app.knowledge.extraction.models import (
    EpistemicClassification, EvidenceReviewAssessment,
)
from app.workers.main import execute


def iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def wait_for_jobs(repository, job_ids, timeout=30):
    for _ in range(timeout * 2):
        with repository._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT job_id,status,error FROM background_jobs WHERE job_id=ANY(%s)",
                    (job_ids,),
                )
                rows = cursor.fetchall()
        if len(rows) == len(job_ids) and all(row[1] in {"complete", "failed"} for row in rows):
            return rows
        sleep(0.5)
    raise TimeoutError("Semantic index jobs did not finish")


def main() -> None:
    repository = PostgresScientificDataRepository(os.environ["DATABASE_URL"])
    now = datetime.now(timezone.utc)
    suffix = now.strftime("%Y%m%dT%H%M%S%f")
    model = f"health-model-{suffix}"
    with repository._connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT c.stable_key,e.content_hash,x.manifest_hash
                FROM canonical_objects c
                JOIN evidence_objects e ON e.evidence_id=c.object_id
                JOIN extraction_manifests x
                  ON x.extraction_manifest_id=e.extraction_manifest_id
                WHERE c.stable_key IN (
                    'evidence:healthcheck-v11-method',
                    'evidence:healthcheck-v11-limitation'
                )
            """)
            review_bindings = {
                row[0]: (row[1], row[2]) for row in cursor.fetchall()
            }
    statement_hash, manifest_hash = review_bindings[
        "evidence:healthcheck-v11-method"
    ]
    review_assessment = EvidenceReviewAssessment(
        True, True, True, .95, EpistemicClassification.OBSERVED_FACT,
        statement_hash, manifest_hash,
    )
    limitation_hash, limitation_manifest_hash = review_bindings[
        "evidence:healthcheck-v11-limitation"
    ]
    limitation_assessment = EvidenceReviewAssessment(
        True, True, False, .4, EpistemicClassification.OBSERVED_FACT,
        limitation_hash, limitation_manifest_hash,
    )
    repository.review_evidence(
        "healthcheck-v11-method", decision="accepted", reviewer="index-reviewer@researchos.local",
        rationale=f"Accepted for semantic indexing {suffix}.", occurred_at=iso(now),
        assessment=review_assessment,
    )
    repository.review_evidence(
        "healthcheck-v11-limitation", decision="rejected", reviewer="index-reviewer@researchos.local",
        rationale=f"Rejected for semantic indexing {suffix}.",
        occurred_at=iso(now + timedelta(seconds=1)),
        assessment=limitation_assessment,
    )
    artifact_id = f"semantic-artifact-{suffix}"
    repository.persist_artifact(
        artifact_id=artifact_id, project_id=f"semantic-project-{suffix}",
        artifact_type="validation_report", title="Semantic indexing healthcheck",
        status="validated", metadata={"statement": "Validated semantic artifact", "suffix": suffix},
        actor_id="index-reviewer@researchos.local", occurred_at=iso(now),
    )
    evidence_vector = tuple(0.01 if index == 0 else 0.0 for index in range(1536))
    artifact_vector = tuple(0.01 if index == 1 else 0.0 for index in range(1536))
    evidence_job = repository.enqueue_semantic_index(
        object_type="evidence", object_id="healthcheck-v11-method", model=model,
        embedding=evidence_vector, metadata={"source": "acceptance"},
    )
    repeated = repository.enqueue_semantic_index(
        object_type="evidence", object_id="healthcheck-v11-method", model=model,
        embedding=evidence_vector, metadata={"source": "acceptance"},
    )
    assert repeated.job_id == evidence_job.job_id
    artifact_job = repository.enqueue_semantic_index(
        object_type="artifact", object_id=artifact_id, model=model,
        embedding=artifact_vector, metadata={"source": "acceptance"},
    )
    try:
        repository.enqueue_semantic_index(
            object_type="evidence", object_id="healthcheck-v11-limitation", model=model,
            embedding=evidence_vector, metadata={},
        )
    except ValueError as exc:
        assert "not accepted" in str(exc)
    else:
        raise AssertionError("Rejected evidence was enqueued")

    stale_payload = {
        "object_type": "evidence", "object_id": "healthcheck-v11-method", "model": model,
        "embedding": evidence_vector, "metadata": {},
        "canonical_object_id": evidence_job.canonical_object_id,
        "content_hash": "0" * 64,
    }
    stale_key = sha256(f"stale:{suffix}".encode()).hexdigest()
    with repository._connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO background_jobs(job_type,payload,deduplication_key)
                VALUES ('index_embedding',%s,%s) RETURNING job_id
            """, (json.dumps(stale_payload), stale_key))
            stale_job_id = str(cursor.fetchone()[0])

    job_ids = [evidence_job.job_id, artifact_job.job_id, stale_job_id]
    states = wait_for_jobs(repository, job_ids)
    state_by_id = {str(row[0]): (row[1], row[2]) for row in states}
    assert state_by_id[evidence_job.job_id][0] == "complete"
    assert state_by_id[artifact_job.job_id][0] == "complete"
    assert state_by_id[stale_job_id][0] == "failed"
    assert "content hash changed" in state_by_id[stale_job_id][1]

    canonical_ids = [evidence_job.canonical_object_id, artifact_job.canonical_object_id]
    with repository._connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT canonical_object_id::text,content_hash,model,dimensions,payload
                FROM embedding_index e
                JOIN background_jobs j
                  ON j.payload->>'canonical_object_id'=e.canonical_object_id::text
                 AND j.payload->>'content_hash'=e.content_hash
                 AND j.payload->>'model'=e.model
                WHERE e.model=%s AND e.canonical_object_id=ANY(%s::uuid[])
                ORDER BY canonical_object_id
            """, (model, canonical_ids))
            indexed = cursor.fetchall()
    assert len(indexed) == 2 and all(row[3] == 1536 for row in indexed), indexed
    payloads = [row[4] for row in indexed]
    with repository._connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM embedding_index WHERE model=%s AND canonical_object_id=ANY(%s::uuid[])",
                (model, canonical_ids),
            )
        connection.commit()
        for payload in payloads:
            execute(connection, "index_embedding", payload)
        connection.commit()
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM embedding_index WHERE model=%s AND canonical_object_id=ANY(%s::uuid[])",
                (model, canonical_ids),
            )
            assert cursor.fetchone()[0] == 2

    evidence_hits = repository.semantic_search(
        model=model, query_embedding=evidence_vector, limit=5,
        object_types=("evidence",),
    )
    assert len(evidence_hits) == 1
    assert evidence_hits[0].object_id == "healthcheck-v11-method"
    assert evidence_hits[0].similarity > 0.999
    assert evidence_hits[0].provenance_id and evidence_hits[0].attributed_actor
    artifact_hits = repository.semantic_search(
        model=model, query_embedding=artifact_vector, limit=5,
        object_types=("artifact",),
    )
    assert len(artifact_hits) == 1 and artifact_hits[0].object_id == artifact_id

    repository.review_evidence(
        "healthcheck-v11-method", decision="rejected", reviewer="index-reviewer@researchos.local",
        rationale=f"Revoked after semantic retrieval {suffix}.",
        occurred_at=iso(now + timedelta(seconds=2)),
        assessment=review_assessment,
    )
    assert repository.semantic_search(
        model=model, query_embedding=evidence_vector, limit=5,
        object_types=("evidence",),
    ) == ()
    for offset, status in enumerate(("ratified", "published", "deprecated"), start=3):
        repository.transition_artifact(
            artifact_id, to_status=status, actor_id="index-reviewer@researchos.local",
            rationale=f"Semantic lifecycle check: {status}.",
            occurred_at=iso(now + timedelta(seconds=offset)),
        )
    assert repository.semantic_search(
        model=model, query_embedding=artifact_vector, limit=5,
        object_types=("artifact",),
    ) == ()
    print("canonical semantic index healthcheck: passed")


if __name__ == "__main__":
    main()
