"""Repeatable DATA-002G reviewed-evidence graph acceptance check."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from dataclasses import replace
import os
from pathlib import Path

from app.knowledge.extraction.models import (
    EvidenceAdmission, ExtractionReviewState,
)
from app.knowledge.modeling.graph_builder import ScientificKnowledgeGraphBuilder
from app.knowledge.intake.models import (
    KnowledgeIntakeDecision, KnowledgeIntakeManifest,
)
from app.knowledge.repositories.postgres import PostgresScientificDataRepository
from app.knowledge.theory_pipeline import KnowledgeTheoryPipeline
from canonical_evidence import assessment, manifest
from canonical_repository import discovery_run
from representation_repository import SECOND_CONTENT, result


def timestamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def main() -> None:
    repository = PostgresScientificDataRepository(os.environ["DATABASE_URL"])
    record = discovery_run().records[0]
    source_representation = result(
        SECOND_CONTENT, "2026-07-15T13:05:00Z"
    )
    with repository._connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT decision_key,decision_hash,inspection_manifest_hash
                FROM screening_decisions
                WHERE decision_key='screening-repository-healthcheck'
            """)
            screening_id, screening_hash, inspection_hash = cursor.fetchone()
    extraction = manifest(
        source_representation.content_hash, inspection_hash,
        screening_id, screening_hash,
    )
    builder = ScientificKnowledgeGraphBuilder()
    pending_admissions = repository.resolve_evidence_admissions(
        tuple(item.object_id for item in extraction.objects)
    )
    pending_extraction = replace(extraction, objects=(extraction.objects[2],))
    try:
        builder.build(pending_extraction, (pending_admissions[2],))
    except ValueError as exc:
        assert "status=provisional" in str(exc)
    else:
        raise AssertionError("Graph builder accepted pending evidence")

    graph_extraction = replace(extraction, objects=extraction.objects[:2])
    incomplete = tuple(
        EvidenceAdmission(
            admission.evidence_object_id,
            ExtractionReviewState.ACCEPTED,
            None,
        )
        for admission in pending_admissions[:2]
    )
    try:
        builder.build(graph_extraction, incomplete)
    except ValueError as exc:
        assert "provenance is incomplete" in str(exc)
    else:
        raise AssertionError("Graph builder accepted missing review provenance")
    now = datetime.now(timezone.utc)
    method_review = repository.review_evidence(
        "healthcheck-v11-method", decision="accepted", reviewer="graph-reviewer@researchos.local",
        rationale=f"Accepted for graph healthcheck {timestamp(now)}.", occurred_at=timestamp(now),
        assessment=assessment(extraction, 0),
    )
    limitation_review = repository.review_evidence(
        "healthcheck-v11-limitation", decision="accepted", reviewer="graph-reviewer@researchos.local",
        rationale=f"Accepted for graph healthcheck {timestamp(now)}.",
        occurred_at=timestamp(now + timedelta(seconds=1)),
        assessment=assessment(extraction, 1),
    )
    accepted_admissions = repository.resolve_evidence_admissions(
        tuple(item.object_id for item in graph_extraction.objects)
    )
    missing_status = (
        EvidenceAdmission(
            graph_extraction.objects[0].object_id, None, None,
        ),
        accepted_admissions[1],
    )
    try:
        builder.build(graph_extraction, missing_status)
    except ValueError as exc:
        assert "status is missing" in str(exc)
    else:
        raise AssertionError("Graph builder accepted missing review status")
    graph = builder.build(graph_extraction, accepted_admissions)
    assert all(
        node.provenance is None
        or node.provenance.review_event.provenance_id
        in {method_review.provenance_id, limitation_review.provenance_id}
        for node in graph.nodes
    )
    intake_ids = tuple(sorted(
        item.object_id for item in graph_extraction.objects
    ))
    admission_by_id = {
        item.evidence_object_id: item for item in accepted_admissions
    }
    intake = KnowledgeIntakeManifest(
        "healthcheck-knowledge-intake-v2", extraction.extraction_id,
        extraction.manifest_hash, graph.graph_id, graph.content_hash,
        intake_ids, intake_ids,
        tuple(
            KnowledgeIntakeDecision(
                object_id, True,
                "Accepted human review verified",
                admission_by_id[object_id].review_event.provenance_id,
            )
            for object_id in intake_ids
        ),
        "graph-reviewer@researchos.local", extraction.created_at,
    ).finalized()
    first = repository.persist_graph(
        graph, occurred_at=extraction.created_at, intake=intake,
    )
    assert repository.persist_graph(
        graph, occurred_at=extraction.created_at, intake=intake,
    ) == first
    assert len(first) == len(graph.edges) == 2

    review_ids = (method_review.provenance_id, limitation_review.provenance_id)
    with repository._connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT count(DISTINCT n.node_id)
                FROM knowledge_nodes n
                JOIN canonical_objects c ON c.object_id=n.object_id
                WHERE c.stable_key IN (
                    'doi:10.0000/researchos.repository-healthcheck',
                    'evidence:healthcheck-v11-method',
                    'evidence:healthcheck-v11-limitation'
                )
            """)
            assert cursor.fetchone()[0] == 3
            cursor.execute("""
                SELECT count(*), count(DISTINCT e.provenance_id),
                       bool_and(e.review_status='accepted'),
                       bool_and(p.human_reviewer='graph-reviewer@researchos.local')
                FROM knowledge_edges e
                JOIN provenance_events p ON p.provenance_id=e.provenance_id
                WHERE p.event_payload->>'evidence_review_provenance_id' IN (%s,%s)
            """, review_ids)
            assert cursor.fetchone() == (2, 2, True, True)
            cursor.execute("""
                SELECT count(*),bool_and(content_hash=%s),
                       bool_and(graph_content_hash=%s)
                FROM knowledge_intake_manifests WHERE intake_key=%s
            """, (intake.content_hash, graph.content_hash, intake.intake_id))
            assert cursor.fetchone() == (1, True, True)

    theory_pipeline = KnowledgeTheoryPipeline(
        Path("/tmp/p0-theory"),
        {graph.graph_id: graph}, data_repository=repository,
    )
    theory_pipeline.build_theories(
        (graph.graph_id,), generated_by="graph-reviewer@researchos.local",
    )
    repository.review_evidence(
        "healthcheck-v11-limitation", decision="rejected",
        reviewer="graph-reviewer@researchos.local",
        rationale=f"Revoked after graph healthcheck {timestamp(now)}.",
        occurred_at=timestamp(now + timedelta(seconds=2)),
        assessment=assessment(extraction, 1),
    )
    mixed_admissions = repository.resolve_evidence_admissions(
        tuple(item.object_id for item in graph_extraction.objects)
    )
    try:
        builder.build(graph_extraction, mixed_admissions)
    except ValueError as exc:
        assert "not accepted" in str(exc)
    else:
        raise AssertionError("Graph builder accepted mixed review states")
    try:
        repository.persist_graph(graph, occurred_at=extraction.created_at)
    except ValueError as exc:
        assert "not accepted" in str(exc)
    else:
        raise AssertionError("Graph persistence accepted rejected evidence")
    try:
        theory_pipeline.build_theories(
            (graph.graph_id,), generated_by="graph-reviewer@researchos.local",
        )
    except ValueError as exc:
        assert "contains rejected evidence" in str(exc)
    else:
        raise AssertionError("Theory construction accepted stale graph evidence")
    with repository._connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT p.event_payload->>'evidence_object_id', e.review_status
                FROM knowledge_edges e
                JOIN provenance_events p ON p.provenance_id=e.provenance_id
                WHERE p.event_payload->>'evidence_review_provenance_id' IN (%s,%s)
                ORDER BY 1
            """, review_ids)
            states = dict(cursor.fetchall())
    assert states == {
        "healthcheck-v11-limitation": "rejected",
        "healthcheck-v11-method": "accepted",
    }, states
    print("canonical graph healthcheck: passed")


if __name__ == "__main__":
    main()
