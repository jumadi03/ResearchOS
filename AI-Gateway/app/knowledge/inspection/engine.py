"""Deterministic PDF structure inspection without scientific judgment."""

from hashlib import sha256
from io import BytesIO
import re

from pypdf import PdfReader

from app.knowledge.ingestion.models import SourceDocument
from app.knowledge.inspection.models import (
    HeadingObservation, PageInspection, SourceInspection,
)


class SourceInspectionEngine:
    inspector_name = "researchos-pdf-structure-inspector"
    inspector_version = "1.0.0"

    def inspect(
        self, document: SourceDocument, content: bytes, *, inspected_at: str,
    ) -> SourceInspection:
        if (
            document.status.value != "acquired"
            or not document.content_hash
            or sha256(content).hexdigest() != document.content_hash
        ):
            raise ValueError("SourceDocument content integrity verification failed")
        if (
            not document.capture_manifest_hash
            or not document.media_type
            or document.media_type != "application/pdf"
        ):
            raise ValueError("Raw-capture provenance is incomplete")
        try:
            reader = PdfReader(BytesIO(content))
        except Exception as exc:
            raise ValueError(
                f"PDF structure inspection failed: {type(exc).__name__}"
            ) from exc
        if reader.is_encrypted:
            raise ValueError("Encrypted PDF cannot be inspected")

        diagnostics = []
        pages = []
        for page_number, page in enumerate(reader.pages, 1):
            try:
                text = page.extract_text() or ""
            except Exception as exc:
                text = ""
                diagnostics.append(
                    f"page {page_number}: text extraction {type(exc).__name__}"
                )
            headings = tuple(self._headings(page_number, text))
            pages.append(PageInspection(
                page_number, len(text), sha256(text.encode("utf-8")).hexdigest(),
                bool(text.strip()), headings,
            ))
            if not text.strip():
                diagnostics.append(f"page {page_number}: no extractable text")

        metadata = tuple(sorted(
            (str(key), str(value))
            for key, value in (reader.metadata or {}).items()
            if value is not None
        ))
        identity = (
            f"{document.document_id}:{document.content_hash}:"
            f"{self.inspector_name}:{self.inspector_version}"
        )
        return SourceInspection(
            f"inspection-{sha256(identity.encode()).hexdigest()[:24]}",
            document.document_id, document.content_hash,
            document.capture_manifest_hash, inspected_at,
            self.inspector_name, self.inspector_version,
            document.media_type, self._pdf_version(content), False,
            len(pages), metadata, tuple(pages), tuple(diagnostics),
            not diagnostics,
        ).finalized()

    @staticmethod
    def _pdf_version(content: bytes) -> str:
        match = re.match(rb"%PDF-(\d+\.\d+)", content)
        return match.group(1).decode("ascii") if match else "unknown"

    @staticmethod
    def _headings(page_number: int, text: str):
        offset = 0
        for line in text.splitlines(keepends=True):
            literal = line.strip()
            start = offset + len(line) - len(line.lstrip())
            end = start + len(literal)
            offset += len(line)
            if (
                literal
                and len(literal) <= 120
                and not literal.endswith((".", "?", "!", ";", ","))
                and (
                    literal.isupper()
                    or re.fullmatch(r"\d+(?:\.\d+)*\s+\S.*", literal)
                )
            ):
                yield HeadingObservation(
                    page_number, start, end, literal,
                    sha256(literal.encode("utf-8")).hexdigest(),
                )
