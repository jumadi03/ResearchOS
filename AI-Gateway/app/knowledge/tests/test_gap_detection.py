from pathlib import Path

from app.knowledge.gaps.detector import ResearchGapDetector
from app.knowledge.gaps.models import GapType
from app.knowledge.gaps.persistence import GapAnalysisStore
from app.knowledge.theory.models import (
    CompetingTheory, EvidenceStance, TheoryBundle, TheoryEvidence, TheoryProposal,
)


def bundle():
    one = TheoryProposal("t1", "Governance improves performance", (TheoryEvidence("e1", "g1", "o1", EvidenceStance.SUPPORTS, 0.7, "q1"),), 1, 0)
    two = TheoryProposal("t2", "Governance does not improve performance", (), 0, 0)
    return TheoryBundle(
        "bundle", ("g1", "g2"), "time", (one, two),
        (CompetingTheory("t1", "t2", "Opposing polarity"),),
    ).finalized()


def test_gap_detector_is_explainable_traceable_and_generates_advisory_hypotheses(tmp_path: Path) -> None:
    analysis = ResearchGapDetector().analyze(bundle(), created_at="later")
    assert analysis.verify()
    assert {gap.gap_type for gap in analysis.gaps} == {
        GapType.EVIDENCE_ABSENCE, GapType.LIMITED_COVERAGE,
        GapType.UNRESOLVED_CONTRADICTION,
    }
    coverage = next(gap for gap in analysis.gaps if gap.gap_type is GapType.LIMITED_COVERAGE)
    assert coverage.evidence_edge_ids == ("e1",)
    assert all(item.advisory and item.gap_id for item in analysis.hypotheses)
    assert GapAnalysisStore(tmp_path).save(analysis).exists()


def test_gap_detector_rejects_tampered_bundle() -> None:
    import pytest
    value = bundle()
    object.__setattr__(value, "content_hash", "tampered")
    with pytest.raises(ValueError, match="verified"):
        ResearchGapDetector().analyze(value, created_at="later")
