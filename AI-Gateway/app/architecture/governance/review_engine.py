"""Fail-safe and auditable Architecture Review Engine."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime
from hashlib import sha256

from ..models import (
    ReviewAuditEvent,
    ReviewDecision,
    ReviewDecisionType,
    ReviewFinding,
    ReviewSession,
    ReviewStatus,
    ValidationReport,
)


@dataclass(frozen=True, slots=True)
class ReviewEngine:
    """Manage immutable review sessions and append-only decisions."""

    @staticmethod
    def _timestamp(value: str) -> str:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value

    @staticmethod
    def _event_id(review_id: str, action: str, actor: str, at: str, seed: str = "") -> str:
        digest = sha256(
            f"{review_id}:{action}:{actor}:{at}:{seed}".encode("utf-8")
        ).hexdigest()[:16]
        return f"review-event:{digest}"

    def open(
        self,
        report: ValidationReport,
        *,
        reviewer: str,
        opened_at: str,
    ) -> ReviewSession:
        """Open a review bound to one graph and compliance result."""
        self._timestamp(opened_at)
        metadata = report.metadata or {}
        graph_id = metadata.get("graph_id")
        graph_hash = metadata.get("graph_hash")
        if not graph_id or not graph_hash:
            raise ValueError("Review requires compliance graph_id and graph_hash")
        if not reviewer.strip():
            raise ValueError("Reviewer identity is required")

        violations = sorted(
            (
                violation
                for result in report.validation_results
                for violation in result.violations
            ),
            key=lambda item: item.violation_id,
        )
        finding_ids = [item.violation_id for item in violations]
        seed = ":".join(
            [graph_hash, report.status, *finding_ids]
        )
        digest = sha256(seed.encode("utf-8")).hexdigest()[:16]
        review_id = f"review:{digest}"
        event = ReviewAuditEvent(
            event_id=self._event_id(review_id, "OPENED", reviewer, opened_at),
            action="OPENED",
            actor=reviewer,
            occurred_at=opened_at,
            details={"compliance_status": report.status},
        )
        return ReviewSession(
            review_id=review_id,
            graph_id=graph_id,
            graph_hash=graph_hash,
            compliance_status=report.status,
            status=ReviewStatus.OPEN,
            opened_by=reviewer,
            opened_at=opened_at,
            findings=tuple(
                ReviewFinding(item.violation_id, item) for item in violations
            ),
            audit_events=(event,),
        )

    def decide(
        self,
        session: ReviewSession,
        *,
        finding_id: str,
        decision_type: ReviewDecisionType,
        rationale: str,
        reviewer: str,
        decided_at: str,
        expires_at: str | None = None,
    ) -> ReviewSession:
        """Append a reviewer decision; prior decisions remain immutable."""
        if session.status is not ReviewStatus.OPEN:
            raise ValueError("Only an open review can receive decisions")
        self._timestamp(decided_at)
        if finding_id not in {item.finding_id for item in session.findings}:
            raise ValueError("Decision references an unknown finding")
        if not rationale.strip() or not reviewer.strip():
            raise ValueError("Decision rationale and reviewer are required")
        if decision_type is ReviewDecisionType.WAIVE:
            if not expires_at:
                raise ValueError("A waiver requires expires_at")
            expiry = date.fromisoformat(expires_at)
            if expiry < datetime.fromisoformat(
                decided_at.replace("Z", "+00:00")
            ).date():
                raise ValueError("A waiver cannot expire before its decision date")
        elif expires_at is not None:
            raise ValueError("expires_at is only valid for waiver decisions")

        seed = ":".join(
            (
                finding_id,
                decision_type.value,
                rationale,
                reviewer,
                decided_at,
                expires_at or "",
                str(len(session.decisions)),
            )
        )
        decision_id = f"review-decision:{sha256((session.review_id + seed).encode()).hexdigest()[:16]}"
        decision = ReviewDecision(
            decision_id=decision_id,
            finding_id=finding_id,
            decision_type=decision_type,
            rationale=rationale,
            reviewer=reviewer,
            decided_at=decided_at,
            expires_at=expires_at,
        )
        event = ReviewAuditEvent(
            event_id=self._event_id(
                session.review_id, "DECIDED", reviewer, decided_at, decision_id
            ),
            action="DECIDED",
            actor=reviewer,
            occurred_at=decided_at,
            details={
                "decision_id": decision_id,
                "finding_id": finding_id,
                "decision_type": decision_type.value,
            },
        )
        return replace(
            session,
            decisions=(*session.decisions, decision),
            audit_events=(*session.audit_events, event),
        )

    def mark_stale(
        self,
        session: ReviewSession,
        *,
        current_graph_hash: str,
        actor: str,
        occurred_at: str,
    ) -> ReviewSession:
        """Invalidate a review when its source graph has changed."""
        self._timestamp(occurred_at)
        if current_graph_hash == session.graph_hash:
            return session
        event = ReviewAuditEvent(
            event_id=self._event_id(
                session.review_id, "MARKED_STALE", actor, occurred_at
            ),
            action="MARKED_STALE",
            actor=actor,
            occurred_at=occurred_at,
            details={"current_graph_hash": current_graph_hash},
        )
        return replace(
            session,
            status=ReviewStatus.STALE,
            audit_events=(*session.audit_events, event),
        )

    def finalize(
        self,
        session: ReviewSession,
        *,
        actor: str,
        occurred_at: str,
        as_of: str,
    ) -> ReviewSession:
        """Close a review using fail-safe decision and waiver semantics."""
        if session.status is not ReviewStatus.OPEN:
            raise ValueError("Only an open review can be finalized")
        self._timestamp(occurred_at)
        evaluation_date = date.fromisoformat(as_of)

        decisions = {
            finding.finding_id: session.current_decision(finding.finding_id)
            for finding in session.findings
        }
        if session.compliance_status == "INCOMPLETE":
            status = ReviewStatus.CHANGES_REQUESTED
        elif any(
            decision and decision.decision_type is ReviewDecisionType.REJECT
            for decision in decisions.values()
        ):
            status = ReviewStatus.REJECTED
        elif not session.findings and session.compliance_status != "PASS":
            status = ReviewStatus.CHANGES_REQUESTED
        elif all(
            decision
            and (
                decision.decision_type is ReviewDecisionType.FALSE_POSITIVE
                or (
                    decision.decision_type is ReviewDecisionType.WAIVE
                    and decision.expires_at is not None
                    and date.fromisoformat(decision.expires_at) >= evaluation_date
                )
            )
            for decision in decisions.values()
        ):
            status = ReviewStatus.APPROVED
        else:
            status = ReviewStatus.CHANGES_REQUESTED

        event = ReviewAuditEvent(
            event_id=self._event_id(
                session.review_id, "FINALIZED", actor, occurred_at, status.value
            ),
            action="FINALIZED",
            actor=actor,
            occurred_at=occurred_at,
            details={"status": status.value, "as_of": as_of},
        )
        return replace(
            session,
            status=status,
            audit_events=(*session.audit_events, event),
        )
