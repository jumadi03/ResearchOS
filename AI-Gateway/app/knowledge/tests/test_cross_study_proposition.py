from hashlib import sha256

import pytest

from app.knowledge.extraction.models import (
    EpistemicClassification, EvidenceReviewAssessment, EvidenceReviewEvent,
    ExtractionReviewState,
)
from app.knowledge.modeling.models import (
    GraphProvenance, KnowledgeEdge, KnowledgeEdgeType, KnowledgeNode,
    KnowledgeNodeType, ScientificKnowledgeGraph,
)
from app.knowledge.modeling.persistence import KnowledgeGraphStore
from app.knowledge.theory.cross_study import (
    CrossStudyProposition, CrossStudyPropositionState,
    CrossStudyPropositionStore, bind_cross_study_evidence,
    proposition_theory_bundle,
)
from app.knowledge.theory.models import EvidenceStance
from app.knowledge.theory_pipeline import KnowledgeTheoryPipeline


def graph(graph_id: str, object_id: str, document_id: str):
    quote_hash = sha256(f"quote:{object_id}".encode()).hexdigest()
    assessment = EvidenceReviewAssessment(
        True, True, True, .9, EpistemicClassification.OBSERVED_FACT,
        quote_hash, sha256(f"manifest:{graph_id}".encode()).hexdigest(),
    )
    review = EvidenceReviewEvent(
        f"review-{object_id}", object_id, ExtractionReviewState.ACCEPTED,
        "reviewer@example", "Exact result reviewed",
        "2026-07-19T00:00:00Z", f"provenance-{object_id}", "pending",
        assessment, assessment.digest(),
    )
    provenance = GraphProvenance(
        f"extraction-{graph_id}", document_id, object_id, 1, quote_hash,
        .9, ExtractionReviewState.ACCEPTED, review,
    )
    source = KnowledgeNode(
        f"node:{document_id}", KnowledgeNodeType.SOURCE_DOCUMENT, document_id,
    )
    result = KnowledgeNode(
        f"node:{object_id}", KnowledgeNodeType.RESULT,
        f"Reviewed result {object_id}", provenance,
    )
    edge = KnowledgeEdge(
        f"edge-{object_id}", source.node_id, result.node_id,
        KnowledgeEdgeType.CONTAINS, True, provenance,
    )
    return ScientificKnowledgeGraph(
        graph_id, f"extraction-{graph_id}", (source, result), (edge,),
    ).finalized()


def proposition(graphs):
    evidence = bind_cross_study_evidence(graphs, (
        ("graph-1", "result-1", "supports"),
        ("graph-2", "result-2", "supports"),
    ))
    return CrossStudyProposition(
        "cross-study-proposition-1",
        "Positive attitudes do not by themselves establish sharing practice.",
        evidence, "discoverer@example", "Two independent reviewed results",
        "2026-07-19T00:01:00Z",
    ).finalized()


def test_cross_study_proposition_requires_independent_documents():
    graphs = {
        "graph-1": graph("graph-1", "result-1", "document-1"),
        "graph-2": graph("graph-2", "result-2", "document-1"),
    }
    item = proposition(graphs)
    assert not item.verify()


def test_cross_study_proposition_review_and_theory_bundle(tmp_path):
    graphs = {
        "graph-1": graph("graph-1", "result-1", "document-1"),
        "graph-2": graph("graph-2", "result-2", "document-2"),
    }
    item = proposition(graphs)
    assert item.verify()
    with pytest.raises(ValueError, match="differ"):
        item.review(
            decision="accepted", reviewer="discoverer@example",
            rationale="Self review", occurred_at="2026-07-19T00:02:00Z",
        )
    accepted = item.review(
        decision="accepted", reviewer="reviewer@example",
        rationale="Statement and independent evidence verified",
        occurred_at="2026-07-19T00:02:00Z",
    )
    assert (
        accepted.state is CrossStudyPropositionState.ACCEPTED
        and accepted.verify()
    )
    bundle = proposition_theory_bundle(
        accepted, created_at="2026-07-19T00:03:00Z",
    )
    assert bundle.verify() and len(bundle.proposals) == 1
    assert bundle.proposals[0].support_count == 2
    assert {
        item.stance for item in bundle.proposals[0].evidence
    } == {EvidenceStance.SUPPORTS}

    store = CrossStudyPropositionStore(tmp_path)
    store.save(item)
    store.save(accepted)
    assert store.load_all() == (accepted,)

    graph_store = KnowledgeGraphStore(tmp_path / "graphs")
    graph_store.save(graphs["graph-1"])
    graph_store.save(graphs["graph-2"])
    assert graph_store.load_all() == (
        graphs["graph-1"], graphs["graph-2"],
    )


def test_cross_study_proposition_rejects_non_result_evidence():
    first = graph("graph-1", "result-1", "document-1")
    second = graph("graph-2", "result-2", "document-2")
    variable = second.nodes[1]
    second = ScientificKnowledgeGraph(
        second.graph_id, second.extraction_id,
        (second.nodes[0], KnowledgeNode(
            variable.node_id, KnowledgeNodeType.VARIABLE,
            variable.label, variable.provenance,
        )),
        second.edges,
    ).finalized()
    evidence = bind_cross_study_evidence(
        {"graph-1": first, "graph-2": second},
        (
            ("graph-1", "result-1", "supports"),
            ("graph-2", "result-2", "supports"),
        ),
    )
    item = CrossStudyProposition(
        "cross-study-proposition-2", "Statement", evidence,
        "discoverer", "Rationale", "2026-07-19T00:00:00Z",
    ).finalized()
    assert not item.verify()


class Repository:
    def __init__(self, graphs):
        self.events = {
            node.provenance.object_id: node.provenance.review_event
            for graph_item in graphs.values()
            for node in graph_item.nodes if node.provenance is not None
        }
        self.artifacts = []

    def resolve_evidence_admissions(self, object_ids):
        from app.knowledge.extraction.models import EvidenceAdmission
        return tuple(EvidenceAdmission(
            object_id, ExtractionReviewState.ACCEPTED,
            self.events[object_id],
        ) for object_id in object_ids)

    def persist_artifact(self, **values):
        self.artifacts.append(values)


def test_pipeline_proposes_reviews_and_builds_cross_study_theory(tmp_path):
    graphs = {
        "graph-1": graph("graph-1", "result-1", "document-1"),
        "graph-2": graph("graph-2", "result-2", "document-2"),
    }
    repository = Repository(graphs)
    pipeline = KnowledgeTheoryPipeline(
        tmp_path, graphs, data_repository=repository,
    )
    item, snapshot = pipeline.propose_cross_study_proposition(
        statement="Positive attitudes do not establish sharing practice.",
        evidence_references=(
            ("graph-1", "result-1", "supports"),
            ("graph-2", "result-2", "supports"),
        ),
        proposed_by="discoverer@example", rationale="Independent results",
        proposed_at="2026-07-19T00:01:00Z",
    )
    assert item.verify() and snapshot.exists()
    with pytest.raises(ValueError, match="Accepted"):
        pipeline.build_cross_study_proposition_theory(
            item.proposition_id, generated_by="discoverer@example",
        )
    reviewed, _ = pipeline.review_cross_study_proposition(
        item.proposition_id, decision="accepted",
        reviewer="reviewer@example", rationale="Evidence linkage verified",
        occurred_at="2026-07-19T00:02:00Z",
    )
    bundle, bundle_snapshot = (
        pipeline.build_cross_study_proposition_theory(
            reviewed.proposition_id, generated_by="discoverer@example",
        )
    )
    assert bundle.verify() and bundle_snapshot.exists()
    assert bundle.proposals[0].support_count == 2
    assert repository.artifacts[0]["artifact_id"] == bundle.bundle_id
