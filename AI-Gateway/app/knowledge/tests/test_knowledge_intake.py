from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from app.knowledge.extraction.models import (
    DocumentCoordinates, EpistemicClassification, EvidenceAdmission,
    EvidenceReviewAssessment, EvidenceReviewEvent, ExtractedScientificObject,
    ExtractionManifest, ExtractionReviewState, ScientificObjectType,
)
from app.knowledge.ingestion_pipeline import KnowledgeIngestionPipeline


def extraction_manifest() -> ExtractionManifest:
    objects = []
    for identifier, kind, text in (
        ("method-1", ScientificObjectType.METHOD, "Verified survey method"),
        ("result-1", ScientificObjectType.RESULT, "Verified result"),
        ("limitation-1", ScientificObjectType.LIMITATION, "Pending limitation"),
    ):
        quote_hash = sha256(text.encode()).hexdigest()
        objects.append(ExtractedScientificObject(
            identifier, kind, text,
            DocumentCoordinates(
                1, 0, len(text), quote_hash, page_text_hash="a" * 64,
            ),
            .9, ExtractionReviewState.PROVISIONAL, "deterministic", "1.0",
            text, "paragraph",
        ))
    return ExtractionManifest(
        "extraction-1", "document-1", "b" * 64, "2026-07-17T00:00:00Z",
        "deterministic", "1.0", tuple(objects), "1.1", "c" * 64,
        "screening-1", "d" * 64, "e" * 64,
    ).finalized()


def admission(
    manifest: ExtractionManifest, object_id: str,
    state: ExtractionReviewState = ExtractionReviewState.ACCEPTED,
) -> EvidenceAdmission:
    item = next(item for item in manifest.objects if item.object_id == object_id)
    assessment = EvidenceReviewAssessment(
        True, True, True, .9, EpistemicClassification.OBSERVED_FACT,
        item.coordinates.quote_hash, manifest.manifest_hash,
    )
    event = EvidenceReviewEvent(
        f"review-{object_id}", object_id, state, "reviewer@example",
        "Exact source and context reviewed", "2026-07-17T00:01:00Z",
        f"provenance-{object_id}", "pending", assessment, assessment.digest(),
    )
    return EvidenceAdmission(object_id, state, event)


class IntakeRepository:
    def __init__(self, manifest, admissions, *, fail_persistence=False):
        self.manifest = manifest
        self.admissions = {item.evidence_object_id: item for item in admissions}
        self.fail_persistence = fail_persistence
        self.persisted = []

    def load_extraction_manifest(self, extraction_id):
        assert extraction_id == self.manifest.extraction_id
        return self.manifest

    def resolve_evidence_admissions(self, evidence_object_ids):
        return tuple(
            self.admissions.get(object_id, EvidenceAdmission(object_id, None, None))
            for object_id in evidence_object_ids
        )

    def persist_graph(self, graph, *, occurred_at, intake=None):
        if self.fail_persistence:
            raise RuntimeError("canonical persistence failed")
        assert intake is not None and intake.verify()
        graph.validate_evidence_admission()
        self.persisted.append((graph, intake, occurred_at))
        return tuple(edge.edge_id for edge in graph.edges)


def pipeline(tmp_path: Path, repository: IntakeRepository):
    return KnowledgeIngestionPipeline(
        (), tmp_path, data_repository=repository,
    )


def test_intake_registers_only_accepted_evidence_and_records_exclusions(
    tmp_path: Path,
) -> None:
    manifest = extraction_manifest()
    repository = IntakeRepository(manifest, (
        admission(manifest, "method-1"),
        admission(manifest, "result-1"),
        admission(manifest, "limitation-1", ExtractionReviewState.PROVISIONAL),
    ))
    intake, graph, intake_path, graph_path = pipeline(
        tmp_path, repository,
    ).intake_accepted_evidence(
        manifest.extraction_id, evidence_object_ids=(),
        actor_id="indexer@example", occurred_at="2026-07-17T00:02:00Z",
    )

    assert intake.verify() and graph.verify()
    assert intake.admitted_evidence_object_ids == ("method-1", "result-1")
    assert next(
        item for item in intake.decisions
        if item.evidence_object_id == "limitation-1"
    ).reason == "Evidence is not accepted: limitation-1 (status=provisional)"
    assert {node.provenance.object_id for node in graph.nodes if node.provenance} == {
        "method-1", "result-1",
    }
    assert intake_path.exists() and graph_path.exists()


def test_intake_rejects_pending_rejected_missing_and_stale_reviews(
    tmp_path: Path,
) -> None:
    manifest = extraction_manifest()
    stale = admission(manifest, "result-1")
    stale_assessment = replace(
        stale.review_event.assessment, extraction_manifest_hash="f" * 64,
    )
    stale = replace(stale, review_event=replace(
        stale.review_event, assessment=stale_assessment,
        assessment_hash=stale_assessment.digest(),
    ))
    repository = IntakeRepository(manifest, (
        admission(manifest, "method-1", ExtractionReviewState.REJECTED),
        stale,
    ))
    with pytest.raises(ValueError, match="admitted no evidence") as exc:
        pipeline(tmp_path, repository).intake_accepted_evidence(
            manifest.extraction_id,
            evidence_object_ids=("method-1", "result-1", "limitation-1"),
            actor_id="indexer@example", occurred_at="2026-07-17T00:02:00Z",
        )
    message = str(exc.value)
    assert "status=rejected" in message
    assert "review provenance is incomplete" in message
    assert "review status is missing" in message


def test_canonical_persistence_failure_creates_no_intake_snapshot(
    tmp_path: Path,
) -> None:
    manifest = extraction_manifest()
    repository = IntakeRepository(
        manifest, (admission(manifest, "method-1"),),
        fail_persistence=True,
    )
    with pytest.raises(RuntimeError, match="canonical persistence failed"):
        pipeline(tmp_path, repository).intake_accepted_evidence(
            manifest.extraction_id, evidence_object_ids=("method-1",),
            actor_id="indexer@example", occurred_at="2026-07-17T00:02:00Z",
        )
    assert not (tmp_path / "intakes").exists()
    assert not (tmp_path / "graphs").exists()


def test_intake_rejects_evidence_outside_canonical_extraction(tmp_path: Path) -> None:
    manifest = extraction_manifest()
    repository = IntakeRepository(
        manifest, (admission(manifest, "method-1"),),
    )
    with pytest.raises(
        ValueError, match="does not belong to extraction manifest",
    ):
        pipeline(tmp_path, repository).intake_accepted_evidence(
            manifest.extraction_id, evidence_object_ids=("foreign-evidence",),
            actor_id="indexer@example", occurred_at="2026-07-17T00:02:00Z",
        )
