"""Repeatable DATA-002A/B integration verification against the local stack."""

from __future__ import annotations

import os

from app.knowledge.models import (
    DiscoveryContract,
    DiscoveryRun,
    LiteratureRecord,
    MatchKind,
    ScientificQuestion,
    SearchPlan,
    SourceRecord,
)
from app.knowledge.discovery.source_registry import (
    CANONICAL_SOURCE_DEFINITIONS,
)
from app.knowledge.repositories.postgres import PostgresScientificDataRepository
from app.knowledge.retrieval.models import (
    EnrichedMetadata,
    LifecycleSignal,
    MetadataObservation,
    MetadataRun,
)


DOI = "10.0000/researchos.repository-healthcheck"
SOURCE_HASH = "repository-healthcheck-source-v1"


def discovery_run() -> DiscoveryRun:
    source = SourceRecord(
        provider="openalex",
        source_id="W-REPOSITORY-HEALTHCHECK",
        retrieved_at="2026-07-15T12:00:00Z",
        response_hash=SOURCE_HASH,
        raw={
            "id": "W-REPOSITORY-HEALTHCHECK",
            "doi": f"https://doi.org/{DOI}",
            "title": "ResearchOS canonical repository health check",
            "type": "article",
        },
    )
    record = LiteratureRecord(
        record_id="repository-healthcheck",
        title="ResearchOS canonical repository health check",
        authors=("ResearchOS",),
        year=2026,
        doi=DOI,
        abstract="A deterministic integration record.",
        venue="ResearchOS",
        work_type="article",
        source_records=(source,),
        match_kind=MatchKind.EXACT,
    )
    return DiscoveryRun(
        run_id="repository-healthcheck",
        question=ScientificQuestion("repository-healthcheck", "Is persistence healthy?"),
        discovery_contract=DiscoveryContract(
            "repository-healthcheck-contract", "researchos-default",
            "repository-healthcheck", "repository-healthcheck",
            "Canonical repository healthcheck", ("scholarly_index",),
            ("Healthcheck record",), ("Unrelated record",), ("en",),
            ("journal_article",), ("reported_result",), 1, 25,
            "metadata_only", "human_review_required",
            ("healthcheck complete",),
        ),
        source_definitions=tuple(
            item for item in CANONICAL_SOURCE_DEFINITIONS
            if item.name == "openalex"
        ),
        search_plan=SearchPlan("repository-healthcheck", "healthcheck", ("openalex",)),
        started_at="2026-07-15T12:00:00Z",
        records=(record,),
    )


def metadata_run() -> MetadataRun:
    observation = MetadataObservation(
        record_id="repository-healthcheck",
        provider="openalex",
        source_id="W-REPOSITORY-HEALTHCHECK",
        response_hash=SOURCE_HASH,
        values={"citation_count": 7, "concepts": ["research infrastructure"]},
    )
    enriched = EnrichedMetadata(
        record_id="repository-healthcheck",
        identifiers=(("doi", DOI),),
        concepts=("research infrastructure",),
        citation_count=7,
        open_access=True,
        lifecycle=LifecycleSignal.ACTIVE,
        observations=(observation,),
        conflicts=(),
    )
    return MetadataRun(
        metadata_run_id="repository-healthcheck",
        discovery_run_id="repository-healthcheck",
        created_at="2026-07-15T12:05:00Z",
        records=(enriched,),
        citation_edges=(),
    )


def main() -> None:
    repository = PostgresScientificDataRepository(os.environ["DATABASE_URL"])
    repository.persist_discovery(discovery_run())
    repository.persist_discovery(discovery_run())
    repository.persist_metadata(metadata_run())
    repository.persist_metadata(metadata_run())

    with repository._connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT d.metadata_version,
                       count(DISTINCT r.source_id),
                       count(DISTINCT o.observation_id)
                FROM canonical_objects c
                JOIN scientific_documents d ON d.document_id=c.object_id
                LEFT JOIN document_source_references r ON r.document_id=d.document_id
                LEFT JOIN metadata_observations o ON o.document_id=d.document_id
                WHERE c.stable_key=%s
                GROUP BY d.metadata_version
            """, (f"doi:{DOI}",))
            row = cursor.fetchone()

    assert row == (2, 1, 2), row
    print("canonical repository healthcheck: passed")


if __name__ == "__main__":
    main()
