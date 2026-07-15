import pytest

from app.architecture.governance import ReviewEngine
from app.architecture.models import (
    ArchitectureArtifact,
    ArchitectureFact,
    ArchitectureLaw,
    ArchitectureValidationResult,
    ArchitectureViolation,
    ReviewDecisionType,
    ReviewStatus,
    ValidationReport,
    ValidationStatus,
)


def _report(*, passed: bool = False) -> ValidationReport:
    violations = ()
    status = ValidationStatus.PASS
    if not passed:
        law = ArchitectureLaw("LAW-1", "Law", "Description", "1.0.0")
        artifact = ArchitectureArtifact(
            "module:app.kernel.service",
            "service",
            "Module",
            "app.kernel.service",
            "",
            {"path": "app/kernel/service.py"},
        )
        fact = ArchitectureFact(
            "fact:1",
            artifact,
            "IMPORTS",
            "app.infrastructure.database",
        )
        violations = (
            ArchitectureViolation(
                "violation:1",
                law,
                fact,
                "Forbidden dependency",
            ),
        )
        status = ValidationStatus.FAIL
    result = ArchitectureValidationResult(
        "DEPENDENCY",
        "graph:sample:abc",
        violations=violations,
        status=status,
    )
    return ValidationReport(
        (result,),
        metadata={"graph_id": "graph:sample:abc", "graph_hash": "abc123"},
    )


def _open():
    return ReviewEngine().open(
        _report(), reviewer="reviewer@example", opened_at="2026-07-15T08:00:00Z"
    )


def test_open_review_is_deterministic_and_audited() -> None:
    engine = ReviewEngine()
    first = _open()
    second = _open()
    assert first.review_id == second.review_id
    assert first.status is ReviewStatus.OPEN
    assert tuple(item.finding_id for item in first.findings) == ("violation:1",)
    assert first.audit_events[0].action == "OPENED"


def test_open_requires_graph_provenance() -> None:
    with pytest.raises(ValueError, match="graph_id"):
        ReviewEngine().open(
            ValidationReport(), reviewer="reviewer", opened_at="2026-07-15T08:00:00Z"
        )


def test_waiver_is_append_only_and_can_approve_review() -> None:
    engine = ReviewEngine()
    opened = _open()
    decided = engine.decide(
        opened,
        finding_id="violation:1",
        decision_type=ReviewDecisionType.WAIVE,
        rationale="Approved migration window",
        reviewer="architect@example",
        decided_at="2026-07-15T09:00:00Z",
        expires_at="2026-08-15",
    )
    finalized = engine.finalize(
        decided,
        actor="architect@example",
        occurred_at="2026-07-15T10:00:00Z",
        as_of="2026-07-15",
    )

    assert opened.decisions == ()
    assert len(decided.decisions) == 1
    assert finalized.status is ReviewStatus.APPROVED
    assert [event.action for event in finalized.audit_events] == [
        "OPENED",
        "DECIDED",
        "FINALIZED",
    ]
    assert finalized.calculate_content_hash() == finalized.calculate_content_hash()
    assert '"status": "APPROVED"' in finalized.to_json()


def test_expired_waiver_requests_changes() -> None:
    engine = ReviewEngine()
    decided = engine.decide(
        _open(),
        finding_id="violation:1",
        decision_type=ReviewDecisionType.WAIVE,
        rationale="Temporary waiver",
        reviewer="architect",
        decided_at="2026-07-15T09:00:00Z",
        expires_at="2026-07-20",
    )
    finalized = engine.finalize(
        decided,
        actor="architect",
        occurred_at="2026-08-01T10:00:00Z",
        as_of="2026-08-01",
    )
    assert finalized.status is ReviewStatus.CHANGES_REQUESTED


def test_waiver_requires_expiry_and_known_finding() -> None:
    with pytest.raises(ValueError, match="expires_at"):
        ReviewEngine().decide(
            _open(),
            finding_id="violation:1",
            decision_type=ReviewDecisionType.WAIVE,
            rationale="Temporary",
            reviewer="architect",
            decided_at="2026-07-15T09:00:00Z",
        )
    with pytest.raises(ValueError, match="unknown finding"):
        ReviewEngine().decide(
            _open(),
            finding_id="unknown",
            decision_type=ReviewDecisionType.FALSE_POSITIVE,
            rationale="Not applicable",
            reviewer="architect",
            decided_at="2026-07-15T09:00:00Z",
        )


def test_changed_graph_marks_review_stale() -> None:
    stale = ReviewEngine().mark_stale(
        _open(),
        current_graph_hash="different",
        actor="system",
        occurred_at="2026-07-15T09:00:00Z",
    )
    assert stale.status is ReviewStatus.STALE
    assert stale.audit_events[-1].details["current_graph_hash"] == "different"


def test_passing_report_can_be_approved_without_findings() -> None:
    engine = ReviewEngine()
    opened = engine.open(
        _report(passed=True),
        reviewer="architect",
        opened_at="2026-07-15T08:00:00Z",
    )
    finalized = engine.finalize(
        opened,
        actor="architect",
        occurred_at="2026-07-15T09:00:00Z",
        as_of="2026-07-15",
    )
    assert finalized.status is ReviewStatus.APPROVED


def test_false_positive_approves_but_reject_rejects() -> None:
    engine = ReviewEngine()
    false_positive = engine.decide(
        _open(),
        finding_id="violation:1",
        decision_type=ReviewDecisionType.FALSE_POSITIVE,
        rationale="Generated import is outside the governed source set",
        reviewer="architect",
        decided_at="2026-07-15T09:00:00Z",
    )
    approved = engine.finalize(
        false_positive,
        actor="architect",
        occurred_at="2026-07-15T10:00:00Z",
        as_of="2026-07-15",
    )
    assert approved.status is ReviewStatus.APPROVED

    rejected_decision = engine.decide(
        _open(),
        finding_id="violation:1",
        decision_type=ReviewDecisionType.REJECT,
        rationale="Architecture is unsafe",
        reviewer="architect",
        decided_at="2026-07-15T09:00:00Z",
    )
    rejected = engine.finalize(
        rejected_decision,
        actor="architect",
        occurred_at="2026-07-15T10:00:00Z",
        as_of="2026-07-15",
    )
    assert rejected.status is ReviewStatus.REJECTED


def test_latest_decision_supersedes_without_erasing_history() -> None:
    engine = ReviewEngine()
    accepted = engine.decide(
        _open(),
        finding_id="violation:1",
        decision_type=ReviewDecisionType.ACCEPT,
        rationale="Finding confirmed",
        reviewer="reviewer",
        decided_at="2026-07-15T09:00:00Z",
    )
    waived = engine.decide(
        accepted,
        finding_id="violation:1",
        decision_type=ReviewDecisionType.WAIVE,
        rationale="Migration approved",
        reviewer="architect",
        decided_at="2026-07-15T10:00:00Z",
        expires_at="2026-08-15",
    )
    assert len(waived.decisions) == 2
    assert waived.current_decision("violation:1").decision_type is (
        ReviewDecisionType.WAIVE
    )
