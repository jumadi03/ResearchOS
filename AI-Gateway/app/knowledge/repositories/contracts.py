"""Persistence ports owned by the Scientific Knowledge application layer."""

from typing import Protocol

from app.knowledge.models import DiscoveryRun, LiteratureRecord
from app.knowledge.ingestion.models import AcquisitionResult
from app.knowledge.inspection.models import SourceInspection
from app.knowledge.screening.models import ScreeningDecision
from app.knowledge.retrieval.models import MetadataRun
from app.knowledge.retrieval.snowballing import CitationTraversalRun
from app.knowledge.repositories.models import StoredRepresentation
from app.knowledge.extraction.models import (
    EvidenceAdmission, EvidenceReviewAssessment, EvidenceReviewEvent, ExtractionManifest,
)
from app.knowledge.modeling.models import ScientificKnowledgeGraph
from app.knowledge.monitoring.models import MonitoringRun, ScientificSourceWatch
from app.knowledge.intake.models import KnowledgeIntakeManifest
from app.knowledge.repositories.artifacts import ArtifactLifecycleEvent
from app.knowledge.repositories.semantic import SemanticIndexJob, SemanticSearchHit
from app.knowledge.repositories.read_models import ObjectPage, ProjectSummary


class ScientificDataRepository(Protocol):
    """Persist canonical data without leaking storage technology to domain code."""

    def persist_discovery(self, run: DiscoveryRun) -> None: ...

    def persist_metadata(self, run: MetadataRun) -> None: ...

    def persist_citation_traversal(
        self, run: CitationTraversalRun,
    ) -> None: ...

    def create_source_watch(
        self, baseline: DiscoveryRun, **options,
    ) -> ScientificSourceWatch: ...

    def load_source_watch(
        self, watch_id: str,
    ) -> tuple[ScientificSourceWatch, DiscoveryRun]: ...

    def list_source_watches(
        self, project_id: str,
    ) -> tuple[ScientificSourceWatch, ...]: ...

    def transition_source_watch(self, watch_id: str, **options): ...

    def list_monitoring_runs(self, watch_id: str) -> tuple[dict, ...]: ...

    def list_scientific_changes(
        self, watch_id: str, **options,
    ) -> tuple[dict, ...]: ...

    def persist_monitoring_run(
        self, watch: ScientificSourceWatch, run: MonitoringRun,
        current: DiscoveryRun,
    ) -> None: ...

    def acknowledge_scientific_change(
        self, change_id: str, **options,
    ) -> str: ...

    def resolve_impact_review(self, change_id: str, **options): ...

    def select_follow_up_target(self, resolution_id: str, **options): ...

    def persist_representation(
        self, record: LiteratureRecord, result: AcquisitionResult, storage_uri: str,
    ) -> tuple[str, int]: ...

    def get_representation(
        self, record: LiteratureRecord, checksum_sha256: str,
    ) -> StoredRepresentation: ...

    def persist_source_inspection(
        self, record: LiteratureRecord, inspection: SourceInspection,
    ) -> str: ...

    def persist_screening_decision(
        self, record: LiteratureRecord, decision: ScreeningDecision,
    ) -> str: ...

    def validate_screening_decision(self, decision: ScreeningDecision) -> None: ...

    def persist_evidence(
        self, record: LiteratureRecord | None, manifest: ExtractionManifest,
        *, source_extraction_id: str | None = None,
    ) -> tuple[str, ...]: ...

    def load_extraction_manifest(self, extraction_id: str) -> ExtractionManifest: ...

    def review_evidence(
        self, evidence_object_id: str, *, decision: str, reviewer: str,
        rationale: str, occurred_at: str, assessment: EvidenceReviewAssessment,
    ) -> EvidenceReviewEvent: ...

    def resolve_evidence_admissions(
        self, evidence_object_ids: tuple[str, ...],
    ) -> tuple[EvidenceAdmission, ...]: ...

    def persist_graph(
        self, graph: ScientificKnowledgeGraph, *, occurred_at: str,
        intake: KnowledgeIntakeManifest | None = None,
    ) -> tuple[str, ...]: ...

    def persist_artifact(
        self, *, artifact_id: str, project_id: str, artifact_type: str,
        title: str, status: str, metadata: dict, actor_id: str,
        occurred_at: str,
    ) -> ArtifactLifecycleEvent: ...

    def transition_artifact(
        self, artifact_id: str, *, to_status: str, actor_id: str,
        rationale: str, occurred_at: str,
    ) -> ArtifactLifecycleEvent: ...

    def persist_publication_representation(
        self, publication_id: str, *, storage_uri: str, media_type: str,
        checksum_sha256: str, file_size: int, representation_type: str,
        edition_type: str, published_at: str,
    ) -> StoredRepresentation: ...

    def record_publication_relationship(self, relationship): ...

    def enqueue_semantic_index(
        self, *, object_type: str, object_id: str, model: str,
        embedding: tuple[float, ...], metadata: dict,
    ) -> SemanticIndexJob: ...

    def semantic_search(
        self, *, model: str, query_embedding: tuple[float, ...], limit: int,
        object_types: tuple[str, ...],
    ) -> tuple[SemanticSearchHit, ...]: ...

    def list_projects(self) -> tuple[ProjectSummary, ...]: ...

    def list_objects(
        self, project_id: str, *, limit: int, cursor: str | None,
        query: str | None, object_types: tuple[str, ...],
    ) -> ObjectPage: ...

    def get_object_read_model(self, object_ref: str, project_id: str) -> dict: ...

    def get_work_queue(self, project_id: str) -> dict: ...

    def get_project_graph(
        self, project_id: str, *, limit: int, relationship_types: tuple[str, ...],
        review_status: str | None, min_confidence: float,
    ) -> dict: ...


class ScientificObjectStore(Protocol):
    """Store immutable representation bytes and return their durable URI."""

    def put(self, result: AcquisitionResult) -> str: ...

    def read_verified(self, representation: StoredRepresentation) -> bytes: ...

    def put_bytes(
        self, content: bytes, *, media_type: str, checksum_sha256: str,
        extension: str, namespace: str,
    ) -> str: ...
