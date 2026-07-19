"""SGF-030A compliance for evidence, persistence, and graph vocabulary."""

from pathlib import Path
import re

from app.knowledge.extraction.models import (
    CANONICAL_EVIDENCE_TYPES,
    PERSISTENCE_EVIDENCE_TYPES,
    DocumentCoordinates,
    EpistemicClassification,
    EvidenceAdmission,
    EvidenceReviewAssessment,
    EvidenceReviewEvent,
    ExtractedScientificObject,
    ExtractionManifest,
    ExtractionReviewState,
    ScientificObjectType,
)
from app.knowledge.modeling.graph_builder import ScientificKnowledgeGraphBuilder
from app.knowledge.modeling.models import KnowledgeEdgeType, KnowledgeNodeType


def accepted(identifier: str) -> EvidenceAdmission:
    assessment = EvidenceReviewAssessment(
        True, True, True, 0.9,
        EpistemicClassification.OBSERVED_FACT,
        "a" * 64, "b" * 64,
    )
    event = EvidenceReviewEvent(
        f"review-{identifier}", identifier, ExtractionReviewState.ACCEPTED,
        "reviewer@example", "Source quotation and context reviewed",
        "2026-07-19T00:00:00Z", f"provenance-{identifier}", "pending",
        assessment, assessment.digest(),
    )
    return EvidenceAdmission(identifier, ExtractionReviewState.ACCEPTED, event)


def extracted(identifier: str, kind: ScientificObjectType):
    content = f"Canonical {kind.value}"
    return ExtractedScientificObject(
        identifier, kind,
        content, DocumentCoordinates(1, 0, len(content), f"hash-{identifier}"),
        0.9, ExtractionReviewState.PROVISIONAL, "parser", "1.0",
    )


def test_every_extraction_type_has_an_identical_graph_node_type():
    assert CANONICAL_EVIDENCE_TYPES == {item.value for item in KnowledgeNodeType} - {
        KnowledgeNodeType.SOURCE_DOCUMENT.value
    }
    for kind in ScientificObjectType:
        assert KnowledgeNodeType(kind.value).value == kind.value


def test_graph_preserves_population_observation_and_measurement_semantics():
    objects = (
        extracted("population-1", ScientificObjectType.POPULATION),
        extracted("observation-1", ScientificObjectType.OBSERVATION),
        extracted("measurement-1", ScientificObjectType.MEASUREMENT),
    )
    manifest = ExtractionManifest(
        "extraction-ontology", "document-1", "content-hash",
        "2026-07-19T00:00:00Z", "parser", "1.0", objects,
    )
    graph = ScientificKnowledgeGraphBuilder().build(
        manifest, tuple(accepted(item.object_id) for item in objects)
    )
    node_types = {
        node.node_type.value
        for node in graph.nodes
        if node.node_type is not KnowledgeNodeType.SOURCE_DOCUMENT
    }
    assert node_types == {"population", "observation", "measurement"}
    assert graph.verify()


def test_migration_021_persistence_vocabulary_matches_ontology_contract():
    migration = (
        Path(__file__).resolve().parents[4]
        / "deploy" / "postgres" / "init" / "021_extraction_manifests.sql"
    ).read_text(encoding="utf-8")
    constraint = re.search(
        r"evidence_type\s+IN\s*\((.*?)\)\s*\)",
        migration,
        flags=re.DOTALL,
    )
    assert constraint is not None
    persisted = set(re.findall(r"'([^']+)'", constraint.group(1)))
    assert persisted == PERSISTENCE_EVIDENCE_TYPES


def test_legacy_generic_evidence_is_persistence_only_not_an_extraction_type():
    assert "evidence" in PERSISTENCE_EVIDENCE_TYPES
    assert "evidence" not in CANONICAL_EVIDENCE_TYPES
    try:
        ScientificObjectType("evidence")
    except ValueError:
        pass
    else:
        raise AssertionError("legacy generic evidence became an extraction type")


def test_graph_relation_vocabulary_matches_sgf_030():
    assert {item.value for item in KnowledgeEdgeType} == {
        "derived_from", "contains", "part_of", "cites", "supports",
        "contradicts", "extends", "replicates", "uses_method", "measures",
        "has_limitation", "interprets", "infers_from", "supersedes",
        "corrects", "invalidates", "represents",
    }
