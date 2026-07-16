from dataclasses import replace
from io import BytesIO

import pytest
from reportlab.pdfgen import canvas

from app.knowledge.ingestion.acquisition import DocumentAcquirer
from app.knowledge.ingestion.models import AccessStatus, DocumentCandidate
from app.knowledge.ingestion.registry import DocumentRegistry
from app.knowledge.inspection.engine import SourceInspectionEngine
from app.knowledge.inspection.persistence import SourceInspectionStore


def source(tmp_path):
    output = BytesIO()
    pdf = canvas.Canvas(output)
    pdf.setTitle("Literal source title")
    pdf.drawString(40, 800, "METHODS")
    pdf.drawString(40, 780, "We observed a factual passage.")
    pdf.showPage()
    pdf.drawString(40, 800, "2 RESULTS")
    pdf.save()
    content = output.getvalue()

    class Response:
        headers = {"Content-Type": "application/pdf"}
        status_code = 200
        url = "https://example.test/source.pdf"
        content = output.getvalue()
        def raise_for_status(self): return None

    candidate = DocumentCandidate(
        "record", Response.url, AccessStatus.OPEN, "CC-BY-4.0",
        "openalex", "source-hash", "source-openalex", "query-family-1",
    )
    result = DocumentAcquirer(
        transport=lambda *args, **kwargs: Response(),
    ).acquire(candidate, acquired_at="acquired")
    document, _ = DocumentRegistry(tmp_path / "documents").register(result)
    return document, content


def test_inspection_is_factual_deterministic_and_integrity_verified(tmp_path):
    document, content = source(tmp_path)
    engine = SourceInspectionEngine()
    first = engine.inspect(document, content, inspected_at="time")
    second = engine.inspect(document, content, inspected_at="time")

    assert first == second
    assert first.verify()
    assert first.page_count == 2
    assert dict(first.document_metadata)["/Title"] == "Literal source title"
    assert [heading.text for page in first.pages for heading in page.headings] == [
        "METHODS", "2 RESULTS",
    ]
    serialized = repr(first).casefold()
    assert "scientificobjecttype" not in serialized
    assert "confidence" not in serialized
    assert "review_state" not in serialized


def test_inspection_snapshot_tampering_and_content_mismatch_fail_closed(tmp_path):
    document, content = source(tmp_path)
    inspection = SourceInspectionEngine().inspect(
        document, content, inspected_at="time",
    )
    store = SourceInspectionStore(tmp_path / "inspections")
    path = store.save(inspection)
    assert store.load(path) == inspection
    assert store.find(
        document.document_id, document.content_hash,
        inspection.inspector_name, inspection.inspector_version,
    ) == inspection

    path.write_text(path.read_text().replace("METHODS", "CLAIM"), encoding="utf-8")
    with pytest.raises(ValueError, match="integrity verification failed"):
        store.load(path)
    with pytest.raises(ValueError, match="content integrity"):
        SourceInspectionEngine().inspect(
            document, content + b"tampered", inspected_at="time",
        )
    assert not replace(inspection, page_count=3).verify()


def test_malformed_pdf_is_rejected(tmp_path):
    document, _ = source(tmp_path)
    malformed = b"%PDF-1.7\nnot a document"
    tampered_document = replace(
        document,
        content_hash=__import__("hashlib").sha256(malformed).hexdigest(),
        manifest_hash=None,
    )
    with pytest.raises(ValueError, match="PDF structure inspection failed"):
        SourceInspectionEngine().inspect(
            tampered_document, malformed, inspected_at="time",
        )
