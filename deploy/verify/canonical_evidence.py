"""Repeatable DATA-002E canonical evidence acceptance check."""

from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
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


def manifest(
    content_hash: str, inspection_hash: str,
    screening_id: str, screening_hash: str,
) -> ExtractionManifest:
    def extracted(identifier, kind, text, start, confidence):
        return ExtractedScientificObject(
            identifier, kind, text,
            DocumentCoordinates(
                1, start, start + len(text),
                sha256(text.encode()).hexdigest(),
                section=kind.value,
                page_text_hash="d" * 64,
            ),
            confidence, ExtractionReviewState.PROVISIONAL,
            "healthcheck-parser", "1.1.0",
            verbatim_text=text, extraction_rule="healthcheck_fixture",
        )
    objects = (
        extracted(
            "healthcheck-v11-method", ScientificObjectType.METHOD,
            "We used a deterministic repository acceptance test.",
            10, 0.95,
        ),
        extracted(
            "healthcheck-v11-limitation", ScientificObjectType.LIMITATION,
            "This object exists only for local acceptance testing.",
            70, 0.90,
        ),
        extracted(
            "healthcheck-v11-pending", ScientificObjectType.RESULT,
            "This object remains pending for admission rejection testing.",
            130, 0.85,
        ),
    )
    return ExtractionManifest(
        "evidence-healthcheck", "source-document-healthcheck", content_hash,
        "2026-07-15T14:00:00Z", "healthcheck-parser", "1.1.0", objects,
        schema_version="1.1", inspection_manifest_hash=inspection_hash,
        screening_decision_id=screening_id,
        screening_decision_hash=screening_hash,
        configuration_hash="e" * 64,
    ).finalized()


def main() -> None:
    repository = PostgresScientificDataRepository(os.environ["DATABASE_URL"])
    record = discovery_run().records[0]
    source_representation = result(
        SECOND_CONTENT, "2026-07-15T13:05:00Z"
    )
    with repository._connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT sd.decision_key,sd.decision_hash,
                       sd.inspection_manifest_hash
                FROM screening_decisions sd
                WHERE sd.decision_key='screening-repository-healthcheck'
            """)
            screening_id, screening_hash, inspection_hash = cursor.fetchone()
    extraction = manifest(
        source_representation.content_hash, inspection_hash,
        screening_id, screening_hash,
    )
    try:
        repository.persist_evidence(
            record, replace(
                extraction, schema_version="1.0",
                inspection_manifest_hash="", screening_decision_id="",
                screening_decision_hash="", configuration_hash="",
                manifest_hash="",
            ),
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Legacy manifest bypassed canonical screening authority")
    invented = replace(
        extraction, extraction_id="invented-screening-extraction",
        screening_decision_id="screening-that-does-not-exist",
        manifest_hash="",
    ).finalized()
    try:
        repository.persist_evidence(record, invented)
    except ValueError:
        pass
    else:
        raise AssertionError("Invented screening provenance was accepted")
    first = repository.persist_evidence(record, extraction)
    assert repository.persist_evidence(record, extraction) == first
    assert len(first) == 3

    conflicting_text = "A conflicting but internally valid extraction."
    conflicting_object = replace(
        extraction.objects[0], content=conflicting_text,
        verbatim_text=conflicting_text,
        coordinates=replace(
            extraction.objects[0].coordinates,
            end_char=10 + len(conflicting_text),
            quote_hash=sha256(conflicting_text.encode()).hexdigest(),
        ),
    )
    try:
        repository.persist_evidence(
            record, replace(
                extraction,
                objects=(
                    conflicting_object, extraction.objects[1],
                    extraction.objects[2],
                ),
                manifest_hash="",
            ).finalized(),
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
                    'evidence:healthcheck-v11-method',
                    'evidence:healthcheck-v11-limitation',
                    'evidence:healthcheck-v11-pending'
                )
                ORDER BY e.evidence_type
            """)
            rows = cursor.fetchall()
            cursor.execute("""
                SELECT object_count,configuration_hash,manifest_hash,
                       screening_decision_id
                FROM extraction_manifests
                WHERE extraction_key='evidence-healthcheck'
            """)
            extraction_row = cursor.fetchone()
    assert len(rows) == 3, rows
    assert {row[0] for row in rows} == {"method", "limitation", "result"}
    assert all(row[4] in {"pending", "accepted", "rejected"} for row in rows)
    assert all(row[5] == "healthcheck-parser@1.1.0" for row in rows)
    assert all(row[6] == source_representation.content_hash for row in rows)
    assert extraction_row[0] == 3
    assert extraction_row[1] == extraction.configuration_hash
    assert extraction_row[2] == extraction.manifest_hash
    assert extraction_row[3] is not None

    accepted = repository.review_evidence(
        "healthcheck-v11-method", decision="accepted", reviewer="reviewer@researchos.local",
        rationale="Verified quotation and coordinates.",
        occurred_at="2026-07-15T14:30:00Z",
    )
    repeated = repository.review_evidence(
        "healthcheck-v11-method", decision="accepted", reviewer="reviewer@researchos.local",
        rationale="Verified quotation and coordinates.",
        occurred_at="2026-07-15T14:30:00Z",
    )
    assert repeated.review_id == accepted.review_id
    rejected = repository.review_evidence(
        "healthcheck-v11-method", decision="rejected", reviewer="reviewer@researchos.local",
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
                WHERE c.stable_key='evidence:healthcheck-v11-method'
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
