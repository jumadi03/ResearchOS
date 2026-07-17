"""Deterministic, provenance-bound screening before evidence extraction."""

from hashlib import sha256

from app.knowledge.inspection.models import SourceInspection
from app.knowledge.ingestion.models import SourceDocument
from app.knowledge.models import DiscoveryContract, LiteratureRecord
from app.knowledge.screening.models import (
    ScreeningDecision, ScreeningDimension, ScreeningReason, ScreeningStatus,
)


class ScientificScreeningEngine:
    screener_name = "researchos-scientific-screening"
    screener_version = "1.0.0"

    def screen(
        self, record: LiteratureRecord, document: SourceDocument,
        inspection: SourceInspection, contract: DiscoveryContract, *, decided_at: str,
    ) -> ScreeningDecision:
        if not inspection.verify():
            raise ValueError("Source inspection integrity verification failed")
        if (
            inspection.document_id != document.document_id
            or inspection.document_content_hash != document.content_hash
        ):
            raise ValueError("Source inspection provenance does not match document")

        technical = self._technical(inspection)
        scope = self._scope(record, contract)
        evidence = self._evidence(inspection)
        quality = self._quality(record, inspection)
        reasons = (technical, scope, evidence, quality)
        failed = tuple(item for item in reasons if not item.passed)
        status = ScreeningStatus.ELIGIBLE
        if failed:
            status = (
                ScreeningStatus.HUMAN_REVIEW_REQUIRED
                if all(item.code.startswith("REVIEW_") for item in failed)
                else ScreeningStatus.INELIGIBLE
            )
        identity = (
            f"{document.document_id}:{document.content_hash}:"
            f"{inspection.manifest_hash}:{contract.contract_id}:"
            f"{self.screener_version}"
        )
        return ScreeningDecision(
            f"screening-{sha256(identity.encode()).hexdigest()[:24]}",
            document.document_id, record.record_id, contract.contract_id,
            document.content_hash or "", inspection.manifest_hash, status,
            reasons, self.screener_name, self.screener_version, decided_at,
        ).finalized()

    @staticmethod
    def _technical(inspection):
        passed = bool(
            inspection.complete and not inspection.encrypted
            and inspection.media_type == "application/pdf"
            and inspection.page_count > 0
            and all(page.has_extractable_text for page in inspection.pages)
        )
        return ScreeningReason(
            ScreeningDimension.TECHNICAL,
            "TECHNICAL_VALID" if passed else "TECHNICAL_UNREADABLE",
            passed,
            "Document structure is complete and machine-readable" if passed
            else "Document is encrypted, incomplete, or lacks extractable text",
        )

    @staticmethod
    def _scope(record, contract):
        year_ok = (
            record.year is None
            or (contract.year_from is None or record.year >= contract.year_from)
            and (contract.year_to is None or record.year <= contract.year_to)
        )
        type_ok = (
            record.work_type is None
            or record.work_type.casefold()
            in {item.casefold() for item in contract.document_types}
        )
        passed = year_ok and type_ok
        return ScreeningReason(
            ScreeningDimension.SCOPE,
            "SCOPE_MATCH" if passed else "SCOPE_MISMATCH",
            passed,
            "Observed year and document type comply with the discovery contract"
            if passed else "Observed year or document type violates the discovery contract",
        )

    @staticmethod
    def _evidence(inspection):
        passed = any(page.character_count > 0 for page in inspection.pages)
        return ScreeningReason(
            ScreeningDimension.EVIDENCE,
            "EVIDENCE_CONTENT_PRESENT" if passed else "EVIDENCE_CONTENT_ABSENT",
            passed,
            "Document contains locatable textual material" if passed
            else "Document contains no locatable textual material",
        )

    @staticmethod
    def _quality(record, inspection):
        passed = bool(record.title.strip() and record.source_records and inspection.complete)
        return ScreeningReason(
            ScreeningDimension.QUALITY,
            "QUALITY_MINIMUM_MET" if passed else "REVIEW_QUALITY_METADATA_INCOMPLETE",
            passed,
            "Minimum traceable metadata and inspection quality are present" if passed
            else "Metadata quality requires explicit human assessment",
        )

