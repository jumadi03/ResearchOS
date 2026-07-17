"""Repeatable DATA-002A/B integration verification against the local stack."""

from __future__ import annotations

from dataclasses import replace
import os

from app.knowledge.models import (
    DiscoveryContract,
    DiscoveryRun,
    LiteratureRecord,
    MatchKind, ProviderEnumeration, QueryConcept,
    ScientificQuestion,
    SearchPlan,
    SourceRecord,
)
from app.knowledge.discovery.source_registry import (
    CANONICAL_SOURCE_DEFINITIONS,
)
from app.knowledge.discovery.query_planner import ScientificQueryPlanner
from app.knowledge.repositories.postgres import PostgresScientificDataRepository
from app.knowledge.retrieval.models import (
    EnrichedMetadata,
    LifecycleSignal,
    MetadataObservation,
    MetadataRun,
)
from app.knowledge.retrieval.snowballing import (
    CitationDirection, CitationStoppingReason, CitationTraversalEdge,
    CitationTraversalCandidate, CitationTraversalRun,
)


DOI = "10.0000/researchos.repository-healthcheck"
SOURCE_HASH = "repository-healthcheck-source-v1"


def discovery_run() -> DiscoveryRun:
    question = ScientificQuestion(
        "repository-healthcheck", "Is persistence healthy?",
    )
    contract = DiscoveryContract(
        "repository-healthcheck-contract", "researchos-default",
        "repository-healthcheck", "repository-healthcheck",
        "Canonical repository healthcheck", ("scholarly_index",),
        ("Healthcheck record",), ("Unrelated record",), ("en",),
        ("journal_article",), ("reported_result",), 1, 25,
        "metadata_only", "human_review_required",
        ("healthcheck complete",),
    )
    draft = SearchPlan(
        "repository-healthcheck", "healthcheck", ("openalex",),
    )
    sources = tuple(
        item for item in CANONICAL_SOURCE_DEFINITIONS
        if item.name == "openalex"
    )
    plan = ScientificQueryPlanner().plan(
        question, contract, draft,
        (QueryConcept(
            "repository-healthcheck-concept", "healthcheck", (),
            ("research infrastructure",), "repository-verifier",
            "Canonical repository integration verification",
        ),),
        sources,
    )
    source_query = plan.source_queries[0]
    source = SourceRecord(
        provider="openalex",
        source_id="W-REPOSITORY-HEALTHCHECK",
        retrieved_at="2026-07-15T12:00:00Z",
        response_hash=SOURCE_HASH,
        source_definition_id=sources[0].source_id,
        query_family_id=source_query.family_id,
        source_query=source_query.query,
        discovery_rank=1,
        page_number=1,
        request_url="https://api.openalex.org/works?search=healthcheck",
        canonical_url="https://openalex.org/W-REPOSITORY-HEALTHCHECK",
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
        question=question, discovery_contract=contract,
        source_definitions=sources, search_plan=plan,
        started_at="2026-07-15T12:00:00Z",
        enumerations=(ProviderEnumeration(
            "openalex", sources[0].source_id, source_query.family_id,
            25, 1, 1, 1, False,
        ),),
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


def citation_traversal_run() -> CitationTraversalRun:
    return CitationTraversalRun(
        traversal_id="citation-repository-healthcheck-v2",
        discovery_run_id="repository-healthcheck",
        discovery_contract_id="repository-healthcheck-contract",
        seed_record_id="repository-healthcheck",
        directions=(
            CitationDirection.BACKWARD, CitationDirection.FORWARD,
        ),
        maximum_depth=1,
        retrieval_budget=25,
        created_at="2026-07-15T12:06:00Z",
        candidates=(
            CitationTraversalCandidate(
                "W-REFERENCE", "openalex", 1, "c" * 64,
                "https://api.openalex.org/works/W-REPOSITORY-HEALTHCHECK",
                "Referenced work", None,
            ),
            CitationTraversalCandidate(
                "W-CITING", "openalex", 1, "d" * 64,
                "https://api.openalex.org/works?filter=cites:W-REPOSITORY-HEALTHCHECK",
                "Citing work", None,
            ),
        ),
        edges=(
            CitationTraversalEdge(
                "W-REPOSITORY-HEALTHCHECK", "W-REFERENCE",
                CitationDirection.BACKWARD, 1, "openalex", "c" * 64,
                "https://api.openalex.org/works/W-REPOSITORY-HEALTHCHECK",
            ),
            CitationTraversalEdge(
                "W-CITING", "W-REPOSITORY-HEALTHCHECK",
                CitationDirection.FORWARD, 1, "openalex", "d" * 64,
                "https://api.openalex.org/works?filter=cites:W-REPOSITORY-HEALTHCHECK",
            ),
        ),
        failures=(),
        stopping_reasons=(CitationStoppingReason.DEPTH_LIMIT,),
    ).finalized()


def main() -> None:
    repository = PostgresScientificDataRepository(os.environ["DATABASE_URL"])
    repository.persist_discovery(discovery_run())
    repository.persist_discovery(discovery_run())
    repository.persist_metadata(metadata_run())
    repository.persist_metadata(metadata_run())
    repository.persist_citation_traversal(citation_traversal_run())
    repository.persist_citation_traversal(citation_traversal_run())

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
            cursor.execute("""
                SELECT count(*)
                FROM scientific_identifiers i
                JOIN canonical_objects c ON c.object_id=i.document_id
                WHERE c.stable_key=%s
            """, (f"doi:{DOI}",))
            identifier_count = cursor.fetchone()[0]
            cursor.execute("""
                SELECT count(*)
                FROM identity_resolution_events e
                JOIN canonical_objects c ON c.object_id=e.document_id
                WHERE c.stable_key=%s
            """, (f"doi:{DOI}",))
            resolution_count = cursor.fetchone()[0]
            cursor.execute("""
                SELECT
                    count(DISTINCT r.traversal_id),
                    count(DISTINCT e.source_identifier || '>' ||
                          e.target_identifier || ':' || e.direction),
                    count(DISTINCT c.identifier),
                    count(DISTINCT f.identifier)
                FROM citation_traversal_runs r
                LEFT JOIN citation_traversal_edges e
                  ON e.traversal_id=r.traversal_id
                LEFT JOIN citation_traversal_candidates c
                  ON c.traversal_id=r.traversal_id
                LEFT JOIN citation_traversal_failures f
                  ON f.traversal_id=r.traversal_id
                WHERE r.traversal_id='citation-repository-healthcheck-v2'
            """)
            citation_counts = cursor.fetchone()
            cursor.execute("SAVEPOINT immutable_resolution_check")
            try:
                cursor.execute("""
                    UPDATE identity_resolution_events SET rationale='mutated'
                    WHERE document_id=(
                        SELECT object_id FROM canonical_objects
                        WHERE stable_key=%s
                    )
                """, (f"doi:{DOI}",))
            except Exception:
                cursor.execute(
                    "ROLLBACK TO SAVEPOINT immutable_resolution_check"
                )
            else:
                raise AssertionError(
                    "Identity resolution immutable trigger did not reject update"
                )
            original = discovery_run().records[0]
            source = replace(
                original.source_records[0],
                source_id="W-LATE-IDENTIFIER",
                response_hash="late-identifier-v1",
            )
            without_doi = replace(
                original, record_id="late-identifier-healthcheck",
                doi=None, source_records=(source,),
            )
            initial_id = repository._upsert_document(cursor, without_doi)
            with_doi = replace(
                without_doi, doi="10.0000/researchos.late-identifier",
                source_records=(replace(
                    source, response_hash="late-identifier-v2",
                ),),
            )
            resolved_id = repository._upsert_document(cursor, with_doi)

    assert row == (2, 1, 2), row
    assert identifier_count == 2, identifier_count
    assert resolution_count == 1, resolution_count
    assert citation_counts == (1, 2, 2, 0), citation_counts
    assert resolved_id == initial_id, (initial_id, resolved_id)
    print("canonical repository healthcheck: passed")


if __name__ == "__main__":
    main()
