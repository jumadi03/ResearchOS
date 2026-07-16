"""Render canonical evidence-linked Markdown and enforce citation gates."""

from hashlib import sha256
import re

from app.knowledge.publication.models import (
    CitationVerification, PublicationKind, PublicationManifest, PublicationPackage,
)
from app.knowledge.theory.models import TheoryBundle, TheoryReviewState
from app.knowledge.validation.models import ValidationReport, ValidationStatus


class PublicationEngine:
    version = "1.0.0"

    def publish(self, bundle: TheoryBundle, report: ValidationReport, *, kind: PublicationKind, generated_at: str, generated_by: str) -> PublicationPackage:
        readiness = self.readiness(bundle, report, kind)
        if not readiness["ready"]:
            failed = "; ".join(
                item["detail"] for item in readiness["checks"] if not item["passed"]
            )
            raise ValueError(f"Publication readiness failed: {failed}")
        available = tuple(sorted({item.edge_id for proposal in bundle.proposals for item in proposal.evidence}))
        markdown = self._render(bundle, report, kind)
        verification = self.verify_citations(markdown, available)
        if not verification.verified:
            raise ValueError(f"Unresolved evidence citations: {verification.unresolved_citations}")
        markdown_hash = sha256(markdown.encode()).hexdigest()
        identity = f"{bundle.bundle_id}:{report.report_id}:{kind.value}:{markdown_hash}"
        publication_id = f"publication-{sha256(identity.encode()).hexdigest()[:24]}"
        manifest = PublicationManifest(
            publication_id, kind, generated_at, generated_by, bundle.bundle_id,
            bundle.content_hash, report.report_id, report.content_hash,
            report.status.value, self.version, markdown_hash, verification,
        )
        return PublicationPackage(manifest, markdown).finalized()

    def preview(
        self, bundle: TheoryBundle, report: ValidationReport, kind: PublicationKind,
    ) -> dict:
        readiness = self.readiness(bundle, report, kind)
        markdown = self._render(bundle, report, kind)
        available = tuple(sorted({
            item.edge_id for proposal in bundle.proposals
            if proposal.review_state is TheoryReviewState.ACCEPTED
            for item in proposal.evidence
        }))
        citations = self.verify_citations(markdown, available)
        return {**readiness, "markdown": markdown, "citation_verification": citations}

    def readiness(
        self, bundle: TheoryBundle, report: ValidationReport, kind: PublicationKind,
    ) -> dict:
        verified = bundle.verify() and report.verify()
        belongs = report.theory_bundle_id == bundle.bundle_id
        current = belongs and report.theory_bundle_hash == bundle.content_hash
        reviewed = all(
            item.review_state is not TheoryReviewState.PROPOSED
            for item in bundle.proposals
        )
        accepted_ids = {
            item.theory_id for item in bundle.proposals
            if item.review_state is TheoryReviewState.ACCEPTED
        }
        accepted = bool(accepted_ids)
        conflicts = tuple(
            item for item in bundle.competing
            if item.left_theory_id in accepted_ids and item.right_theory_id in accepted_ids
        )
        provenance = all(
            evidence.edge_id and evidence.graph_id and evidence.object_id
            and evidence.quote_hash
            for proposal in bundle.proposals
            if proposal.review_state is TheoryReviewState.ACCEPTED
            for evidence in proposal.evidence
        ) and all(
            proposal.evidence for proposal in bundle.proposals
            if proposal.review_state is TheoryReviewState.ACCEPTED
        )
        allowed_statuses = (
            {ValidationStatus.PASS}
            if kind is PublicationKind.SYSTEMATIC_REVIEW_SUPPORT
            else {ValidationStatus.PASS, ValidationStatus.INCOMPLETE}
        )
        policy = report.status in allowed_statuses
        checks = (
            {"key": "integrity", "label": "Verified inputs", "passed": verified,
             "detail": "Theory bundle and validation report must pass integrity verification."},
            {"key": "current_validation", "label": "Current validation", "passed": current,
             "detail": "Validation report is stale unless it matches exact current theory bundle content."},
            {"key": "review_complete", "label": "Theory review complete", "passed": reviewed,
             "detail": "Every active theory proposal must have a reviewer decision."},
            {"key": "accepted_theory", "label": "Accepted synthesis", "passed": accepted,
             "detail": "At least one accepted theory is required for publication."},
            {"key": "conflicts", "label": "No accepted conflicts", "passed": not conflicts,
             "detail": "Accepted competing theories must be resolved before publication."},
            {"key": "provenance", "label": "Complete evidence provenance", "passed": provenance,
             "detail": "Every accepted theory needs traceable evidence and quote hashes."},
            {"key": "validation_policy", "label": "Validation policy", "passed": policy,
             "detail": (
                 "Systematic review support requires PASS validation."
                 if kind is PublicationKind.SYSTEMATIC_REVIEW_SUPPORT
                 else "This publication type requires PASS or INCOMPLETE validation."
             )},
        )
        return {
            "ready": all(item["passed"] for item in checks),
            "kind": kind.value,
            "validation_report_id": report.report_id,
            "validation_status": report.status.value,
            "checks": checks,
        }

    def _render(self, bundle: TheoryBundle, report: ValidationReport, kind: PublicationKind) -> str:
        assessments = {item.theory_id: item for item in report.assessments}
        lines = [
            f"# {kind.value.replace('_', ' ').title()}", "",
            "## Provenance", "",
            f"- Theory bundle: `{bundle.bundle_id}`", f"- Validation report: `{report.report_id}`",
            f"- Validation status: `{report.status.value.upper()}`", "",
            "## Theory synthesis", "",
        ]
        if not bundle.proposals:
            lines.append("No theory proposals were available for publication.")
        for proposal in bundle.proposals:
            if proposal.review_state is not TheoryReviewState.ACCEPTED:
                continue
            if not proposal.evidence:
                lines.extend([
                    f"### {proposal.theory_id}", "",
                    "Proposal omitted from synthesis because it has no traceable evidence assertion.", "",
                ])
                continue
            citations = " ".join(f"[evidence:{item.edge_id}]" for item in proposal.evidence)
            assessment = assessments.get(proposal.theory_id)
            status = assessment.status.value if assessment else "not_assessed"
            score = assessment.confidence_score if assessment else 0.0
            statement = proposal.statement.rstrip(".") + "."
            lines.extend([
                f"### {proposal.theory_id}", "",
                f"{statement} {citations}".rstrip(), "",
                f"Assessment: `{status}`; method score: `{score:.4f}`.", "",
            ])
        lines.extend(["## Limitations and unresolved conflicts", ""])
        if bundle.competing:
            for item in bundle.competing:
                lines.append(f"- `{item.left_theory_id}` competes with `{item.right_theory_id}`: {item.reason}.")
        else:
            lines.append("- No competing theory relationship was recorded in the input bundle.")
        lines.extend(["", "## Evidence index", ""])
        for edge_id in sorted({
            item.edge_id for proposal in bundle.proposals
            if proposal.review_state is TheoryReviewState.ACCEPTED
            for item in proposal.evidence
        }):
            lines.append(f"- `[evidence:{edge_id}]` — knowledge-graph assertion `{edge_id}`")
        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def verify_citations(markdown: str, available: tuple[str, ...]) -> CitationVerification:
        cited = tuple(sorted(set(re.findall(r"\[evidence:([^\]]+)\]", markdown))))
        available_set = set(available)
        unresolved = tuple(item for item in cited if item not in available_set)
        return CitationVerification(cited, tuple(sorted(available)), unresolved, not unresolved)
