"""Repeatable DATA-002E canonical evidence acceptance check."""

from __future__ import annotations

from dataclasses import replace
import os

from app.knowledge.extraction.models import (
    DocumentCoordinates,
    ExtractedScientificObject,
    ExtractionManifest,
    ExtractionReviewState,
    ScientificObjectType,
)
from app.knowledge.repositories.postgres import PostgresScientificDataRepository
from canonical_repository import discovery_run
from representation_repository import SECOND_CONTENT, result


def manifest(content_hash: str) -> ExtractionManifest:
    objects = (
        ExtractedScientificObject(
            "healthcheck-method", ScientificObjectType.METHOD,
            "We used a deterministic repository acceptance test.",
            DocumentCoordinates(1, 10, 61, "a" * 64), 0.95,
            ExtractionReviewState.PROVISIONAL, "healthcheck-parser", "1.0.0",
        ),
        ExtractedScientificObject(
            "healthcheck-limitation", ScientificObjectType.LIMITATION,
            "This object exists only for local acceptance testing.",
            DocumentCoordinates(1, 70, 123, "b" * 64), 0.90,
            ExtractionReviewState.PROVISIONAL, "healthcheck-parser", "1.0.0",
        ),
        ExtractedScientificObject(
            "healthcheck-pending", ScientificObjectType.RESULT,
            "This object remains pending for admission rejection testing.",
            DocumentCoordinates(1, 130, 191, "c" * 64), 0.85,
            ExtractionReviewState.PROVISIONAL, "healthcheck-parser", "1.0.0",
        ),
    )
    return ExtractionManifest(
        "evidence-healthcheck", "source-document-healthcheck", content_hash,
        "2026-07-15T14:00:00Z", "healthcheck-parser", "1.0.0", objects,
    )


def main() -> None:
    repository = PostgresScientificDataRepository(os.environ["DATABASE_URL"])
    record = discovery_run().records[0]
    source_representation = result(
        SECOND_CONTENT, "2026-07-15T13:05:00Z"
    )
    extraction = manifest(source_representation.content_hash)
    first = repository.persist_evidence(record, extraction)
    assert repository.persist_evidence(record, extraction) == first
    assert len(first) == 3

    conflicting_object = replace(
        extraction.objects[0],
        coordinates=replace(extraction.objects[0].coordinates, quote_hash="c" * 64),
    )
    try:
        repository.persist_evidence(
            record, replace(
                extraction,
                objects=(
                    conflicting_object, extraction.objects[1],
                    extraction.objects[2],
                ),
            ),
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("Evidence integrity conflict was not rejected")

    with repository._connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT e.evidence_type, e.page, e.character_start, e.character_end,
                       e.human_review_status, e.extraction_method,
                       r.checksum_sha256
                FROM evidence_objects e
                JOIN canonical_objects c ON c.object_id=e.evidence_id
                JOIN scientific_representations r ON r.representation_id=e.representation_id
                WHERE c.stable_key IN (
                    'evidence:healthcheck-method', 'evidence:healthcheck-limitation',
                    'evidence:healthcheck-pending'
                )
                ORDER BY e.evidence_type
            """)
            rows = cursor.fetchall()
    assert len(rows) == 3, rows
    assert {row[0] for row in rows} == {"method", "limitation", "result"}
    assert all(row[4] in {"pending", "accepted", "rejected"} for row in rows)
    assert all(row[5] == "healthcheck-parser@1.0.0" for row in rows)
    assert all(row[6] == source_representation.content_hash for row in rows)

    accepted = repository.review_evidence(
        "healthcheck-method", decision="accepted", reviewer="reviewer@researchos.local",
        rationale="Verified quotation and coordinates.",
        occurred_at="2026-07-15T14:30:00Z",
    )
    repeated = repository.review_evidence(
        "healthcheck-method", decision="accepted", reviewer="reviewer@researchos.local",
        rationale="Verified quotation and coordinates.",
        occurred_at="2026-07-15T14:30:00Z",
    )
    assert repeated.review_id == accepted.review_id
    rejected = repository.review_evidence(
        "healthcheck-method", decision="rejected", reviewer="reviewer@researchos.local",
        rationale="Superseding review: the statement is methodological context only.",
        occurred_at="2026-07-15T14:35:00Z",
    )
    assert rejected.previous_state == "accepted"
    with repository._connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT e.human_review_status, count(v.review_id),
                       count(DISTINCT v.provenance_id)
                FROM canonical_objects c
                JOIN evidence_objects e ON e.evidence_id=c.object_id
                JOIN evidence_review_events v ON v.evidence_id=e.evidence_id
                WHERE c.stable_key='evidence:healthcheck-method'
                GROUP BY e.human_review_status
            """)
            review_state = cursor.fetchone()
    assert review_state[0] == "rejected", review_state
    assert review_state[1] == review_state[2] and review_state[1] >= 2, review_state
    try:
        with repository._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE evidence_review_events SET rationale='mutated' WHERE review_id=%s",
                    (accepted.review_id,),
                )
    except Exception as exc:
        assert "append-only" in str(exc)
    else:
        raise AssertionError("Evidence review mutation was not rejected")
    print("canonical evidence healthcheck: passed")


if __name__ == "__main__":
    main()
