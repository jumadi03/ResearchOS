from pathlib import Path

from app.knowledge.extraction.models import (
    DocumentCoordinates, ExtractedScientificObject, ExtractionManifest,
    ExtractionReviewState, ScientificObjectType,
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


def test_graph_is_deterministic_traceable_and_assertional(tmp_path: Path) -> None:
    builder = ScientificKnowledgeGraphBuilder()
    first = builder.build(manifest())
    second = builder.build(manifest())
    assert first == second
    assert first.verify()
    assert len(first.nodes) == 5
    assert {edge.edge_type for edge in first.edges} == {
        KnowledgeEdgeType.CONTAINS, KnowledgeEdgeType.USES_METHOD, KnowledgeEdgeType.SUPPORTS,
    }
    assert all(edge.assertion for edge in first.edges)
    assert all(edge.provenance.quote_hash for edge in first.edges)
    store = KnowledgeGraphStore(tmp_path)
    assert store.save(first) == store.save(second)


def test_graph_integrity_rejects_unfinalized_snapshot(tmp_path: Path) -> None:
    import pytest
    graph = ScientificKnowledgeGraphBuilder().build(manifest())
    object.__setattr__(graph, "content_hash", "tampered")
    with pytest.raises(ValueError, match="integrity"):
        KnowledgeGraphStore(tmp_path).save(graph)
