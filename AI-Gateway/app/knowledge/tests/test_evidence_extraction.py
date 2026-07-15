from io import BytesIO
from pathlib import Path

from reportlab.pdfgen import canvas

from app.knowledge.extraction.engine import EvidenceExtractionEngine
from app.knowledge.extraction.models import ExtractionReviewState, ScientificObjectType
from app.knowledge.extraction.persistence import ExtractionManifestStore
from app.knowledge.ingestion.acquisition import DocumentAcquirer
from app.knowledge.ingestion.models import AccessStatus, DocumentCandidate
from app.knowledge.ingestion.registry import DocumentRegistry


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
    candidate = DocumentCandidate("record", "https://example.test/a.pdf", AccessStatus.OPEN, "CC-BY", "openalex", "source-hash")
    result = DocumentAcquirer(transport=lambda *a, **k: Response(content)).acquire(candidate, acquired_at="time")
    registry = DocumentRegistry(tmp_path / "documents")
    return registry.register(result)[0], registry, content


def test_extraction_has_coordinates_provenance_and_provisional_state(tmp_path: Path) -> None:
    source, _, content = document(tmp_path)
    manifest = EvidenceExtractionEngine().extract(source, content, created_at="later")
    assert [item.object_type for item in manifest.objects] == [ScientificObjectType.METHOD, ScientificObjectType.RESULT, ScientificObjectType.LIMITATION, ScientificObjectType.CONCLUSION]
    assert all(item.review_state is ExtractionReviewState.PROVISIONAL for item in manifest.objects)
    assert all(item.coordinates.page == 1 and item.coordinates.quote_hash for item in manifest.objects)
    store = ExtractionManifestStore(tmp_path / "extractions")
    assert store.save(manifest) == store.save(manifest)


def test_extraction_rejects_tampered_pdf(tmp_path: Path) -> None:
    import pytest
    source, _, _ = document(tmp_path)
    with pytest.raises(ValueError, match="integrity"):
        EvidenceExtractionEngine().extract(source, b"%PDF-tampered", created_at="later")
