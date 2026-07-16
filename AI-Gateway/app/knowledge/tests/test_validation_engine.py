from pathlib import Path
from dataclasses import asdict
from hashlib import sha256
import json

from app.knowledge.theory.models import EvidenceStance, TheoryBundle, TheoryEvidence, TheoryProposal
from app.knowledge.validation.engine import ValidationEngine
from app.knowledge.validation.models import RiskOfBias, ValidationStatus
from app.knowledge.validation.persistence import ValidationReportStore


def bundle(evidence=True, contradictions=0):
    items = (
        TheoryEvidence("e1", "g1", "o1", EvidenceStance.SUPPORTS, 0.8, "q1"),
        TheoryEvidence("e2", "g2", "o2", EvidenceStance.SUPPORTS, 0.8, "q2"),
    ) if evidence else ()
    proposal = TheoryProposal("t1", "Theory", items, len(items), contradictions)
    return TheoryBundle("bundle", ("g1", "g2"), "time", (proposal,), ()).finalized()


def test_validation_pass_is_transparent_and_reproducible(tmp_path: Path) -> None:
    report = ValidationEngine().validate(
        bundle(), assessed_at="2026-07-15T00:00:00Z",
        search_completed_at="2026-07-01T00:00:00Z", max_age_days=180,
        bias_by_theory={"t1": RiskOfBias.LOW}, reviewer="reviewer@example",
    )
    assert report.status is ValidationStatus.PASS
    assert report.assessments[0].confidence_score == 1.0
    assert report.assessments[0].evidence_edge_ids == ("e1", "e2")
    assert report.method.version == "1.0.0" and report.verify()
    assert report.theory_bundle_hash == bundle().content_hash
    assert report.schema_version == "1.1"
    assert ValidationReportStore(tmp_path).save(report).exists()


def test_validation_is_fail_safe_for_missing_bias_staleness_and_conflict() -> None:
    engine = ValidationEngine()
    incomplete = engine.validate(bundle(False), assessed_at="2026-07-15T00:00:00Z", search_completed_at="2026-07-01T00:00:00Z", max_age_days=180, bias_by_theory={}, reviewer="r")
    assert incomplete.status is ValidationStatus.INCOMPLETE
    stale = engine.validate(bundle(), assessed_at="2026-07-15T00:00:00Z", search_completed_at="2025-01-01T00:00:00Z", max_age_days=180, bias_by_theory={"t1": RiskOfBias.LOW}, reviewer="r")
    assert stale.status is ValidationStatus.STALE
    failed = engine.validate(bundle(contradictions=1), assessed_at="2026-07-15T00:00:00Z", search_completed_at="2026-07-01T00:00:00Z", max_age_days=180, bias_by_theory={"t1": RiskOfBias.LOW}, reviewer="r")
    assert failed.status is ValidationStatus.FAIL
    import pytest
    with pytest.raises(ValueError, match="cannot be after"):
        engine.validate(bundle(), assessed_at="2026-07-15T00:00:00Z", search_completed_at="2026-07-16T00:00:00Z", max_age_days=180, bias_by_theory={"t1": RiskOfBias.LOW}, reviewer="r")


def test_validation_store_restores_verified_reports(tmp_path: Path) -> None:
    report = ValidationEngine().validate(
        bundle(), assessed_at="2026-07-15T00:00:00Z",
        search_completed_at="2026-07-01T00:00:00Z", max_age_days=180,
        bias_by_theory={"t1": RiskOfBias.LOW}, reviewer="reviewer@example",
    )
    store = ValidationReportStore(tmp_path)
    store.save(report)

    assert store.load_all() == (report,)
    assert store.load_all()[0].verify()


def test_validation_store_migrates_verified_legacy_report_as_inactive(tmp_path: Path) -> None:
    report = ValidationEngine().validate(
        bundle(), assessed_at="2026-07-15T00:00:00Z",
        search_completed_at="2026-07-01T00:00:00Z", max_age_days=180,
        bias_by_theory={"t1": RiskOfBias.LOW}, reviewer="reviewer@example",
    )
    raw = asdict(report)
    raw.pop("theory_bundle_hash")
    raw.pop("triggered_by_decision_id")
    raw["schema_version"] = "1.0"
    raw["content_hash"] = ""
    raw["content_hash"] = sha256(json.dumps(
        raw, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()).hexdigest()
    directory = tmp_path / report.report_id
    directory.mkdir()
    (directory / f"v1.0-{raw['content_hash']}.json").write_text(
        json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    restored = ValidationReportStore(tmp_path).load_all()[0]
    assert restored.schema_version == "1.1"
    assert restored.theory_bundle_hash == ""
    assert restored.verify()
