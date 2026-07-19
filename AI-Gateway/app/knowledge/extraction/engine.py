"""Deterministic PDF parsing into traceable provisional scientific objects."""

from __future__ import annotations

from hashlib import sha256
import re
from io import BytesIO

from pypdf import PdfReader

from app.knowledge.extraction.models import (
    DocumentCoordinates, ExtractedScientificObject, ExtractionManifest,
    ExtractionReviewState, ScientificObjectType,
)
from app.knowledge.ingestion.models import SourceDocument
from app.knowledge.inspection.models import SourceInspection
from app.knowledge.screening.models import ScreeningDecision


class EvidenceExtractionEngine:
    parser_name = "researchos-heading-parser"
    parser_version = "1.2.0"

    _HEADINGS = {
        "method": ScientificObjectType.METHOD,
        "methodology": ScientificObjectType.METHOD,
        "methods": ScientificObjectType.METHOD,
        "results": ScientificObjectType.RESULT,
        "findings": ScientificObjectType.RESULT,
        "limitation": ScientificObjectType.LIMITATION,
        "limitations": ScientificObjectType.LIMITATION,
        "conclusion": ScientificObjectType.CONCLUSION,
        "conclusions": ScientificObjectType.CONCLUSION,
        "dataset": ScientificObjectType.DATASET,
        "data": ScientificObjectType.DATASET,
        "population": ScientificObjectType.POPULATION,
        "participants": ScientificObjectType.POPULATION,
        "variables": ScientificObjectType.VARIABLE,
        "measures": ScientificObjectType.MEASUREMENT,
        "measurements": ScientificObjectType.MEASUREMENT,
        "observations": ScientificObjectType.OBSERVATION,
        "survey recruitment": ScientificObjectType.METHOD,
        "data collection": ScientificObjectType.METHOD,
        "awareness and concern about reproducibility and replicability": (
            ScientificObjectType.RESULT
        ),
    }
    _STOP_HEADINGS = (
        "author contributions", "supporting information", "references",
        "discussion", "discussion and recommendations", "acknowledgments",
        "acknowledgements", "funding", "competing interests",
    )
    _PAGE_FURNITURE = re.compile(
        r"(?im)^[ \t]*(?:PLOS ONE|OPEN ACCESS|a1111111111|Citation:|Editor:|"
        r"Received:|Accepted:|Published:|Copyright:|Data Availability Statement:|"
        r"Funding:|Competing interests:).*$"
    )
    _NON_SCIENTIFIC_CONTRIBUTIONS = re.compile(
        r"(?i)(?:Project administration:|Writing\s*[–-]\s*original draft:|"
        r"Writing\s*[–-]\s*review\s*&\s*editing:|Supervision:|Visualization:)"
    )

    def extract(
        self, document: SourceDocument, pdf: bytes, *, created_at: str,
        inspection: SourceInspection | None = None,
        screening_decision: ScreeningDecision | None = None,
    ) -> ExtractionManifest:
        if inspection is None or screening_decision is None:
            raise ValueError("Eligible screening decision is required for evidence extraction")
        screening_decision.require_eligible(
            document_id=document.document_id,
            content_hash=document.content_hash or "",
            inspection_manifest_hash=inspection.manifest_hash,
        )
        if not document.content_hash or sha256(pdf).hexdigest() != document.content_hash:
            raise ValueError("SourceDocument content integrity verification failed")
        objects = []
        for page_number, page in enumerate(PdfReader(BytesIO(pdf)).pages, start=1):
            text = page.extract_text() or ""
            page_text_hash = sha256(text.encode("utf-8")).hexdigest()
            sections = self._sections(text)
            for kind, content, start, end, section, rule, confidence in sections:
                quote_hash = sha256(content.encode("utf-8")).hexdigest()
                identity = f"{document.document_id}:{page_number}:{start}:{end}:{kind.value}:{quote_hash}"
                objects.append(ExtractedScientificObject(
                    f"object-{sha256(identity.encode()).hexdigest()[:24]}", kind,
                    content, DocumentCoordinates(
                        page_number, start, end, quote_hash, section=section,
                        page_text_hash=page_text_hash,
                    ),
                    confidence, ExtractionReviewState.PROVISIONAL,
                    self.parser_name, self.parser_version,
                    verbatim_text=content, extraction_rule=rule,
                ))
        configuration_hash = sha256((
            self.parser_name + ":" + self.parser_version + ":"
            + ",".join(sorted(self._HEADINGS))
        ).encode()).hexdigest()
        manifest_identity = (
            f"{document.document_id}:{document.content_hash}:"
            f"{screening_decision.decision_hash}:{self.parser_version}"
        )
        return ExtractionManifest(
            f"extraction-{sha256(manifest_identity.encode()).hexdigest()[:24]}",
            document.document_id, document.content_hash, created_at,
            self.parser_name, self.parser_version, tuple(objects),
            schema_version="1.1",
            inspection_manifest_hash=inspection.manifest_hash,
            screening_decision_id=screening_decision.decision_id,
            screening_decision_hash=screening_decision.decision_hash,
            configuration_hash=configuration_hash,
        ).finalized()

    def _sections(self, text: str):
        all_headings = (*self._HEADINGS, *self._STOP_HEADINGS)
        headings = "|".join(sorted(
            (re.escape(item) for item in all_headings), key=len, reverse=True
        ))
        matches = list(re.finditer(
            rf"(?im)^\s*({headings})\s*[:\n]", text
        ))
        sections = []
        for index, match in enumerate(matches):
            section = match.group(1).strip()
            if section.lower() in self._STOP_HEADINGS:
                continue
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            end = self._clean_end(text, start, end)
            raw = text[start:end]
            leading = len(raw) - len(raw.lstrip())
            trailing = len(raw.rstrip())
            start += leading
            end = match.end() + trailing
            content = text[start:end]
            if (
                len(content) >= 20
                and not self._NON_SCIENTIFIC_CONTRIBUTIONS.search(content)
            ):
                sections.append((
                    self._HEADINGS[section.lower()], content, start, end,
                    section, "bounded_heading_section", 0.90,
                ))
        if not sections:
            for match in re.finditer(r"(?i)([^.!?]*(?:we (?:find|show|conclude)|results? (?:show|indicate))[^.!?]*[.!?])", text):
                content = match.group(1).strip()
                if len(content) >= 80:
                    start = match.start(1) + len(match.group(1)) - len(
                        match.group(1).lstrip()
                    )
                    sections.append((
                        ScientificObjectType.CLAIM, content,
                        start, start + len(content), None,
                        "complete_explicit_claim_sentence", 0.75,
                    ))
        return sections

    def _clean_end(self, text: str, start: int, end: int) -> int:
        candidate = text[start:end]
        furniture = self._PAGE_FURNITURE.search(candidate)
        if furniture:
            end = start + furniture.start()
            candidate = text[start:end]
        candidate = candidate.rstrip()
        if candidate and candidate[-1] not in ".!?":
            sentence_ends = tuple(re.finditer(r"[.!?](?=\s|$)", candidate))
            if sentence_ends:
                end = start + sentence_ends[-1].end()
        return end
