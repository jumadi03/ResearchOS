from dataclasses import asdict, replace
from hashlib import sha256
import json
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
        self.derived_manifests = {}

    def load_extraction_manifest(self, extraction_id):
        if extraction_id in self.derived_manifests:
            return self.derived_manifests[extraction_id]
        if extraction_id != self.manifest.extraction_id:
            raise KeyError(extraction_id)
        return self.manifest

    def persist_evidence(
        self, record, manifest, *, source_extraction_id=None,
    ):
        assert record is None
        assert source_extraction_id == self.manifest.extraction_id
        assert manifest.verify()
        self.derived_manifests[manifest.extraction_id] = manifest
        return tuple(item.object_id for item in manifest.objects)

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
    legacy_payload = asdict(replace(intake, content_hash=""))
    legacy_payload.pop("semantic_relation_ids")
    legacy_hash = sha256(json.dumps(
        legacy_payload, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"),
    ).encode()).hexdigest()
    assert intake.content_hash == legacy_hash


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


def test_semantic_relation_requires_independent_review_before_intake(
    tmp_path: Path,
) -> None:
    manifest = extraction_manifest()
    repository = IntakeRepository(manifest, (
        admission(manifest, "result-1"),
        admission(manifest, "limitation-1"),
    ))
    service = pipeline(tmp_path, repository)
    relation, _ = service.propose_semantic_relation(
        manifest.extraction_id, source_object_id="result-1",
        target_object_id="limitation-1", edge_type="has_limitation",
        provenance_object_id="limitation-1", proposed_by="proposer@example",
        rationale="The reviewed passage states this result limitation",
        proposed_at="2026-07-17T00:02:00Z",
    )
    assert relation.state.value == "proposed"
    queue = service.semantic_relation_review_queue(manifest.extraction_id)
    assert queue["counts"]["proposed"] == 1
    assert queue["counts"]["accepted_objects"] == 2
    assert queue["proposals"][0]["source"].object_id == "result-1"
    assert queue["proposals"][0]["target"].object_id == "limitation-1"
    assert queue["review_context"][0]["review_event"].provenance_id
    assert queue["review_context"][0][
        "review_event"
    ].assessment_hash
    assert next(
        item for item in queue["annotation_coverage"]
        if item["object_type"] == "limitation"
    )["status"] == "present"
    assert "population" in queue["blockers"][-1]
    with pytest.raises(ValueError, match="not accepted"):
        service.intake_accepted_evidence(
            manifest.extraction_id,
            evidence_object_ids=("result-1", "limitation-1"),
            semantic_relation_ids=(relation.relation_id,),
            actor_id="indexer@example", occurred_at="2026-07-17T00:03:00Z",
        )
    with pytest.raises(ValueError, match="differ from proposer"):
        service.review_semantic_relation(
            relation.relation_id, decision="accepted",
            reviewer="proposer@example", rationale="Self approval",
            occurred_at="2026-07-17T00:04:00Z",
        )

    accepted, _ = service.review_semantic_relation(
        relation.relation_id, decision="accepted",
        reviewer="reviewer@example", rationale="Source and relation verified",
        occurred_at="2026-07-17T00:05:00Z",
    )
    intake, graph, _, _ = service.intake_accepted_evidence(
        manifest.extraction_id,
        evidence_object_ids=("result-1", "limitation-1"),
        semantic_relation_ids=(relation.relation_id,),
        actor_id="indexer@example", occurred_at="2026-07-17T00:06:00Z",
    )
    assert accepted.verify() and intake.verify() and graph.verify()
    assert intake.schema_version == "1.1"
    assert intake.semantic_relation_ids == (relation.relation_id,)
    semantic = next(
        edge for edge in graph.edges if edge.edge_type.value == "has_limitation"
    )
    assert semantic.provenance.object_id == "limitation-1"
    current = service.list_semantic_relations()[0]
    assert current.admissions[0].graph_id == graph.graph_id
    assert current.admissions[0].intake_id == intake.intake_id
    restored = pipeline(tmp_path, repository).list_semantic_relations()[0]
    assert restored.admissions == current.admissions


def test_semantic_relation_reversal_is_historical_persistent_and_fail_closed(
    tmp_path: Path,
) -> None:
    manifest = extraction_manifest()
    repository = IntakeRepository(manifest, (
        admission(manifest, "result-1"),
        admission(manifest, "limitation-1"),
    ))
    service = pipeline(tmp_path, repository)
    proposed, _ = service.propose_semantic_relation(
        manifest.extraction_id, source_object_id="result-1",
        target_object_id="limitation-1", edge_type="has_limitation",
        provenance_object_id="limitation-1", proposed_by="proposer@example",
        rationale="Proposed from reviewed source context",
        proposed_at="2026-07-17T01:00:00Z",
    )
    accepted, _ = service.review_semantic_relation(
        proposed.relation_id, decision="accepted", reviewer="reviewer@example",
        rationale="Relation verified", occurred_at="2026-07-17T01:01:00Z",
    )
    rejected, _ = service.review_semantic_relation(
        proposed.relation_id, decision="rejected", reviewer="reviewer@example",
        rationale="Later context review invalidated the relation",
        occurred_at="2026-07-17T01:02:00Z",
    )
    assert accepted.state.value == "accepted"
    assert rejected.state.value == "rejected"
    assert len(rejected.reviews) == 2
    restored = pipeline(tmp_path, repository)
    current = restored.list_semantic_relations()[0]
    assert current == rejected and current.verify()
    with pytest.raises(ValueError, match="not accepted"):
        restored.intake_accepted_evidence(
            manifest.extraction_id,
            evidence_object_ids=("result-1", "limitation-1"),
            semantic_relation_ids=(current.relation_id,),
            actor_id="indexer@example", occurred_at="2026-07-17T01:03:00Z",
        )


def test_semantic_relation_rejects_structural_types_and_broken_review_chain(
    tmp_path: Path,
) -> None:
    manifest = extraction_manifest()
    repository = IntakeRepository(manifest, (
        admission(manifest, "result-1"),
        admission(manifest, "limitation-1"),
    ))
    service = pipeline(tmp_path, repository)
    with pytest.raises(ValueError, match="not an admissible scientific"):
        service.propose_semantic_relation(
            manifest.extraction_id, source_object_id="result-1",
            target_object_id="limitation-1", edge_type="contains",
            provenance_object_id="limitation-1",
            proposed_by="proposer@example",
            rationale="Attempted structural assertion",
            proposed_at="2026-07-17T02:00:00Z",
        )
    relation, _ = service.propose_semantic_relation(
        manifest.extraction_id, source_object_id="result-1",
        target_object_id="limitation-1", edge_type="has_limitation",
        provenance_object_id="limitation-1", proposed_by="proposer@example",
        rationale="Reviewed source context suggests this limitation",
        proposed_at="2026-07-17T02:01:00Z",
    )
    accepted, _ = service.review_semantic_relation(
        relation.relation_id, decision="accepted", reviewer="reviewer@example",
        rationale="Verified relation", occurred_at="2026-07-17T02:02:00Z",
    )
    broken = replace(
        accepted,
        reviews=(replace(
            accepted.reviews[0], previous_state=accepted.state,
        ),),
        content_hash="",
    ).finalized()
    assert broken.verify() is False


def test_semantic_reextraction_persists_only_provisional_derived_objects(
    tmp_path: Path,
) -> None:
    text = (
        "The final sample comprised 425 qualitative researchers (n = 425). "
        "Attitudes toward data sharing were measured on a Likert scale. "
        "The number of identified drivers does not indicate their importance."
    )
    quote_hash = sha256(text.encode()).hexdigest()
    source = ExtractedScientificObject(
        "semantic-source", ScientificObjectType.RESULT, text,
        DocumentCoordinates(
            4, 20, 20 + len(text), quote_hash,
            page_text_hash="a" * 64,
        ),
        0.9, ExtractionReviewState.PROVISIONAL,
        "source-parser", "1.2.0", text, "bounded_heading_section",
    )
    manifest = ExtractionManifest(
        "semantic-parent", "document-1", "b" * 64,
        "2026-07-19T00:00:00Z", "source-parser", "1.2.0",
        (source,), "1.1", "c" * 64, "screening-1",
        "d" * 64, "e" * 64,
    ).finalized()
    repository = IntakeRepository(
        manifest, (admission(manifest, "semantic-source"),),
    )

    ingestion = pipeline(tmp_path, repository)
    derived, snapshot = ingestion.semantic_reextract(manifest.extraction_id)
    retried, retried_snapshot = ingestion.semantic_reextract(
        manifest.extraction_id
    )

    assert derived.verify() and snapshot.exists()
    assert retried == derived and retried_snapshot == snapshot
    assert repository.derived_manifests[derived.extraction_id] == derived
    assert all(
        item.review_state is ExtractionReviewState.PROVISIONAL
        for item in derived.objects
    )
    assert {
        item.object_type for item in derived.objects
    } >= {
        ScientificObjectType.POPULATION,
        ScientificObjectType.VARIABLE,
        ScientificObjectType.MEASUREMENT,
        ScientificObjectType.LIMITATION,
    }
