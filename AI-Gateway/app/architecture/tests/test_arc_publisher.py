from pathlib import Path

from pypdf import PdfReader

from app.architecture import ArchitectureGraphBuilder
from app.architecture.governance import ARCGenerator, ARCPublisher, ReviewEngine
from app.architecture.models import (
    ArchitectureLawBundle,
    ArchitectureValidationResult,
    ValidationReport,
    ValidationStatus,
)


def _arc_package(tmp_path: Path):
    source = tmp_path / "source"
    package_dir = source / "sample"
    package_dir.mkdir(parents=True)
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (package_dir / "service.py").write_text("class Service: pass\n", encoding="utf-8")
    graph = ArchitectureGraphBuilder(source, "sample-project", "revision-1").build()
    bundle = ArchitectureLawBundle("", "1.0.0").finalized()
    report = ValidationReport(
        (
            ArchitectureValidationResult(
                "DEPENDENCY",
                graph.graph_id,
                status=ValidationStatus.PASS,
            ),
        ),
        {"graph_id": graph.graph_id, "graph_hash": graph.content_hash},
    )
    engine = ReviewEngine()
    review = engine.finalize(
        engine.open(
            report,
            reviewer="architect",
            opened_at="2026-07-15T08:00:00Z",
        ),
        actor="architect",
        occurred_at="2026-07-15T09:00:00Z",
        as_of="2026-07-15",
    )
    return ARCGenerator().generate(
        graph=graph,
        law_bundle=bundle,
        compliance_report=report,
        review=review,
        generated_at="2026-07-15T10:00:00Z",
    )


def test_publisher_adds_verified_html_and_pdf(tmp_path: Path) -> None:
    source = _arc_package(tmp_path)
    published = ARCPublisher().publish(source)
    repeated = ARCPublisher().publish(source)

    assert source.verify() is True
    assert published.verify() is True
    assert source.manifest.arc_id != published.manifest.arc_id
    assert isinstance(published.artifacts["report.html"], str)
    assert published.artifacts["report.pdf"].startswith(b"%PDF-")
    assert set(published.manifest.artifact_checksums) == set(published.artifacts)
    assert repeated.manifest.arc_id == published.manifest.arc_id
    assert repeated.artifacts["report.pdf"] == published.artifacts["report.pdf"]


def test_html_renderer_escapes_untrusted_markdown_content() -> None:
    html = ARCPublisher().render_html(
        "# Report\n\n- Value: `<script>alert(1)</script>`\n"
    )
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert '<meta charset="utf-8">' in html


def test_pdf_is_readable_and_contains_report_text(tmp_path: Path) -> None:
    published = ARCPublisher().publish(_arc_package(tmp_path))
    output = tmp_path / "report.pdf"
    output.write_bytes(published.artifacts["report.pdf"])
    reader = PdfReader(output)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert len(reader.pages) >= 1
    assert "Architecture Review & Compliance Report" in text
    assert "ResearchOS - Architecture Review & Compliance" in text


def test_published_package_persists_pdf_as_binary(tmp_path: Path) -> None:
    published = ARCPublisher().publish(_arc_package(tmp_path / "input"))
    output = tmp_path / "published"
    published.write_to(output)
    assert (output / "report.pdf").read_bytes().startswith(b"%PDF-")
    assert (output / "report.html").read_text(encoding="utf-8").startswith(
        "<!doctype html>"
    )
