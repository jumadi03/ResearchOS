from io import BytesIO
from pathlib import Path
from dataclasses import replace

import pytest
from reportlab.pdfgen import canvas

from app.knowledge.extraction.engine import EvidenceExtractionEngine
from app.knowledge.extraction.models import ExtractionReviewState, ScientificObjectType
from app.knowledge.extraction.persistence import ExtractionManifestStore
from app.knowledge.ingestion.acquisition import DocumentAcquirer
from app.knowledge.ingestion.models import AccessStatus, DocumentCandidate
from app.knowledge.ingestion.registry import DocumentRegistry
from app.knowledge.inspection.engine import SourceInspectionEngine
from app.knowledge.screening.models import (
    ScreeningDecision, ScreeningDimension, ScreeningReason, ScreeningStatus,
)


def pdf_bytes() -> bytes:
    output = BytesIO()
    pdf = canvas.Canvas(output)
    text = pdf.beginText(40, 800)
    for line in ("Methods", "We surveyed 120 villages.", "Results", "Failure was associated with weak governance.", "Limitations", "The sample covers one region.", "Conclusion", "Governance capacity matters."):
        text.textLine(line)
    pdf.drawText(text)
    pdf.save()
    return output.getvalue()


class Response:
    headers = {"Content-Type": "application/pdf"}
    def __init__(self, content): self.content = content
    def raise_for_status(self): return None


def document(tmp_path: Path):
    content = pdf_bytes()
    candidate = DocumentCandidate(
        "record", "https://example.test/a.pdf", AccessStatus.OPEN, "CC-BY",
        "openalex", "source-hash", "source-openalex", "query-family-1",
    )
    result = DocumentAcquirer(transport=lambda *a, **k: Response(content)).acquire(candidate, acquired_at="time")
    registry = DocumentRegistry(tmp_path / "documents")
    return registry.register(result)[0], registry, content


def screened(source, content):
    inspection = SourceInspectionEngine().inspect(
        source, content, inspected_at="screened"
    )
    reasons = tuple(
        ScreeningReason(dimension, f"{dimension.value.upper()}_PASS", True, "passed")
        for dimension in ScreeningDimension
    )
    decision = ScreeningDecision(
        "decision", source.document_id, source.record_id, "contract",
        source.content_hash, inspection.manifest_hash, ScreeningStatus.ELIGIBLE,
        reasons, "test", "1.0", "screened",
    ).finalized()
    return inspection, decision


def test_extraction_has_coordinates_provenance_and_provisional_state(tmp_path: Path) -> None:
    source, _, content = document(tmp_path)
    inspection, decision = screened(source, content)
    manifest = EvidenceExtractionEngine().extract(
        source, content, created_at="later", inspection=inspection,
        screening_decision=decision,
    )
    assert [item.object_type for item in manifest.objects] == [ScientificObjectType.METHOD, ScientificObjectType.RESULT, ScientificObjectType.LIMITATION, ScientificObjectType.CONCLUSION]
    assert all(item.review_state is ExtractionReviewState.PROVISIONAL for item in manifest.objects)
    assert all(item.coordinates.page == 1 and item.coordinates.quote_hash for item in manifest.objects)
    assert manifest.verify()
    assert manifest.screening_decision_id == decision.decision_id
    assert manifest.screening_decision_hash == decision.decision_hash
    assert manifest.inspection_manifest_hash == inspection.manifest_hash
    assert all(
        item.content == item.verbatim_text
        and item.coordinates.page_text_hash
        and item.coordinates.quote_hash
        for item in manifest.objects
    )
    store = ExtractionManifestStore(tmp_path / "extractions")
    assert store.save(manifest) == store.save(manifest)


def test_extraction_rejects_tampered_pdf(tmp_path: Path) -> None:
    source, _, content = document(tmp_path)
    inspection, decision = screened(source, content)
    with pytest.raises(ValueError, match="integrity"):
        EvidenceExtractionEngine().extract(
            source, b"%PDF-tampered", created_at="later",
            inspection=inspection, screening_decision=decision,
        )


def test_direct_extractor_cannot_bypass_screening(tmp_path: Path) -> None:
    source, _, content = document(tmp_path)
    with pytest.raises(ValueError, match="screening decision"):
        EvidenceExtractionEngine().extract(source, content, created_at="later")


def test_extended_scientific_object_headings_remain_provisional(tmp_path: Path) -> None:
    output = BytesIO()
    pdf = canvas.Canvas(output)
    text = pdf.beginText(40, 800)
    for line in (
        "Population", "Adults in coastal villages.",
        "Variables", "Governance capacity and service failure.",
        "Measurements", "Capacity was measured on a five-point scale.",
        "Observations", "Twenty facilities lacked supplies.",
    ):
        text.textLine(line)
    pdf.drawText(text)
    pdf.save()
    content = output.getvalue()
    candidate = DocumentCandidate(
        "record", "https://example.test/extended.pdf", AccessStatus.OPEN,
        "CC-BY", "openalex", "source-hash", "source-openalex",
        "query-family-1",
    )
    result = DocumentAcquirer(
        transport=lambda *a, **k: Response(content)
    ).acquire(candidate, acquired_at="time")
    source = DocumentRegistry(tmp_path / "extended").register(result)[0]
    inspection, decision = screened(source, content)
    manifest = EvidenceExtractionEngine().extract(
        source, content, created_at="later", inspection=inspection,
        screening_decision=decision,
    )
    assert [item.object_type for item in manifest.objects] == [
        ScientificObjectType.POPULATION,
        ScientificObjectType.VARIABLE,
        ScientificObjectType.MEASUREMENT,
        ScientificObjectType.OBSERVATION,
    ]
    assert all(
        item.review_state is ExtractionReviewState.PROVISIONAL
        for item in manifest.objects
    )


def test_manifest_tampering_and_ambiguous_text_fail_safely(tmp_path: Path) -> None:
    source, _, content = document(tmp_path)
    inspection, decision = screened(source, content)
    manifest = EvidenceExtractionEngine().extract(
        source, content, created_at="later", inspection=inspection,
        screening_decision=decision,
    )
    assert not replace(manifest, parser_version="tampered").verify()
    with pytest.raises(ValueError, match="integrity"):
        ExtractionManifestStore(tmp_path / "tampered").save(
            replace(manifest, parser_version="tampered")
        )

    output = BytesIO()
    pdf = canvas.Canvas(output)
    pdf.drawString(40, 800, "Bibliographic text without extractable scientific claims.")
    pdf.save()
    ambiguous = output.getvalue()
    candidate = DocumentCandidate(
        "record", "https://example.test/ambiguous.pdf", AccessStatus.OPEN,
        "CC-BY", "openalex", "source-hash", "source-openalex",
        "query-family-1",
    )
    result = DocumentAcquirer(
        transport=lambda *a, **k: Response(ambiguous)
    ).acquire(candidate, acquired_at="time")
    source = DocumentRegistry(tmp_path / "ambiguous").register(result)[0]
    inspection, decision = screened(source, ambiguous)
    empty = EvidenceExtractionEngine().extract(
        source, ambiguous, created_at="later", inspection=inspection,
        screening_decision=decision,
    )
    assert empty.objects == ()
    assert empty.verify()


def test_extraction_bounds_sections_before_page_furniture_and_back_matter(
    tmp_path: Path,
) -> None:
    output = BytesIO()
    pdf = canvas.Canvas(output)
    text = pdf.beginText(40, 800)
    for line in (
        "Results",
        "Forty percent of journals allowed repository reuse.",
        "PLOS ONE",
        "Citation: Example metadata that is not scientific evidence.",
        "Conclusion",
        "Open-data policies remain inconsistent across journals and require clearer repository standards.",
        "Author Contributions",
        "Writing – original draft: Example Author.",
        "References",
        "1. Example reference.",
    ):
        text.textLine(line)
    pdf.drawText(text)
    pdf.save()
    content = output.getvalue()
    candidate = DocumentCandidate(
        "record", "https://example.test/bounded.pdf", AccessStatus.OPEN,
        "CC-BY", "openalex", "source-hash", "source-openalex",
        "query-family-1",
    )
    result = DocumentAcquirer(
        transport=lambda *a, **k: Response(content)
    ).acquire(candidate, acquired_at="time")
    source = DocumentRegistry(tmp_path / "bounded").register(result)[0]
    inspection, decision = screened(source, content)

    manifest = EvidenceExtractionEngine().extract(
        source, content, created_at="later", inspection=inspection,
        screening_decision=decision,
    )

    assert [item.object_type for item in manifest.objects] == [
        ScientificObjectType.RESULT,
        ScientificObjectType.CONCLUSION,
    ]
    assert manifest.objects[0].content == (
        "Forty percent of journals allowed repository reuse."
    )
    assert manifest.objects[1].content == (
        "Open-data policies remain inconsistent across journals and require clearer repository standards."
    )
    assert all(
        "Author Contributions" not in item.content
        for item in manifest.objects
    )


def test_short_truncated_claim_fragments_fail_closed(tmp_path: Path) -> None:
    output = BytesIO()
    pdf = canvas.Canvas(output)
    text = pdf.beginText(40, 800)
    text.textLine("We find that 26.")
    text.textLine("Looking at disciplinary impacts, we find that 55.")
    pdf.drawText(text)
    pdf.save()
    content = output.getvalue()
    candidate = DocumentCandidate(
        "record", "https://example.test/fragments.pdf", AccessStatus.OPEN,
        "CC-BY", "openalex", "source-hash", "source-openalex",
        "query-family-1",
    )
    result = DocumentAcquirer(
        transport=lambda *a, **k: Response(content)
    ).acquire(candidate, acquired_at="time")
    source = DocumentRegistry(tmp_path / "fragments").register(result)[0]
    inspection, decision = screened(source, content)

    manifest = EvidenceExtractionEngine().extract(
        source, content, created_at="later", inspection=inspection,
        screening_decision=decision,
    )

    assert manifest.objects == ()
