"""Immutable Review Engine aggregate and audit records."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from hashlib import sha256
import json
from typing import Any

from .architecture_violation import ArchitectureViolation
from .review_status import ReviewDecisionType, ReviewStatus
from ..schema import REVIEW_SCHEMA


@dataclass(frozen=True, slots=True)
class ReviewFinding:
    finding_id: str
    violation: ArchitectureViolation


@dataclass(frozen=True, slots=True)
class ReviewDecision:
    decision_id: str
    finding_id: str
    decision_type: ReviewDecisionType
    rationale: str
    reviewer: str
    decided_at: str
    expires_at: str | None = None


@dataclass(frozen=True, slots=True)
class ReviewAuditEvent:
    event_id: str
    action: str
    actor: str
    occurred_at: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ReviewSession:
    review_id: str
    graph_id: str
    graph_hash: str
    compliance_status: str
    status: ReviewStatus
    opened_by: str
    opened_at: str
    findings: tuple[ReviewFinding, ...] = ()
    decisions: tuple[ReviewDecision, ...] = ()
    audit_events: tuple[ReviewAuditEvent, ...] = ()
    schema_version: str = "1.0"

    def current_decision(self, finding_id: str) -> ReviewDecision | None:
        """Return the most recent decision for a finding."""
        for decision in reversed(self.decisions):
            if decision.finding_id == finding_id:
                return decision
        return None

    def to_json(self, *, indent: int | None = 2) -> str:
        """Serialize the complete review and audit trail deterministically."""
        payload = asdict(self)
        if self.schema_version == "0.9":
            payload.pop("schema_version")
        payload["content_hash"] = self.calculate_content_hash()
        return json.dumps(
            payload,
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    def calculate_content_hash(self) -> str:
        """Return a SHA-256 hash suitable for ARC manifest provenance."""
        payload = asdict(self)
        if self.schema_version == "0.9":
            payload.pop("schema_version")
        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        return sha256(canonical.encode("utf-8")).hexdigest()

    @classmethod
    def from_json(cls, value: str) -> "ReviewSession":
        """Rehydrate a review and verify its content-addressed snapshot."""
        payload = json.loads(value)
        schema_version = payload.get("schema_version", "0.9")
        REVIEW_SCHEMA.require_readable(schema_version)
        session = cls(
            review_id=payload["review_id"],
            graph_id=payload["graph_id"],
            graph_hash=payload["graph_hash"],
            compliance_status=payload["compliance_status"],
            status=ReviewStatus(payload["status"]),
            opened_by=payload["opened_by"],
            opened_at=payload["opened_at"],
            findings=tuple(
                ReviewFinding(
                    finding_id=item["finding_id"],
                    violation=ArchitectureViolation.from_dict(item["violation"]),
                )
                for item in payload.get("findings", [])
            ),
            decisions=tuple(
                ReviewDecision(
                    decision_id=item["decision_id"],
                    finding_id=item["finding_id"],
                    decision_type=ReviewDecisionType(item["decision_type"]),
                    rationale=item["rationale"],
                    reviewer=item["reviewer"],
                    decided_at=item["decided_at"],
                    expires_at=item.get("expires_at"),
                )
                for item in payload.get("decisions", [])
            ),
            audit_events=tuple(
                ReviewAuditEvent(
                    event_id=item["event_id"],
                    action=item["action"],
                    actor=item["actor"],
                    occurred_at=item["occurred_at"],
                    details=item.get("details", {}),
                )
                for item in payload.get("audit_events", [])
            ),
            schema_version=schema_version,
        )
        if payload.get("content_hash") != session.calculate_content_hash():
            raise ValueError("Review snapshot content hash is invalid")
        seed = ":".join(
            [
                session.graph_hash,
                session.compliance_status,
                *(finding.finding_id for finding in session.findings),
            ]
        )
        expected_id = f"review:{sha256(seed.encode('utf-8')).hexdigest()[:16]}"
        if session.review_id != expected_id:
            raise ValueError("Review identifier is invalid")
        return session

    def upgraded(self) -> "ReviewSession":
        """Return a current-schema copy with a newly protected content hash."""
        return replace(self, schema_version=REVIEW_SCHEMA.current)
