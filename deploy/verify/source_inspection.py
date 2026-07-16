"""Repeatable SCAN-001G factual source-inspection acceptance check."""

from dataclasses import replace
from hashlib import sha256
import os

from app.knowledge.inspection.models import PageInspection, SourceInspection
from app.knowledge.repositories.postgres import PostgresScientificDataRepository
from canonical_repository import discovery_run
from representation_repository import SECOND_CONTENT, result


def main() -> None:
    repository = PostgresScientificDataRepository(os.environ["DATABASE_URL"])
    record = discovery_run().records[0]
    source = record.source_records[0]
    representation = replace(
        result(SECOND_CONTENT, "2026-07-15T13:05:00Z"),
        source_definition_id=source.source_definition_id,
        query_family_id=source.query_family_id,
        capture_manifest_hash=None,
    )
    page_text = "METHODS\nFactual structure only."
    inspection = SourceInspection(
        "inspection-repository-healthcheck",
        "source-document-healthcheck", representation.content_hash,
        representation.capture_manifest_hash or "",
        "2026-07-15T13:10:00Z",
        "researchos-pdf-structure-inspector", "1.0.0",
        "application/pdf", "1.7", False, 1,
        (("/Title", "Repository healthcheck"),),
        (PageInspection(
            1, len(page_text), sha256(page_text.encode()).hexdigest(),
            True, (),
        ),),
        (), True,
    ).finalized()
    first = repository.persist_source_inspection(record, inspection)
    assert repository.persist_source_inspection(record, inspection) == first

    try:
        repository.persist_source_inspection(
            record, replace(
                inspection, raw_capture_manifest_hash="0" * 64,
                manifest_hash="",
            ).finalized(),
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Invented raw-capture provenance was accepted")

    with repository._connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT page_count,document_metadata,pages,complete,manifest_hash
                FROM source_inspections WHERE inspection_key=%s
            """, (inspection.inspection_id,))
            row = cursor.fetchone()
    assert row[0] == 1 and row[1]["/Title"] == "Repository healthcheck"
    assert row[2][0]["text_hash"] == inspection.pages[0].text_hash
    assert row[3] is True and row[4] == inspection.manifest_hash
    print("source inspection healthcheck: passed")


if __name__ == "__main__":
    main()
