from dataclasses import replace

import pytest

from app.knowledge.inspection.engine import SourceInspectionEngine
from app.knowledge.models import DiscoveryContract, LiteratureRecord, SourceRecord
from app.knowledge.screening.engine import ScientificScreeningEngine
from app.knowledge.screening.models import ScreeningStatus
from app.knowledge.screening.persistence import ScreeningDecisionStore
from app.knowledge.tests.test_evidence_extraction import document


def contract():
    return DiscoveryContract(
        "contract", "project", "question", "plan", "governance research",
        ("A2",), ("Relevant scientific studies",),
        ("Non-scientific commentary",), ("en",), ("article",),
        ("claim",), 1, 10, "open", "human ratification required",
        ("budget exhausted",), 2020, 2026,
    )


def record(*, year=2025, work_type="article", with_source=True):
    source = SourceRecord(
        "openalex", "W1", "now", "response-hash", "source-openalex",
        "family", "query", 1, 1, "https://example.test/api", None, {},
    )
    return LiteratureRecord(
        "record", "Scientific governance", ("Author",), year, None,
        "Abstract", "Journal", work_type, (source,) if with_source else (),
    )


def test_screening_is_deterministic_provenance_bound_and_immutable(tmp_path):
    source, _, content = document(tmp_path)
    inspection = SourceInspectionEngine().inspect(source, content, inspected_at="now")
    engine = ScientificScreeningEngine()
    first = engine.screen(record(), source, inspection, contract(), decided_at="later")
    second = engine.screen(record(), source, inspection, contract(), decided_at="later")
    assert first == second
    assert first.status is ScreeningStatus.ELIGIBLE
    assert first.verify()
    store = ScreeningDecisionStore(tmp_path / "screenings")
    path = store.save(first)
    assert store.load(path) == first


def test_scope_rejection_and_quality_review_have_explicit_reasons(tmp_path):
    source, _, content = document(tmp_path)
    inspection = SourceInspectionEngine().inspect(source, content, inspected_at="now")
    engine = ScientificScreeningEngine()
    rejected = engine.screen(
        record(year=2010), source, inspection, contract(), decided_at="later"
    )
    assert rejected.status is ScreeningStatus.INELIGIBLE
    assert "SCOPE_MISMATCH" in {item.code for item in rejected.reasons}
    review = engine.screen(
        record(with_source=False), source, inspection, contract(), decided_at="later"
    )
    assert review.status is ScreeningStatus.HUMAN_REVIEW_REQUIRED
    assert "REVIEW_QUALITY_METADATA_INCOMPLETE" in {
        item.code for item in review.reasons
    }
    assert rejected.decision_id != review.decision_id


def test_changed_screening_outcome_gets_a_new_immutable_identity(tmp_path):
    source, _, content = document(tmp_path)
    inspection = SourceInspectionEngine().inspect(source, content, inspected_at="now")
    engine = ScientificScreeningEngine()

    incomplete = engine.screen(
        record(with_source=False), source, inspection, contract(), decided_at="later"
    )
    enriched = engine.screen(
        record(with_source=True), source, inspection, contract(), decided_at="later"
    )

    assert incomplete.status is ScreeningStatus.HUMAN_REVIEW_REQUIRED
    assert enriched.status is ScreeningStatus.ELIGIBLE
    assert incomplete.decision_id != enriched.decision_id


def test_provider_article_aliases_match_canonical_journal_article_scope(tmp_path):
    source, _, content = document(tmp_path)
    inspection = SourceInspectionEngine().inspect(source, content, inspected_at="now")
    governed_contract = replace(
        contract(), document_types=("journal_article",)
    )

    for provider_type in ("article", "journal-article", "JournalArticle"):
        decision = ScientificScreeningEngine().screen(
            record(work_type=provider_type), source, inspection,
            governed_contract, decided_at="later",
        )
        assert decision.status is ScreeningStatus.ELIGIBLE


def test_stale_tampered_and_noneligible_decisions_fail_closed(tmp_path):
    source, _, content = document(tmp_path)
    inspection = SourceInspectionEngine().inspect(source, content, inspected_at="now")
    decision = ScientificScreeningEngine().screen(
        record(), source, inspection, contract(), decided_at="later"
    )
    with pytest.raises(ValueError, match="provenance"):
        decision.require_eligible(
            document_id=source.document_id, content_hash="0" * 64,
            inspection_manifest_hash=inspection.manifest_hash,
        )
    with pytest.raises(ValueError, match="integrity"):
        replace(decision, decided_at="tampered").require_eligible(
            document_id=source.document_id,
            content_hash=source.content_hash,
            inspection_manifest_hash=inspection.manifest_hash,
        )
    rejected = ScientificScreeningEngine().screen(
        record(year=2010), source, inspection, contract(), decided_at="later"
    )
    with pytest.raises(ValueError, match="SCOPE_MISMATCH"):
        rejected.require_eligible(
            document_id=source.document_id,
            content_hash=source.content_hash,
            inspection_manifest_hash=inspection.manifest_hash,
        )
