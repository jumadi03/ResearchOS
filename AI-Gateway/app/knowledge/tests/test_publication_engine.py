from pathlib import Path
from dataclasses import replace

from app.knowledge.publication.engine import PublicationEngine
from app.knowledge.publication.models import PublicationKind
from app.knowledge.publication.persistence import PublicationStore
from app.knowledge.theory.models import EvidenceStance, TheoryBundle, TheoryEvidence, TheoryProposal
from app.knowledge.validation.engine import ValidationEngine
from app.knowledge.validation.models import RiskOfBias


def inputs(graphs=2):
    evidence = tuple(TheoryEvidence(f"e{i}", f"g{i}", f"o{i}", EvidenceStance.SUPPORTS, 0.8, f"q{i}") for i in range(graphs))
    bundle = TheoryBundle("bundle", tuple(f"g{i}" for i in range(graphs)), "time", (TheoryProposal("t1", "Governance improves performance", evidence, len(evidence), 0),), ()).finalized()
    report = ValidationEngine().validate(bundle, assessed_at="2026-07-15T00:00:00Z", search_completed_at="2026-07-01T00:00:00Z", max_age_days=180, bias_by_theory={"t1": RiskOfBias.LOW}, reviewer="reviewer")
    return bundle, report


def test_publication_is_evidence_linked_reproducible_and_immutable(tmp_path: Path) -> None:
    bundle, report = inputs()
    package = PublicationEngine().publish(bundle, report, kind=PublicationKind.SYSTEMATIC_REVIEW_SUPPORT, generated_at="time", generated_by="publisher@example")
    assert package.verify()
    assert "[evidence:e0]" in package.markdown
    assert package.manifest.citation_verification.verified
    store = PublicationStore(tmp_path)
    location = store.save(package)
    assert store.save(package) == location
    assert (location / "publication.md").exists() and (location / "manifest.json").exists()


def test_systematic_review_gate_rejects_non_pass_validation() -> None:
    import pytest
    bundle, report = inputs(1)
    with pytest.raises(ValueError, match="requires PASS"):
        PublicationEngine().publish(bundle, report, kind=PublicationKind.SYSTEMATIC_REVIEW_SUPPORT, generated_at="time", generated_by="publisher")


def test_publication_rejects_validation_for_stale_bundle_content() -> None:
    import pytest
    bundle, report = inputs()
    stale = replace(report, theory_bundle_hash="older-content", content_hash="").finalized()
    with pytest.raises(ValueError, match="stale"):
        PublicationEngine().publish(
            bundle, stale, kind=PublicationKind.LITERATURE_REVIEW,
            generated_at="time", generated_by="publisher",
        )


def test_citation_verifier_detects_unresolved_reference() -> None:
    result = PublicationEngine.verify_citations("Claim [evidence:missing]", ("known",))
    assert not result.verified and result.unresolved_citations == ("missing",)
