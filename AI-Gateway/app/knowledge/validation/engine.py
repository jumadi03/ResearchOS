"""Transparent, fail-safe validation assessments."""

from datetime import datetime
from hashlib import sha256

from app.knowledge.theory.models import TheoryBundle
from app.knowledge.validation.models import (
    AssessmentMethod, RiskOfBias, TheoryAssessment, ValidationReport,
    ValidationStatus,
)


class ValidationEngine:
    method = AssessmentMethod(
        "researchos-theory-confidence", "1.0.0", 2,
        ((RiskOfBias.LOW, 1.0), (RiskOfBias.SOME_CONCERNS, 0.75),
         (RiskOfBias.HIGH, 0.40), (RiskOfBias.UNKNOWN, 0.0)),
        0.25,
    )

    def validate(self, bundle: TheoryBundle, *, assessed_at: str, search_completed_at: str, max_age_days: int, bias_by_theory: dict[str, RiskOfBias], reviewer: str, triggered_by_decision_id: str | None = None) -> ValidationReport:
        if not bundle.verify(): raise ValueError("Validation requires a verified theory bundle")
        if max_age_days < 1: raise ValueError("max_age_days must be positive")
        age_days = (self._date(assessed_at) - self._date(search_completed_at)).days
        if age_days < 0:
            raise ValueError("search_completed_at cannot be after assessed_at")
        stale = age_days > max_age_days
        factors = dict(self.method.bias_factors)
        assessments = []
        for proposal in bundle.proposals:
            bias = bias_by_theory.get(proposal.theory_id, RiskOfBias.UNKNOWN)
            graph_count = len({item.graph_id for item in proposal.evidence})
            support = proposal.support_count
            contradictions = proposal.contradiction_count
            reasons = []
            if not proposal.evidence: reasons.append("No traceable evidence assertions")
            if graph_count < self.method.minimum_replications: reasons.append("Independent replication threshold not met")
            if bias is RiskOfBias.UNKNOWN: reasons.append("Risk of bias has not been assessed")
            if contradictions: reasons.append("Unresolved contradicting evidence exists")
            if stale: reasons.append("Literature search is stale")
            score = min(1.0, graph_count / self.method.minimum_replications) * factors[bias]
            score *= max(0.0, 1.0 - contradictions * self.method.contradiction_penalty)
            if contradictions: status = ValidationStatus.FAIL
            elif not proposal.evidence or bias is RiskOfBias.UNKNOWN: status = ValidationStatus.INCOMPLETE
            elif stale: status = ValidationStatus.STALE
            elif graph_count < self.method.minimum_replications: status = ValidationStatus.INCOMPLETE
            else: status = ValidationStatus.PASS
            assessments.append(TheoryAssessment(
                proposal.theory_id, status, round(score, 4), support, graph_count,
                contradictions, bias, tuple(reasons),
                tuple(sorted(item.edge_id for item in proposal.evidence)),
            ))
        statuses = {item.status for item in assessments}
        overall = ValidationStatus.FAIL if ValidationStatus.FAIL in statuses else ValidationStatus.INCOMPLETE if (not assessments or ValidationStatus.INCOMPLETE in statuses) else ValidationStatus.STALE if ValidationStatus.STALE in statuses else ValidationStatus.PASS
        identity = f"{bundle.bundle_id}:{bundle.content_hash}:{assessed_at}:{self.method.version}"
        return ValidationReport(
            f"validation-{sha256(identity.encode()).hexdigest()[:24]}", bundle.bundle_id,
            assessed_at, search_completed_at, max_age_days, reviewer, self.method,
            tuple(assessments), overall, bundle.content_hash,
            triggered_by_decision_id,
        ).finalized()

    @staticmethod
    def _date(value: str) -> datetime:
        try: return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc: raise ValueError(f"Invalid ISO timestamp: {value}") from exc
