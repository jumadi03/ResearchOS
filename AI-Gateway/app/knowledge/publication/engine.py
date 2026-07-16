"""Render canonical evidence-linked Markdown and enforce citation gates."""

from hashlib import sha256
import re

from app.knowledge.publication.models import (
    CitationVerification, PublicationKind, PublicationManifest, PublicationPackage,
)
from app.knowledge.theory.models import TheoryBundle
from app.knowledge.validation.models import ValidationReport, ValidationStatus


class PublicationEngine:
    version = "1.0.0"

    def publish(self, bundle: TheoryBundle, report: ValidationReport, *, kind: PublicationKind, generated_at: str, generated_by: str) -> PublicationPackage:
        if not bundle.verify() or not report.verify():
            raise ValueError("Publication requires verified theory and validation inputs")
        if report.theory_bundle_id != bundle.bundle_id:
            raise ValueError("Validation report does not belong to theory bundle")
        if report.theory_bundle_hash != bundle.content_hash:
            raise ValueError("Validation report is stale for current theory bundle content")
        if kind is PublicationKind.SYSTEMATIC_REVIEW_SUPPORT and report.status is not ValidationStatus.PASS:
            raise ValueError("Systematic review support requires PASS validation")
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
        for edge_id in sorted({item.edge_id for proposal in bundle.proposals for item in proposal.evidence}):
            lines.append(f"- `[evidence:{edge_id}]` — knowledge-graph assertion `{edge_id}`")
        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def verify_citations(markdown: str, available: tuple[str, ...]) -> CitationVerification:
        cited = tuple(sorted(set(re.findall(r"\[evidence:([^\]]+)\]", markdown))))
        available_set = set(available)
        unresolved = tuple(item for item in cited if item not in available_set)
        return CitationVerification(cited, tuple(sorted(available)), unresolved, not unresolved)
