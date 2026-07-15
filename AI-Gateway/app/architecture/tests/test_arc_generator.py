from dataclasses import replace
from pathlib import Path

import pytest

from app.architecture import ArchitectureGraphBuilder
from app.architecture.governance import ARCGenerator, ReviewEngine
from app.architecture.models import (
    ArchitectureLawBundle,
    ArchitectureValidationResult,
    ReviewStatus,
    ValidationReport,
    ValidationStatus,
)


def _approved_inputs(tmp_path: Path):
    package = tmp_path / "sample"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "service.py").write_text("class Service: pass\n", encoding="utf-8")
    graph = ArchitectureGraphBuilder(
        tmp_path, "sample-project", "revision-1"
    ).build()
    bundle = ArchitectureLawBundle("", "1.0.0").finalized()
    report = ValidationReport(
        validation_results=(
            ArchitectureValidationResult(
                "DEPENDENCY",
                graph.graph_id,
                status=ValidationStatus.PASS,
            ),
        ),
        metadata={"graph_id": graph.graph_id, "graph_hash": graph.content_hash},
    )
    engine = ReviewEngine()
    opened = engine.open(
        report,
        reviewer="architect",
        opened_at="2026-07-15T08:00:00Z",
    )
    review = engine.finalize(
        opened,
        actor="architect",
        occurred_at="2026-07-15T09:00:00Z",
        as_of="2026-07-15",
    )
    assert review.status is ReviewStatus.APPROVED
    return graph, bundle, report, review


def test_arc_generator_creates_verified_deterministic_package(tmp_path: Path) -> None:
    graph, bundle, report, review = _approved_inputs(tmp_path)
    generator = ARCGenerator()
    first = generator.generate(
        graph=graph,
        law_bundle=bundle,
        compliance_report=report,
        review=review,
        generated_at="2026-07-15T10:00:00Z",
    )
    second = generator.generate(
        graph=graph,
        law_bundle=bundle,
        compliance_report=report,
        review=review,
        generated_at="2026-07-15T10:00:00Z",
    )

    assert first == second
    assert first.verify() is True
    assert first.manifest.arc_id.startswith("arc:sample-project:")
    assert set(first.all_files()) == {
        "architecture-graph.json",
        "laws.json",
        "compliance-report.json",
        "review.json",
        "report.md",
        "manifest.json",
        "checksums.json",
    }
    assert "# Architecture Review & Compliance Report" in first.artifacts["report.md"]
    assert "Review status: **APPROVED**" in first.artifacts["report.md"]


def test_package_verification_detects_modified_artifact(tmp_path: Path) -> None:
    graph, bundle, report, review = _approved_inputs(tmp_path)
    package = ARCGenerator().generate(
        graph=graph,
        law_bundle=bundle,
        compliance_report=report,
        review=review,
        generated_at="2026-07-15T10:00:00Z",
    )
    tampered = replace(
        package,
        artifacts={**package.artifacts, "report.md": "modified"},
    )
    assert tampered.verify() is False


def test_verified_package_can_be_persisted_without_silent_overwrite(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    graph, bundle, report, review = _approved_inputs(source)
    package = ARCGenerator().generate(
        graph=graph,
        law_bundle=bundle,
        compliance_report=report,
        review=review,
        generated_at="2026-07-15T10:00:00Z",
    )
    output = tmp_path / "arc"
    written = package.write_to(output)
    assert len(written) == 7
    assert (output / "manifest.json").read_text(encoding="utf-8") == (
        package.manifest.to_json()
    )
    with pytest.raises(FileExistsError):
        package.write_to(output)


def test_arc_generation_rejects_open_review(tmp_path: Path) -> None:
    graph, bundle, report, approved = _approved_inputs(tmp_path)
    open_review = replace(approved, status=ReviewStatus.OPEN)
    with pytest.raises(ValueError, match="approved review"):
        ARCGenerator().generate(
            graph=graph,
            law_bundle=bundle,
            compliance_report=report,
            review=open_review,
            generated_at="2026-07-15T10:00:00Z",
        )


def test_arc_generation_rejects_graph_provenance_mismatch(tmp_path: Path) -> None:
    graph, bundle, report, review = _approved_inputs(tmp_path)
    mismatched = replace(
        report,
        metadata={"graph_id": graph.graph_id, "graph_hash": "tampered"},
    )
    with pytest.raises(ValueError, match="graph_hash"):
        ARCGenerator().generate(
            graph=graph,
            law_bundle=bundle,
            compliance_report=mismatched,
            review=review,
            generated_at="2026-07-15T10:00:00Z",
        )
