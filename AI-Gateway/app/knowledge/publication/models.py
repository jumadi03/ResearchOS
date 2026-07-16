"""Canonical publication artifact and manifest contracts."""

from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from hashlib import sha256
import json


class PublicationKind(StrEnum):
    LITERATURE_REVIEW = "literature_review"
    SCOPING_REVIEW = "scoping_review"
    SYSTEMATIC_REVIEW_SUPPORT = "systematic_review_support"
    RESEARCH_PROPOSAL = "research_proposal"
    EVIDENCE_BRIEF = "evidence_brief"


@dataclass(frozen=True, slots=True)
class CitationVerification:
    cited_evidence_ids: tuple[str, ...]
    available_evidence_ids: tuple[str, ...]
    unresolved_citations: tuple[str, ...]
    verified: bool


@dataclass(frozen=True, slots=True)
class PublicationManifest:
    publication_id: str
    kind: PublicationKind
    generated_at: str
    generated_by: str
    theory_bundle_id: str
    theory_bundle_hash: str
    validation_report_id: str
    validation_report_hash: str
    validation_status: str
    engine_version: str
    markdown_hash: str
    citation_verification: CitationVerification
    schema_version: str = "1.0"


@dataclass(frozen=True, slots=True)
class PublicationPackage:
    manifest: PublicationManifest
    markdown: str
    content_hash: str = ""

    def finalized(self):
        payload = asdict(replace(self, content_hash=""))
        digest = sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return replace(self, content_hash=digest)

    def verify(self) -> bool:
        return (
            bool(self.content_hash)
            and self.finalized().content_hash == self.content_hash
            and sha256(self.markdown.encode()).hexdigest() == self.manifest.markdown_hash
            and self.manifest.citation_verification.verified
        )
