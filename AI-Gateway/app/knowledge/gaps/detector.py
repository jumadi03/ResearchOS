"""Deterministic, explainable research-gap rules."""

from hashlib import sha256

from app.knowledge.gaps.models import (
    GapAnalysis, GapSeverity, GapType, HypothesisProposal, ResearchGap,
)
from app.knowledge.theory.models import TheoryBundle


class ResearchGapDetector:
    ruleset_version = "1.0.0"

    def analyze(self, bundle: TheoryBundle, *, created_at: str) -> GapAnalysis:
        if not bundle.verify():
            raise ValueError("Gap detection requires a verified theory bundle")
        gaps = []
        for proposal in bundle.proposals:
            evidence_ids = tuple(sorted(item.edge_id for item in proposal.evidence))
            if not evidence_ids:
                gaps.append(self._gap(
                    GapType.EVIDENCE_ABSENCE, GapSeverity.HIGH, (proposal.theory_id,), (),
                    "GAP-EVIDENCE-001", "Theory proposal has no traceable evidence assertion.",
                ))
            elif len(evidence_ids) < 2:
                gaps.append(self._gap(
                    GapType.LIMITED_COVERAGE, GapSeverity.MEDIUM, (proposal.theory_id,), evidence_ids,
                    "GAP-COVERAGE-001", "Theory proposal is supported by fewer than two independent graph assertions.",
                ))
            if proposal.contradiction_count:
                gaps.append(self._gap(
                    GapType.UNRESOLVED_CONTRADICTION, GapSeverity.HIGH,
                    (proposal.theory_id,), evidence_ids, "GAP-CONFLICT-001",
                    "Theory proposal contains unresolved contradicting evidence.",
                ))
        for competing in bundle.competing:
            gaps.append(self._gap(
                GapType.UNRESOLVED_CONTRADICTION, GapSeverity.HIGH,
                tuple(sorted((competing.left_theory_id, competing.right_theory_id))), (),
                "GAP-CONFLICT-002", f"Competing theory proposals remain unresolved: {competing.reason}.",
            ))
        unique = {gap.gap_id: gap for gap in gaps}
        gaps = tuple(sorted(unique.values(), key=lambda item: item.gap_id))
        hypotheses = tuple(self._hypothesis(gap) for gap in gaps)
        identity = f"{bundle.bundle_id}:{bundle.content_hash}:{created_at}:{self.ruleset_version}"
        return GapAnalysis(
            f"gap-analysis-{sha256(identity.encode()).hexdigest()[:24]}",
            bundle.bundle_id, created_at, gaps, hypotheses,
            ruleset_version=self.ruleset_version,
        ).finalized()

    @staticmethod
    def _gap(kind, severity, theories, evidence, rule, explanation):
        identity = f"{kind.value}:{':'.join(theories)}:{rule}"
        return ResearchGap(
            f"gap-{sha256(identity.encode()).hexdigest()[:24]}", kind, severity,
            theories, evidence, rule, explanation,
        )

    @staticmethod
    def _hypothesis(gap: ResearchGap) -> HypothesisProposal:
        if gap.gap_type is GapType.UNRESOLVED_CONTRADICTION:
            statement = "The competing outcomes are moderated by an unmodeled contextual factor."
        elif gap.gap_type is GapType.EVIDENCE_ABSENCE:
            statement = "The proposed relationship is observable under a preregistered direct test."
        else:
            statement = "The proposed relationship replicates in an independent setting and sample."
        return HypothesisProposal(
            f"hypothesis-{sha256((gap.gap_id + statement).encode()).hexdigest()[:24]}",
            gap.gap_id, statement, f"Generated from {gap.rule_id}: {gap.explanation}", True,
        )
