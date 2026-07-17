"""Repeatable SCAN-001I canonical screening-decision acceptance check."""

import os

from app.knowledge.repositories.postgres import PostgresScientificDataRepository
from app.knowledge.screening.models import (
    ScreeningDecision, ScreeningDimension, ScreeningReason, ScreeningStatus,
)
from canonical_repository import discovery_run


def main() -> None:
    repository = PostgresScientificDataRepository(os.environ["DATABASE_URL"])
    record = discovery_run().records[0]
    with repository._connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT document_id,document_content_hash,manifest_hash
                FROM source_inspections
                WHERE inspection_key='inspection-repository-healthcheck'
            """)
            source_document_id, content_hash, inspection_hash = cursor.fetchone()
    reasons = tuple(
        ScreeningReason(dimension, f"{dimension.value.upper()}_PASS", True, "passed")
        for dimension in ScreeningDimension
    )
    decision = ScreeningDecision(
        "screening-repository-healthcheck", source_document_id,
        record.record_id, "contract-healthcheck", content_hash,
        inspection_hash, ScreeningStatus.ELIGIBLE, reasons,
        "researchos-scientific-screening", "1.0.0",
        "2026-07-15T13:15:00Z",
    ).finalized()
    first = repository.persist_screening_decision(record, decision)
    assert repository.persist_screening_decision(record, decision) == first
    with repository._connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT status,reasons,decision_hash FROM screening_decisions
                WHERE decision_key=%s
            """, (decision.decision_id,))
            row = cursor.fetchone()
    assert row[0] == "eligible"
    assert len(row[1]) == 4
    assert row[2] == decision.decision_hash
    print("screening decision healthcheck: passed")


if __name__ == "__main__":
    main()
