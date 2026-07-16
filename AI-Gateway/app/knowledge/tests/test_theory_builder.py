from pathlib import Path

from app.knowledge.extraction.models import ExtractionReviewState
from app.knowledge.modeling.models import (
    GraphProvenance, KnowledgeEdge, KnowledgeEdgeType, KnowledgeNode,
    KnowledgeNodeType, ScientificKnowledgeGraph,
)
from app.knowledge.theory.builder import TheoryBuilder
from app.knowledge.theory.models import TheoryReviewState
from app.knowledge.theory.persistence import TheoryBundleStore
from app.knowledge.validation.engine import ValidationEngine
from app.knowledge.validation.models import RiskOfBias, ValidationStatus


def graph(identifier, conclusion):
    provenance = GraphProvenance("extraction", "document", f"object-{identifier}", 1, f"quote-{identifier}", 0.7, ExtractionReviewState.PROVISIONAL)
    result = KnowledgeNode(f"result-{identifier}", KnowledgeNodeType.RESULT, "Result", provenance)
    theory = KnowledgeNode(f"conclusion-{identifier}", KnowledgeNodeType.CONCLUSION, conclusion, provenance)
    edge = KnowledgeEdge(f"edge-{identifier}", result.node_id, theory.node_id, KnowledgeEdgeType.SUPPORTS, True, provenance)
    return ScientificKnowledgeGraph(f"graph-{identifier}", f"extraction-{identifier}", (result, theory), (edge,)).finalized()


def test_theory_builder_aggregates_support_and_represents_competition(tmp_path: Path) -> None:
    bundle = TheoryBuilder().build((
        graph("one", "Governance improves village performance"),
        graph("two", "Governance does not improve village performance"),
    ), created_at="time")
    assert bundle.verify()
    assert len(bundle.proposals) == 2
    assert all(item.support_count == 1 for item in bundle.proposals)
    assert len(bundle.competing) == 1
    assert TheoryBundleStore(tmp_path).save(bundle).exists()


def test_equivalent_claims_consolidate_across_graphs_without_losing_provenance() -> None:
    bundle = TheoryBuilder().build((
        graph("one", "Open science improves reproducibility."),
        graph("two", "  open SCIENCE improves reproducibility  "),
    ), created_at="time")

    assert len(bundle.proposals) == 1
    proposal = bundle.proposals[0]
    assert proposal.statement == "Open science improves reproducibility."
    assert proposal.support_count == 2
    assert {item.graph_id for item in proposal.evidence} == {"graph-one", "graph-two"}
    assert {item.object_id for item in proposal.evidence} == {"object-one", "object-two"}

    reversed_bundle = TheoryBuilder().build(tuple(reversed((
        graph("one", "Open science improves reproducibility."),
        graph("two", "  open SCIENCE improves reproducibility  "),
    ))), created_at="time")
    assert reversed_bundle.content_hash == bundle.content_hash

    report = ValidationEngine().validate(
        bundle, assessed_at="2026-07-16T00:00:00Z",
        search_completed_at="2026-07-16T00:00:00Z", max_age_days=180,
        bias_by_theory={proposal.theory_id: RiskOfBias.LOW}, reviewer="reviewer@example",
    )
    assert report.status is ValidationStatus.PASS
    assert report.assessments[0].independent_graphs == 2


def test_related_but_non_equivalent_claims_remain_separate() -> None:
    bundle = TheoryBuilder().build((
        graph("one", "Open science improves reproducibility"),
        graph("two", "Open science improves data availability"),
    ), created_at="time")

    assert len(bundle.proposals) == 2


def test_reviewer_alignment_merges_accepted_theories_and_records_audit_event() -> None:
    builder = TheoryBuilder()
    bundle = builder.build((
        graph("one", "Open practices improve reproducibility"),
        graph("two", "Transparent workflows support reproducible research"),
    ), created_at="time")
    source_ids = tuple(item.theory_id for item in bundle.proposals)
    for theory_id in source_ids:
        bundle = builder.review(
            bundle, theory_id=theory_id, decision=TheoryReviewState.ACCEPTED,
            reviewer="reviewer@example", rationale="Source claim reviewed",
            occurred_at=f"review-{theory_id}",
        )

    aligned = builder.align(
        bundle, theory_ids=source_ids,
        statement="Open and transparent practices improve reproducibility",
        reviewer="reviewer@example", rationale="Scoped constructs and outcomes match",
        occurred_at="alignment-time",
    )

    assert aligned.verify() and len(aligned.proposals) == 1
    proposal = aligned.proposals[0]
    assert proposal.review_state is TheoryReviewState.ACCEPTED
    assert proposal.support_count == 2
    assert {item.graph_id for item in proposal.evidence} == {"graph-one", "graph-two"}
    assert aligned.alignments[0].source_theory_ids == tuple(sorted(source_ids))
    assert aligned.alignments[0].resulting_theory_id == proposal.theory_id
    assert aligned.alignments[0].reviewer == "reviewer@example"


def test_alignment_fails_closed_without_prior_acceptance() -> None:
    import pytest
    builder = TheoryBuilder()
    bundle = builder.build((
        graph("one", "Open practices improve reproducibility"),
        graph("two", "Transparent workflows support reproducible research"),
    ), created_at="time")

    with pytest.raises(ValueError, match="accepted first"):
        builder.align(
            bundle, theory_ids=tuple(item.theory_id for item in bundle.proposals),
            statement="Open practices improve reproducibility", reviewer="reviewer@example",
            rationale="Constructs match", occurred_at="alignment-time",
        )


def test_alignment_candidates_are_advisory_ranked_and_accepted_only() -> None:
    builder = TheoryBuilder()
    bundle = builder.build((
        graph("one", "Open science practices improve reproducibility"),
        graph("two", "Open research practices support reproducibility"),
        graph("three", "Funding affects publication speed"),
    ), created_at="time")
    related_ids = {
        item.theory_id for item in bundle.proposals
        if "reproducibility" in item.statement
    }
    for theory_id in related_ids:
        bundle = builder.review(
            bundle, theory_id=theory_id, decision=TheoryReviewState.ACCEPTED,
            reviewer="reviewer@example", rationale="Claim reviewed", occurred_at=theory_id,
        )

    candidates = builder.alignment_candidates(bundle)

    assert len(candidates) == 1
    assert set(candidates[0].theory_ids) == related_ids
    assert candidates[0].graph_ids == ("graph-one", "graph-two")
    assert candidates[0].lexical_overlap_score == 0.4286
    assert candidates[0].advisory is True


def test_theory_review_is_attributable_and_requires_rationale() -> None:
    import pytest
    builder = TheoryBuilder()
    bundle = builder.build((graph("one", "Governance matters"),), created_at="time")
    reviewed = builder.review(
        bundle, theory_id=bundle.proposals[0].theory_id,
        decision=TheoryReviewState.ACCEPTED, reviewer="reviewer@example",
        rationale="Evidence inspected", occurred_at="later",
    )
    assert reviewed.proposals[0].review_state is TheoryReviewState.ACCEPTED
    assert reviewed.reviews[0].reviewer == "reviewer@example"
    assert reviewed.content_hash != bundle.content_hash
    with pytest.raises(ValueError, match="rationale"):
        builder.review(bundle, theory_id=bundle.proposals[0].theory_id, decision=TheoryReviewState.REJECTED, reviewer="x", rationale="", occurred_at="later")
