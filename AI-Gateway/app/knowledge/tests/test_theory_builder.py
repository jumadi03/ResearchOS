from pathlib import Path
from dataclasses import asdict
from hashlib import sha256
import json

from app.knowledge.extraction.models import ExtractionReviewState
from app.knowledge.modeling.models import (
    GraphProvenance, KnowledgeEdge, KnowledgeEdgeType, KnowledgeNode,
    KnowledgeNodeType, ScientificKnowledgeGraph,
)
from app.knowledge.theory.builder import TheoryBuilder
from app.knowledge.theory.models import TheoryReviewState
from app.knowledge.theory.persistence import TheoryBundleStore
from app.knowledge.theory_pipeline import KnowledgeTheoryPipeline
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
    assert builder.alignment_candidates(decided) == ()
    pipeline = KnowledgeTheoryPipeline(tmp_path, {})
    pipeline.bundles[decided.bundle_id] = decided
    history = pipeline.alignment_history(decided.bundle_id)
    assert history["latest_validation"] is None
    assert history["items"][0]["decision"] == "keep_separate"
    assert set(history["items"][0]["theory_ids"]) == related_ids
    assert history["items"][0]["evidence_by_theory"][0][0]["object_id"]
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

    assert restored[0].schema_version == "1.2"
    assert restored[0].alignments == ()
    assert restored[0].alignment_decisions == ()
    assert restored[0].verify()
