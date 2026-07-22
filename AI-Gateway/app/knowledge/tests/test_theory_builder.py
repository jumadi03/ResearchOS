from pathlib import Path
from dataclasses import asdict, replace
from hashlib import sha256
import json

import pytest

from app.knowledge.extraction.models import (
    EpistemicClassification, EvidenceAdmission, EvidenceReviewAssessment,
    EvidenceReviewEvent, ExtractionReviewState,
)
from app.knowledge.modeling.models import (
    GraphProvenance, KnowledgeEdge, KnowledgeEdgeType, KnowledgeNode,
    KnowledgeNodeType, ScientificKnowledgeGraph,
)
from app.knowledge.theory.builder import TheoryBuilder
from app.knowledge.theory.models import (
    TheoryAlignmentDecisionEvent, TheoryAlignmentEvent, TheoryReviewState,
)
from app.knowledge.theory.persistence import TheoryBundleStore
from app.knowledge.theory.quality import AlignmentQualityEvaluator
from app.knowledge.theory_pipeline import KnowledgeTheoryPipeline
from app.knowledge.validation.engine import ValidationEngine
from app.knowledge.validation.models import RiskOfBias, ValidationStatus


def graph(identifier, conclusion, state=ExtractionReviewState.ACCEPTED, *, event=True):
    object_id = f"object-{identifier}"
    assessment = EvidenceReviewAssessment(
        True, True, True, .9, EpistemicClassification.OBSERVED_FACT,
        "a" * 64, "b" * 64,
    )
    review = (
        EvidenceReviewEvent(
            f"review-{identifier}", object_id, state, "reviewer@example",
            "Scientific evidence reviewed", "review-time",
            f"provenance-{identifier}", "pending", assessment,
            assessment.digest(),
        )
        if event and state is not None else None
    )
    provenance = GraphProvenance(
        "extraction", "document", object_id, 1, f"quote-{identifier}",
        0.7, state, review,
    )
    result = KnowledgeNode(f"result-{identifier}", KnowledgeNodeType.RESULT, "Result", provenance)
    theory = KnowledgeNode(f"conclusion-{identifier}", KnowledgeNodeType.CONCLUSION, conclusion, provenance)
    edge = KnowledgeEdge(f"edge-{identifier}", result.node_id, theory.node_id, KnowledgeEdgeType.SUPPORTS, True, provenance)
    return ScientificKnowledgeGraph(f"graph-{identifier}", f"extraction-{identifier}", (result, theory), (edge,)).finalized()


class AdmissionRepository:
    def __init__(self, admissions):
        self.admissions = {
            item.evidence_object_id: item for item in admissions
        }
        self.artifacts = []

    def resolve_evidence_admissions(self, evidence_object_ids):
        return tuple(
            self.admissions.get(
                object_id, EvidenceAdmission(object_id, None, None)
            )
            for object_id in evidence_object_ids
        )

    def persist_artifact(self, **values):
        self.artifacts.append(values)


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


def test_theory_builder_deduplicates_support_from_the_same_evidence_quote() -> None:
    source = graph("duplicate", "One reviewed conclusion")
    original = source.edges[0]
    duplicated = replace(original, edge_id="edge-duplicate-alias")
    repeated = replace(
        source, edges=(original, duplicated), content_hash="",
    ).finalized()

    bundle = TheoryBuilder().build((repeated,), created_at="time")

    assert len(bundle.proposals) == 1
    assert bundle.proposals[0].support_count == 1
    assert len(bundle.proposals[0].evidence) == 1


def test_cross_study_builder_rejects_single_source_and_distinct_claims() -> None:
    bundle = TheoryBuilder().build_cross_study((
        graph("one", "Institutions shape data sharing"),
        graph("two", "Researchers need repository guidance"),
    ), created_at="time")

    assert bundle.verify()
    assert bundle.proposals == ()


def test_cross_study_builder_requires_two_independent_evidence_objects() -> None:
    bundle = TheoryBuilder().build_cross_study((
        graph("one", "Institutional support improves data sharing"),
        graph("two", "Institutional support improves data sharing"),
    ), created_at="time")

    assert len(bundle.proposals) == 1
    proposal = bundle.proposals[0]
    assert proposal.support_count == 2
    assert len({item.graph_id for item in proposal.evidence}) == 2
    assert len({item.object_id for item in proposal.evidence}) == 2
    assert proposal.statement.startswith(
        "Independent evidence across studies supports the proposition that "
    )


def test_cross_study_builder_can_use_explicitly_supported_results() -> None:
    first = graph("result-one", "A conclusion")
    second = graph("result-two", "Another conclusion")
    first = replace(
        first,
        nodes=(
            replace(first.nodes[0], label="Repository guidance improves data sharing"),
            first.nodes[1],
        ),
        content_hash="",
    ).finalized()
    second = replace(
        second,
        nodes=(
            replace(second.nodes[0], label="Repository guidance improves data sharing"),
            second.nodes[1],
        ),
        content_hash="",
    ).finalized()

    bundle = TheoryBuilder().build_cross_study(
        (first, second), created_at="time",
    )

    assert len(bundle.proposals) == 1
    proposal = bundle.proposals[0]
    assert "repository guidance improves data sharing" in proposal.statement
    assert {item.object_id for item in proposal.evidence} == {
        "object-result-one", "object-result-two",
    }


def test_cross_study_builder_ignores_unrelated_limitation_without_support() -> None:
    source = graph("limited", "A supported conclusion")
    provenance = source.nodes[0].provenance
    limitation = KnowledgeNode(
        "limitation-limited", KnowledgeNodeType.LIMITATION,
        "Small samples constrain generalization", provenance,
    )
    unsupported = replace(
        source, nodes=source.nodes + (limitation,), content_hash="",
    ).finalized()

    bundle = TheoryBuilder().build_cross_study(
        (unsupported, graph("other", "Another conclusion")),
        created_at="time",
    )

    assert bundle.proposals == ()


def test_theory_builder_rejects_provisional_rejected_and_mixed_graphs() -> None:
    import pytest
    builder = TheoryBuilder()
    for state, reason in (
        (ExtractionReviewState.PROVISIONAL, "not accepted"),
        (ExtractionReviewState.REJECTED, "contains rejected evidence"),
    ):
        with pytest.raises(ValueError, match=reason):
            builder.build((
                graph("unsafe", "Unsafe conclusion", state),
            ), created_at="time")
    with pytest.raises(ValueError, match="contains rejected evidence"):
        builder.build((
            graph("accepted", "Accepted conclusion"),
            graph(
                "rejected", "Rejected conclusion",
                ExtractionReviewState.REJECTED,
            ),
        ), created_at="time")


def test_theory_builder_rejects_missing_status_and_review_provenance() -> None:
    import pytest
    builder = TheoryBuilder()
    with pytest.raises(ValueError, match="status is missing"):
        builder.build((
            graph("missing-status", "Unsafe conclusion", None, event=False),
        ), created_at="time")
    with pytest.raises(ValueError, match="provenance is incomplete"):
        builder.build((
            graph("missing-event", "Unsafe conclusion", event=False),
        ), created_at="time")


def test_theory_pipeline_revalidates_live_evidence_after_graph_snapshot(
    tmp_path: Path,
) -> None:
    import pytest
    safe_graph = graph("live", "Reviewed evidence supports a theory")
    event = next(
        node.provenance.review_event for node in safe_graph.nodes
        if node.provenance is not None
    )
    repository = AdmissionRepository((
        EvidenceAdmission(
            event.evidence_object_id, ExtractionReviewState.ACCEPTED, event,
        ),
    ))
    pipeline = KnowledgeTheoryPipeline(
        tmp_path, {safe_graph.graph_id: safe_graph},
        data_repository=repository,
    )
    bundle, _ = pipeline.build_theories(
        (safe_graph.graph_id,), generated_by="researcher@example",
    )
    assert bundle.verify()
    rejected = EvidenceReviewEvent(
        "review-rejected", event.evidence_object_id,
        ExtractionReviewState.REJECTED, "reviewer@example",
        "Evidence was revoked after graph admission", "later",
        "provenance-rejected", "accepted",
    )
    repository.admissions[event.evidence_object_id] = EvidenceAdmission(
        event.evidence_object_id, ExtractionReviewState.REJECTED, rejected,
    )
    with pytest.raises(ValueError, match="contains rejected evidence"):
        pipeline.build_theories(
            (safe_graph.graph_id,), generated_by="researcher@example",
        )


def test_theory_pipeline_cannot_bypass_canonical_admission_authority(
    tmp_path: Path,
) -> None:
    import pytest
    safe_graph = graph("no-repository", "Reviewed evidence supports theory")
    pipeline = KnowledgeTheoryPipeline(
        tmp_path, {safe_graph.graph_id: safe_graph},
    )

    with pytest.raises(ValueError, match="Canonical repository is required"):
        pipeline.build_theories(
            (safe_graph.graph_id,), generated_by="researcher@example",
        )


def test_stale_evidence_dependency_blocks_revalidation_and_publication_readiness(
    tmp_path: Path,
) -> None:
    safe_graph = graph("dependency", "Reviewed evidence supports theory")
    event = safe_graph.nodes[0].provenance.review_event
    repository = AdmissionRepository((
        EvidenceAdmission(
            event.evidence_object_id, ExtractionReviewState.ACCEPTED, event,
        ),
    ))
    pipeline = KnowledgeTheoryPipeline(
        tmp_path, {safe_graph.graph_id: safe_graph},
        data_repository=repository,
    )
    bundle, _ = pipeline.build_theories(
        (safe_graph.graph_id,), generated_by="researcher@example",
    )
    proposal = bundle.proposals[0]
    bundle, _ = pipeline.review_theory(
        bundle.bundle_id, theory_id=proposal.theory_id, decision="accepted",
        reviewer="reviewer@example", rationale="Evidence supports the claim",
        occurred_at="2026-07-18T00:00:00Z",
    )
    report, _ = pipeline.validate_theories(
        bundle.bundle_id, assessed_at="2026-07-18T00:00:00Z",
        search_completed_at="2026-07-18T00:00:00Z", max_age_days=180,
        risk_of_bias_by_theory={proposal.theory_id: "low"},
        reviewer="reviewer@example", triggered_by_decision_id=None,
    )
    repository.admissions[event.evidence_object_id] = EvidenceAdmission(
        event.evidence_object_id, ExtractionReviewState.REJECTED,
        replace(event, decision=ExtractionReviewState.REJECTED),
    )

    impact = pipeline.dependency_impact(bundle.bundle_id)
    assert impact.current is False
    assert impact.impacted_evidence_ids == (event.evidence_object_id,)
    assert impact.impacted_graph_ids == (safe_graph.graph_id,)
    assert impact.graph_states == ((safe_graph.graph_id, "superseded"),)
    assert impact.evidence_states == (
        (event.evidence_object_id, "rejected"),
    )
    assert pipeline.validation_history(bundle.bundle_id)[0][
        "active_for_current_bundle"
    ] is False
    readiness = pipeline.publication_readiness(
        bundle.bundle_id, kind="literature_review",
        validation_report_id=report.report_id,
    )
    assert readiness["ready"] is False
    assert readiness["dependency_impact"]["current"] is False
    assert next(
        item for item in readiness["checks"]
        if item["key"] == "current_dependencies"
    )["passed"] is False
    lifecycle = pipeline.graph_lifecycle(safe_graph.graph_id)
    assert lifecycle.state == "superseded"
    assert lifecycle.current is False
    assert lifecycle.impacted_evidence_ids == (event.evidence_object_id,)
    with pytest.raises(ValueError, match="stale or inadmissible"):
        pipeline.validate_theories(
            bundle.bundle_id, assessed_at="2026-07-19T00:00:00Z",
            search_completed_at="2026-07-19T00:00:00Z", max_age_days=180,
            risk_of_bias_by_theory={proposal.theory_id: "low"},
            reviewer="reviewer@example", triggered_by_decision_id=None,
        )


def test_rejected_semantic_relation_supersedes_graph_and_theory_dependencies(
    tmp_path: Path,
) -> None:
    safe_graph = graph(
        "relation-dependency",
        "Reviewed semantic relations support reproducible synthesis",
    )
    event = safe_graph.nodes[0].provenance.review_event
    repository = AdmissionRepository((
        EvidenceAdmission(
            event.evidence_object_id, ExtractionReviewState.ACCEPTED, event,
        ),
    ))
    relation_state = {
        safe_graph.graph_id: (
            ("semantic-relation-reviewed", "accepted"),
        ),
    }
    pipeline = KnowledgeTheoryPipeline(
        tmp_path, {safe_graph.graph_id: safe_graph},
        data_repository=repository,
        semantic_relation_resolver=lambda graph_id: relation_state.get(
            graph_id, (),
        ),
    )
    bundle, _ = pipeline.build_theories(
        (safe_graph.graph_id,), generated_by="researcher@example",
    )
    proposal = bundle.proposals[0]
    bundle, _ = pipeline.review_theory(
        bundle.bundle_id, theory_id=proposal.theory_id, decision="accepted",
        reviewer="reviewer@example", rationale="Theory relation reviewed",
        occurred_at="2026-07-19T03:00:00Z",
    )
    report, _ = pipeline.validate_theories(
        bundle.bundle_id, assessed_at="2026-07-19T03:01:00Z",
        search_completed_at="2026-07-19T03:01:00Z", max_age_days=180,
        risk_of_bias_by_theory={proposal.theory_id: "low"},
        reviewer="reviewer@example", triggered_by_decision_id=None,
    )
    assert pipeline.graph_lifecycle(safe_graph.graph_id).current is True
    relation_state[safe_graph.graph_id] = (
        ("semantic-relation-reviewed", "rejected"),
    )

    lifecycle = pipeline.graph_lifecycle(safe_graph.graph_id)
    assert lifecycle.state == "superseded"
    assert lifecycle.impacted_semantic_relation_ids == (
        "semantic-relation-reviewed",
    )
    impact = pipeline.dependency_impact(bundle.bundle_id)
    assert impact.current is False
    assert impact.impacted_graph_ids == (safe_graph.graph_id,)
    assert impact.impacted_semantic_relation_ids == (
        "semantic-relation-reviewed",
    )
    assert pipeline.validation_history(bundle.bundle_id)[0][
        "active_for_current_bundle"
    ] is False
    readiness = pipeline.publication_readiness(
        bundle.bundle_id, kind="literature_review",
        validation_report_id=report.report_id,
    )
    assert readiness["ready"] is False
    with pytest.raises(ValueError, match="current graph dependencies"):
        pipeline.build_theories(
            (safe_graph.graph_id,), generated_by="researcher@example",
        )
    with pytest.raises(ValueError, match="stale or inadmissible"):
        pipeline.validate_theories(
            bundle.bundle_id, assessed_at="2026-07-19T03:02:00Z",
            search_completed_at="2026-07-19T03:02:00Z", max_age_days=180,
            risk_of_bias_by_theory={proposal.theory_id: "low"},
            reviewer="reviewer@example", triggered_by_decision_id=None,
        )


def test_publication_relationships_project_correction_and_retraction(
    tmp_path: Path,
) -> None:
    pipeline = KnowledgeTheoryPipeline(tmp_path, {})
    pipeline.publication_packages = {"old": object(), "new": object()}
    correction, snapshot = pipeline.relate_publication(
        "new", relation_type="corrects", target_publication_id="old",
        actor_id="publisher@example", rationale="Corrected analysis and citations",
        occurred_at="2026-07-19T00:00:00Z",
    )
    assert correction.verify() and snapshot.exists()
    assert pipeline.publication_lifecycle("old")["state"] == "corrected"
    assert pipeline.publication_lifecycle("old")[
        "replacement_publication_id"
    ] == "new"
    assert pipeline.publication_lifecycle("new")["state"] == "current"

    retraction, _ = pipeline.relate_publication(
        "new", relation_type="retracts", target_publication_id=None,
        actor_id="publisher@example", rationale="Material validity failure confirmed",
        occurred_at="2026-07-20T00:00:00Z",
    )
    assert retraction.verify()
    assert pipeline.publication_lifecycle("new")["state"] == "retracted"
    with pytest.raises(ValueError, match="must not specify"):
        pipeline.relate_publication(
            "new", relation_type="retracts", target_publication_id="old",
            actor_id="publisher@example", rationale="Invalid retraction target",
            occurred_at="2026-07-21T00:00:00Z",
        )
    with pytest.raises(ValueError, match="cannot correct or supersede itself"):
        pipeline.relate_publication(
            "new", relation_type="supersedes", target_publication_id="new",
            actor_id="publisher@example", rationale="Invalid self relationship",
            occurred_at="2026-07-21T00:00:00Z",
        )


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


def test_reviewer_alignment_merges_accepted_theories_and_records_audit_event(tmp_path: Path) -> None:
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
    pipeline = KnowledgeTheoryPipeline(tmp_path, {})
    pipeline.bundles[aligned.bundle_id] = aligned
    history = pipeline.alignment_history(aligned.bundle_id)
    assert history["items"][0]["decision"] == "aligned"
    assert history["items"][0]["resulting_theory_id"] == proposal.theory_id
    assert len(history["items"][0]["evidence_by_theory"][0]) == 2


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


def test_alignment_candidates_are_advisory_ranked_and_accepted_only(tmp_path: Path) -> None:
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
    assert candidates[0].lexical_overlap_score == 0.3643
    assert candidates[0].method == "explainable-lexical-v2"
    assert candidates[0].shared_terms == ("open", "practices", "reproducibility")
    assert candidates[0].shared_bigrams == ()
    assert candidates[0].score_components == (
        ("content_term_jaccard", 0.4286),
        ("content_bigram_jaccard", 0.0),
    )
    assert "score must be at least 0.20" in candidates[0].explanation
    assert candidates[0].advisory is True
    assert candidates[0].evidence_by_theory[0][0].object_id
    assert candidates[0].evidence_by_theory[0][0].document_id == "document"
    assert candidates[0].evidence_by_theory[0][0].page == 1

    decided = builder.keep_separate(
        bundle, theory_ids=candidates[0].theory_ids, reviewer="reviewer@example",
        rationale="The populations and outcome definitions are materially different",
        occurred_at="decision-time",
    )
    assert decided.alignment_decisions[0].decision == "keep_separate"
    assert decided.alignment_decisions[0].reviewer == "reviewer@example"
    assert decided.alignment_decisions[0].candidate_method == "explainable-lexical-v2"
    assert decided.alignment_decisions[0].candidate_score == 0.3643
    assert decided.alignment_decisions[0].candidate_threshold == 0.2
    assert decided.alignment_decisions[0].candidate_shared_terms == (
        "open", "practices", "reproducibility",
    )
    assert builder.alignment_candidates(decided) == ()
    pipeline = KnowledgeTheoryPipeline(tmp_path, {})
    pipeline.bundles[decided.bundle_id] = decided
    history = pipeline.alignment_history(decided.bundle_id)
    assert history["latest_validation"] is None
    assert history["items"][0]["decision"] == "keep_separate"
    assert set(history["items"][0]["theory_ids"]) == related_ids
    assert history["items"][0]["evidence_by_theory"][0][0]["object_id"]
    assert history["items"][0]["candidate_score"] == 0.3643
    quality = pipeline.alignment_quality(decided.bundle_id)
    assert quality["simulation_only"] is True
    assert quality["outcomes"]["reviewed"] == 1
    assert quality["outcomes"]["keep_separate"] == 1
    assert quality["outcomes"]["pending"] == 0
    assert quality["benchmark"]["version"] == "1.0.0"
    report, _ = pipeline.validate_theories(
        decided.bundle_id, assessed_at="2026-07-15T00:00:00Z",
        search_completed_at="2026-07-01T00:00:00Z", max_age_days=180,
        risk_of_bias_by_theory={
            item.theory_id: "low" for item in decided.proposals
        }, reviewer="reviewer@example",
        triggered_by_decision_id=decided.alignment_decisions[0].decision_id,
    )
    assert report.triggered_by_decision_id == decided.alignment_decisions[0].decision_id
    assert pipeline.alignment_history(decided.bundle_id)["validation_state"]["active"]
    third = next(item for item in decided.proposals if item.theory_id not in related_ids)
    pipeline.review_theory(
        decided.bundle_id, theory_id=third.theory_id, decision="rejected",
        reviewer="reviewer@example", rationale="Unrelated scope",
        occurred_at="later-review",
    )
    stale_history = pipeline.alignment_history(decided.bundle_id)
    assert stale_history["validation_state"] == {
        "active": False,
        "reason": "theory_bundle_changed_after_reviewer_decision",
    }
    assert pipeline.validation_history(decided.bundle_id)[0][
        "active_for_current_bundle"
    ] is False


def test_alignment_candidates_exclude_stopword_and_opposing_polarity_noise() -> None:
    builder = TheoryBuilder()
    bundle = builder.build((
        graph("positive", "Open governance improves reproducibility outcomes"),
        graph("negative", "Open governance does not improve reproducibility outcomes"),
        graph("generic-one", "Evidence in the system"),
        graph("generic-two", "Policy in the system"),
    ), created_at="time")
    for proposal in bundle.proposals:
        bundle = builder.review(
            bundle, theory_id=proposal.theory_id,
            decision=TheoryReviewState.ACCEPTED, reviewer="reviewer@example",
            rationale="Candidate benchmark review", occurred_at=proposal.theory_id,
        )

    assert builder.alignment_candidates(bundle) == ()


def test_alignment_quality_benchmark_is_versioned_and_threshold_is_simulated() -> None:
    evaluator = AlignmentQualityEvaluator()
    baseline = evaluator.benchmark(threshold=0.2)
    stricter = evaluator.benchmark(threshold=0.5)

    assert baseline["method"] == "explainable-lexical-v2"
    assert baseline["version"] == "1.0.0"
    assert len(baseline["cases"]) == 8
    assert baseline["metrics"]["precision"] >= 0.75
    assert baseline["metrics"]["recall"] >= 1.0
    assert baseline["metrics"]["recall"] >= stricter["metrics"]["recall"]
    with pytest.raises(ValueError, match="between 0 and 1"):
        evaluator.benchmark(threshold=1.1)


def test_calibration_requires_evidence_separate_approval_and_supports_rollback(
    tmp_path: Path,
) -> None:
    pipeline = KnowledgeTheoryPipeline(tmp_path, {})
    bundle = TheoryBuilder().build(
        (graph("calibration", "Calibration evidence"),), created_at="time"
    )
    decision_events = tuple(
        TheoryAlignmentDecisionEvent(
            f"decision-{index}", (f"left-{index}", f"right-{index}"),
            "keep_separate", "reviewer", "Scopes differ", f"time-{index}",
            candidate_id=f"candidate-{index}",
            candidate_method="explainable-lexical-v2",
            candidate_score=0.21 + index / 1000,
            candidate_threshold=0.2,
            candidate_shared_terms=("shared", "terms"),
        )
        for index in range(15)
    )
    alignment_events = tuple(
        TheoryAlignmentEvent(
            f"alignment-{index}", (f"a-left-{index}", f"a-right-{index}"),
            f"result-{index}", "Aligned statement", "reviewer",
            "Equivalent scopes", f"alignment-time-{index}",
            candidate_id=f"aligned-candidate-{index}",
            candidate_method="explainable-lexical-v2",
            candidate_score=0.4 + index / 1000,
            candidate_threshold=0.2,
            candidate_shared_terms=("shared", "terms"),
        )
        for index in range(15)
    )
    bundle = replace(
        bundle, alignments=alignment_events,
        alignment_decisions=decision_events, content_hash="",
    ).finalized()
    pipeline.bundles[bundle.bundle_id] = bundle

    summary = pipeline.alignment_calibration_summary()
    assert summary["eligible_to_propose"] is True
    proposal, _ = pipeline.propose_alignment_calibration(
        threshold=0.3, proposer="reviewer-one",
        rationale="Observed labels support this conservative threshold",
        proposed_at="2026-07-16T06:00:00Z",
    )
    assert proposal.status == "pending"
    with pytest.raises(ValueError, match="different reviewer"):
        pipeline.approve_alignment_calibration(
            proposal.calibration_id, approver="reviewer-one",
            approved_at="2026-07-16T06:01:00Z",
        )
    approved, _ = pipeline.approve_alignment_calibration(
        proposal.calibration_id, approver="reviewer-two",
        approved_at="2026-07-16T06:02:00Z",
    )
    assert approved.status == "approved"
    assert pipeline.theory_builder.candidate_threshold == 0.3
    restored = KnowledgeTheoryPipeline(tmp_path, {})
    assert restored.theory_builder.candidate_threshold == 0.3
    rollback, _ = restored.rollback_alignment_calibration(
        approver="reviewer-three", rationale="Rollback after monitored regression",
        occurred_at="2026-07-16T06:03:00Z",
    )
    assert rollback.proposed_threshold == 0.2
    assert restored.theory_builder.candidate_threshold == 0.2


def test_stratified_calibration_queue_is_blind_independent_and_adjudicated(
    tmp_path: Path,
) -> None:
    builder = TheoryBuilder()
    bundle = builder.build((
        graph("blind-one", "Open science practices improve reproducibility"),
        graph("blind-two", "Open research practices support reproducibility"),
    ), created_at="time")
    for proposal in bundle.proposals:
        bundle = builder.review(
            bundle, theory_id=proposal.theory_id,
            decision=TheoryReviewState.ACCEPTED, reviewer="source-reviewer",
            rationale="Eligible for calibration sampling",
            occurred_at=proposal.theory_id,
        )
    pipeline = KnowledgeTheoryPipeline(tmp_path, {})
    pipeline.bundles[bundle.bundle_id] = bundle

    refreshed = pipeline.refresh_calibration_queue(
        created_at="2026-07-16T07:00:00Z"
    )
    assert refreshed["created"] == 1
    assert refreshed["queue"]["by_stratum"][1]["count"] == 1
    first = pipeline.next_calibration_case(reviewer="reviewer-one")
    assert first is not None
    assert "score" not in first
    assert "method" not in first
    assert "stratum" not in first
    reviewed, _ = pipeline.review_calibration_case(
        first["case_id"], reviewer="reviewer-one", decision="aligned",
        rationale="Constructs and outcomes appear equivalent",
        reviewed_at="2026-07-16T07:01:00Z",
    )
    assert reviewed["status"] == "awaiting_second_review"
    assert pipeline.next_calibration_case(reviewer="reviewer-one") is None
    second = pipeline.next_calibration_case(reviewer="reviewer-two")
    assert second["case_id"] == first["case_id"]
    disputed, _ = pipeline.review_calibration_case(
        first["case_id"], reviewer="reviewer-two",
        decision="keep_separate",
        rationale="Operational definitions remain materially different",
        reviewed_at="2026-07-16T07:02:00Z",
    )
    assert disputed["status"] == "disputed"
    assert pipeline.calibration_disputes(reviewer="reviewer-one") == ()
    disputes = pipeline.calibration_disputes(reviewer="reviewer-three")
    assert disputes[0]["case_id"] == first["case_id"]
    final, _ = pipeline.adjudicate_calibration_case(
        first["case_id"], reviewer="reviewer-three",
        decision="keep_separate",
        rationale="Differences outweigh surface lexical similarity",
        reviewed_at="2026-07-16T07:03:00Z",
    )
    assert final["status"] == "finalized"
    assert final["final_outcome"] == "keep_separate"
    summary = pipeline.alignment_calibration_summary()
    assert summary["queue"]["finalized"] == 1
    assert summary["queue"]["agreement_rate"] == 0.0
    restored = KnowledgeTheoryPipeline(tmp_path, {})
    assert restored.alignment_calibration_summary()["queue"]["finalized"] == 1


def test_theory_translation_preserves_source_and_requires_current_hash(
    tmp_path: Path,
) -> None:
    pipeline = KnowledgeTheoryPipeline(tmp_path, {})
    bundle = TheoryBuilder().build((
        graph("translation", "Open science improves reproducibility"),
    ), created_at="time")
    pipeline.bundles[bundle.bundle_id] = bundle
    theory_id = bundle.proposals[0].theory_id

    translated, _ = pipeline.record_theory_translation(
        bundle.bundle_id, theory_id,
        translated_statement="Sains terbuka meningkatkan reprodusibilitas",
        provider="human", model="reviewer-translation-v1",
        generated_by="translator@example",
        generated_at="2026-07-16T08:00:00Z",
    )
    assert translated.status == "advisory"
    assert translated.source_statement == bundle.proposals[0].statement
    assert translated.source_hash
    listed = pipeline.theory_translations(bundle.bundle_id)
    assert listed[0]["translated_statement"].startswith("Sains terbuka")
    reviewed, _ = pipeline.review_theory_translation(
        translated.translation_id, reviewer="reviewer@example",
        rationale="Terminology checked against the source statement",
        corrected_translation="Sains terbuka meningkatkan keterulangan hasil",
        reviewed_at="2026-07-16T08:01:00Z",
    )
    assert reviewed.status == "reviewed"
    assert reviewed.translated_statement.endswith("keterulangan hasil")
    restored = KnowledgeTheoryPipeline(tmp_path, {})
    restored.bundles[bundle.bundle_id] = bundle
    assert restored.theory_translations(bundle.bundle_id)[0]["status"] == "reviewed"
    changed = replace(
        bundle,
        proposals=(replace(
            bundle.proposals[0], statement="Open science may improve reproducibility",
        ),),
        content_hash="",
    ).finalized()
    restored.bundles[bundle.bundle_id] = changed
    assert restored.theory_translations(bundle.bundle_id) == ()
    with pytest.raises(ValueError, match="source has changed"):
        restored.review_theory_translation(
            translated.translation_id, reviewer="another-reviewer",
            rationale="Attempted review against changed source",
            reviewed_at="2026-07-16T08:02:00Z",
        )


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


def test_theory_store_restores_latest_verified_snapshot(tmp_path: Path) -> None:
    builder = TheoryBuilder()
    bundle = builder.build((graph("one", "Governance matters"),), created_at="time")
    store = TheoryBundleStore(tmp_path)
    store.save(bundle)
    reviewed = builder.review(
        bundle, theory_id=bundle.proposals[0].theory_id,
        decision=TheoryReviewState.ACCEPTED, reviewer="reviewer@example",
        rationale="Evidence reviewed", occurred_at="later",
    )
    store.save(reviewed)

    restored = store.load_all()

    assert restored == (reviewed,)
    assert restored[0].verify()


def test_theory_store_verifies_and_migrates_legacy_snapshot(tmp_path: Path) -> None:
    bundle = TheoryBuilder().build(
        (graph("legacy", "Governance matters"),), created_at="time"
    )
    raw = asdict(bundle)
    raw.pop("alignments")
    raw.pop("alignment_decisions")
    for proposal in raw["proposals"]:
        for evidence in proposal["evidence"]:
            evidence.pop("document_id")
            evidence.pop("page")
    raw["schema_version"] = "1.0"
    raw["content_hash"] = ""
    raw["content_hash"] = sha256(json.dumps(
        raw, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()).hexdigest()
    directory = tmp_path / bundle.bundle_id
    directory.mkdir(parents=True)
    (directory / f"v1.0-{raw['content_hash']}.json").write_text(
        json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )

    restored = TheoryBundleStore(tmp_path).load_all()

    assert restored[0].schema_version == "1.3"
    assert restored[0].alignments == ()
    assert restored[0].alignment_decisions == ()
    assert restored[0].verify()
