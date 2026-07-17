from pathlib import Path
from dataclasses import replace

from app.knowledge.extraction.models import (
    DocumentCoordinates, EpistemicClassification, EvidenceAdmission,
    EvidenceReviewAssessment, EvidenceReviewEvent,
    ExtractedScientificObject, ExtractionManifest, ExtractionReviewState,
    ScientificObjectType,
)
from app.knowledge.modeling.graph_builder import ScientificKnowledgeGraphBuilder
from app.knowledge.modeling.models import KnowledgeEdgeType
from app.knowledge.modeling.persistence import KnowledgeGraphStore


def obj(identifier, kind, content, page=1):
    return ExtractedScientificObject(
        identifier, kind, content, DocumentCoordinates(page, 0, len(content), f"hash-{identifier}"),
        0.7, ExtractionReviewState.PROVISIONAL, "parser", "1.0",
    )


def manifest():
    return ExtractionManifest(
        "extraction-1", "document-1", "content-hash", "time", "parser", "1.0",
        (
            obj("method-1", ScientificObjectType.METHOD, "Survey"),
            obj("result-1", ScientificObjectType.RESULT, "Association found"),
            obj("limitation-1", ScientificObjectType.LIMITATION, "One region only"),
            obj("conclusion-1", ScientificObjectType.CONCLUSION, "Governance matters"),
        ),
    )


def admission(identifier, state=ExtractionReviewState.ACCEPTED, *, event=True):
    assessment = EvidenceReviewAssessment(
        True, True, True, .9, EpistemicClassification.OBSERVED_FACT,
        "a" * 64, "b" * 64,
    )
    review = (
        EvidenceReviewEvent(
            f"review-{identifier}", identifier, state, "reviewer@example",
            "Source quotation and context reviewed", "review-time",
            f"provenance-{identifier}", "pending", assessment,
            assessment.digest(),
        )
        if event else None
    )
    return EvidenceAdmission(identifier, state, review)


def admissions(*, overrides=None):
    overrides = overrides or {}
    return tuple(
        overrides.get(identifier, admission(identifier))
        for identifier in ("method-1", "result-1", "limitation-1", "conclusion-1")
    )


def test_graph_is_deterministic_traceable_and_assertional(tmp_path: Path) -> None:
    builder = ScientificKnowledgeGraphBuilder()
    first = builder.build(manifest(), admissions())
    second = builder.build(manifest(), admissions())
    assert first == second
    assert first.verify()
    assert len(first.nodes) == 5
    assert {edge.edge_type for edge in first.edges} == {
        KnowledgeEdgeType.CONTAINS, KnowledgeEdgeType.USES_METHOD, KnowledgeEdgeType.SUPPORTS,
    }
    assert all(edge.assertion for edge in first.edges)
    assert all(edge.provenance.quote_hash for edge in first.edges)
    assert all(
        edge.provenance.review_event.provenance_id
        for edge in first.edges
    )
    store = KnowledgeGraphStore(tmp_path)
    assert store.save(first) == store.save(second)


def test_graph_integrity_rejects_unfinalized_snapshot(tmp_path: Path) -> None:
    import pytest
    graph = ScientificKnowledgeGraphBuilder().build(manifest(), admissions())
    object.__setattr__(graph, "content_hash", "tampered")
    with pytest.raises(ValueError, match="integrity"):
        KnowledgeGraphStore(tmp_path).save(graph)


def test_graph_builder_rejects_unreviewed_and_rejected_evidence() -> None:
    import pytest
    builder = ScientificKnowledgeGraphBuilder()
    for state in (
        ExtractionReviewState.PROVISIONAL,
        ExtractionReviewState.REJECTED,
    ):
        overridden = admissions(overrides={
            "result-1": admission("result-1", state),
        })
        with pytest.raises(ValueError, match="not accepted"):
            builder.build(manifest(), overridden)


def test_graph_builder_rejects_mixed_and_missing_review_state() -> None:
    import pytest
    builder = ScientificKnowledgeGraphBuilder()
    mixed = admissions(overrides={
        "result-1": admission(
            "result-1", ExtractionReviewState.REJECTED,
        ),
    })
    with pytest.raises(ValueError, match="not accepted"):
        builder.build(manifest(), mixed)
    missing = admissions(overrides={
        "result-1": EvidenceAdmission("result-1", None, None),
    })
    with pytest.raises(ValueError, match="status is missing"):
        builder.build(manifest(), missing)


def test_graph_builder_rejects_missing_review_event_and_direct_bypass() -> None:
    import pytest
    builder = ScientificKnowledgeGraphBuilder()
    incomplete = admissions(overrides={
        "result-1": admission("result-1", event=False),
    })
    with pytest.raises(ValueError, match="provenance is incomplete"):
        builder.build(manifest(), incomplete)
    with pytest.raises(ValueError, match="Canonical repository is required"):
        builder.build(manifest())


def test_graph_builder_rejects_each_incomplete_review_provenance_field() -> None:
    import pytest
    builder = ScientificKnowledgeGraphBuilder()
    base = admission("result-1")
    for field in (
        "reviewer", "rationale", "occurred_at", "provenance_id",
        "previous_state",
    ):
        incomplete_event = replace(base.review_event, **{field: ""})
        incomplete = admissions(overrides={
            "result-1": replace(base, review_event=incomplete_event),
        })
        with pytest.raises(ValueError, match="provenance is incomplete"):
            builder.build(manifest(), incomplete)


def test_graph_snapshot_cannot_bypass_missing_review_provenance(
    tmp_path: Path,
) -> None:
    import pytest
    graph = ScientificKnowledgeGraphBuilder().build(manifest(), admissions())
    nodes = tuple(
        replace(
            node,
            provenance=replace(node.provenance, review_event=None),
        )
        if node.provenance is not None else node
        for node in graph.nodes
    )
    unsafe = replace(graph, nodes=nodes, content_hash="").finalized()

    with pytest.raises(ValueError, match="provenance is incomplete"):
        KnowledgeGraphStore(tmp_path).save(unsafe)
