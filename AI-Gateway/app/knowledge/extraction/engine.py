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


class EvidenceExtractionEngine:
    parser_name = "researchos-heading-parser"
    parser_version = "1.0.0"

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
    }

    def extract(self, document: SourceDocument, pdf: bytes, *, created_at: str) -> ExtractionManifest:
        if not document.content_hash or sha256(pdf).hexdigest() != document.content_hash:
            raise ValueError("SourceDocument content integrity verification failed")
        objects = []
        for page_number, page in enumerate(PdfReader(BytesIO(pdf)).pages, start=1):
            text = page.extract_text() or ""
            sections = self._sections(text)
            for index, (kind, content, start, end) in enumerate(sections):
                quote_hash = sha256(content.encode("utf-8")).hexdigest()
                identity = f"{document.document_id}:{page_number}:{start}:{end}:{kind.value}:{quote_hash}"
                objects.append(ExtractedScientificObject(
                    f"object-{sha256(identity.encode()).hexdigest()[:24]}", kind,
                    content, DocumentCoordinates(page_number, start, end, quote_hash),
                    0.70, ExtractionReviewState.PROVISIONAL,
                    self.parser_name, self.parser_version,
                ))
        manifest_identity = f"{document.document_id}:{document.content_hash}:{self.parser_version}"
        return ExtractionManifest(
            f"extraction-{sha256(manifest_identity.encode()).hexdigest()[:24]}",
            document.document_id, document.content_hash, created_at,
            self.parser_name, self.parser_version, tuple(objects),
        )

    def _sections(self, text: str):
        matches = list(re.finditer(r"(?im)^\s*(methods?|methodology|results?|findings|limitations?|conclusions?|dataset|data)\s*[:\n]", text))
        sections = []
        for index, match in enumerate(matches):
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            content = " ".join(text[start:end].split()).strip()
            if content:
                sections.append((self._HEADINGS[match.group(1).lower()], content, start, end))
        if not sections:
            for match in re.finditer(r"(?i)([^.!?]*(?:we (?:find|show|conclude)|results? (?:show|indicate))[^.!?]*[.!?])", text):
                content = " ".join(match.group(1).split())
                if content:
                    sections.append((ScientificObjectType.CLAIM, content, match.start(), match.end()))
        return sections
