from pathlib import Path

from app.knowledge.extraction.models import ExtractionReviewState
from app.knowledge.modeling.models import (
    GraphProvenance, KnowledgeEdge, KnowledgeEdgeType, KnowledgeNode,
    KnowledgeNodeType, ScientificKnowledgeGraph,
)
from app.knowledge.theory.builder import TheoryBuilder
from app.knowledge.theory.models import TheoryReviewState
from app.knowledge.theory.persistence import TheoryBundleStore


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
