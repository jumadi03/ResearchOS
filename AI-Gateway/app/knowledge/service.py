"""Application service wiring SK-001A infrastructure and domain pipeline."""

from pathlib import Path

from app.knowledge.discovery.providers import LiteratureProvider
from app.knowledge.models import DiscoveryRun, ScientificQuestion, SearchPlan
from app.knowledge.ingestion.models import DocumentCandidate
from app.knowledge.repository_service import KnowledgeRepositoryService
from app.knowledge.ingestion_pipeline import KnowledgeIngestionPipeline
from app.knowledge.theory_pipeline import KnowledgeTheoryPipeline


class KnowledgeDiscoveryService:
    def __init__(
        self, providers: tuple[LiteratureProvider, ...], output_root: Path,
        *, document_acquirer=None, data_repository=None, object_store=None,
    ) -> None:
        self.output_root = output_root
        self.data_repository = data_repository
        self.repository_service = KnowledgeRepositoryService(data_repository)
        self.object_store = object_store
        self.ingestion_pipeline = KnowledgeIngestionPipeline(
            providers, output_root, document_acquirer=document_acquirer,
            data_repository=data_repository, object_store=object_store,
        )
        self.document_registry = self.ingestion_pipeline.document_registry
        self._graphs = self.ingestion_pipeline.graphs
        self.theory_pipeline = KnowledgeTheoryPipeline(
            output_root, self._graphs, data_repository=data_repository,
            object_store=object_store,
        )

    def discover(self, question: ScientificQuestion, plan: SearchPlan):
        return self.ingestion_pipeline.discover(question, plan)

    def collect_metadata(self, run_id: str):
        return self.ingestion_pipeline.collect_metadata(run_id)

    def acquire_document(self, run_id: str, candidate: DocumentCandidate):
        return self.ingestion_pipeline.acquire_document(run_id, candidate)

    def extract_document(self, document_id: str):
        return self.ingestion_pipeline.extract_document(document_id)

    def build_knowledge_graph(self, extraction_id: str):
        return self.ingestion_pipeline.build_knowledge_graph(extraction_id)

    def review_evidence(
        self, evidence_object_id: str, *, decision: str, reviewer: str,
        rationale: str, occurred_at: str,
    ):
        return self.repository_service.review_evidence(
            evidence_object_id, decision=decision, reviewer=reviewer,
            rationale=rationale, occurred_at=occurred_at,
        )

    def build_theories(self, graph_ids: tuple[str, ...], *, generated_by: str = "researchos"):
        return self.theory_pipeline.build_theories(
            graph_ids, generated_by=generated_by
        )

    def review_theory(self, bundle_id, **options):
        return self.theory_pipeline.review_theory(bundle_id, **options)

    def align_theories(self, bundle_id, **options):
        return self.theory_pipeline.align_theories(bundle_id, **options)

    def alignment_candidates(self, bundle_id):
        return self.theory_pipeline.alignment_candidates(bundle_id)

    def list_theory_bundles(self):
        return self.theory_pipeline.list_theory_bundles()

    def detect_research_gaps(self, bundle_id: str, *, generated_by: str = "researchos"):
        return self.theory_pipeline.detect_research_gaps(
            bundle_id, generated_by=generated_by
        )

    def validate_theories(self, bundle_id, **options):
        return self.theory_pipeline.validate_theories(bundle_id, **options)

    def publish(self, bundle_id, **options):
        return self.theory_pipeline.publish(bundle_id, **options)

    def transition_artifact(
        self, artifact_id: str, *, to_status: str, actor_id: str,
        rationale: str, occurred_at: str,
    ):
        return self.repository_service.transition_artifact(
            artifact_id, to_status=to_status, actor_id=actor_id,
            rationale=rationale, occurred_at=occurred_at,
        )

    def enqueue_semantic_index(
        self, *, object_type: str, object_id: str, model: str,
        embedding: tuple[float, ...], metadata: dict,
    ):
        return self.repository_service.enqueue_semantic_index(
            object_type=object_type, object_id=object_id, model=model,
            embedding=embedding, metadata=metadata,
        )

    def semantic_search(
        self, *, model: str, query_embedding: tuple[float, ...], limit: int,
        object_types: tuple[str, ...],
    ):
        return self.repository_service.semantic_search(
            model=model, query_embedding=query_embedding, limit=limit,
            object_types=object_types,
        )

    def list_projects(self):
        return self.repository_service.list_projects()

    def list_objects(
        self, project_id: str, *, limit: int = 50, cursor: str | None = None,
        query: str | None = None, object_types: tuple[str, ...] = (),
    ):
        return self.repository_service.list_objects(
            project_id, limit=limit, cursor=cursor, query=query,
            object_types=object_types,
        )

    def get_object_read_model(self, object_ref: str, project_id: str, principal):
        return self.repository_service.get_object_read_model(
            object_ref, project_id, principal
        )

    def get_work_queue(self, project_id: str, principal):
        return self.repository_service.get_work_queue(project_id, principal)

    def get_project_graph(
        self, project_id: str, *, limit: int = 100,
        relationship_types: tuple[str, ...] = (), review_status: str | None = None,
        min_confidence: float = 0.0,
    ):
        return self.repository_service.get_project_graph(
            project_id, limit=limit, relationship_types=relationship_types,
            review_status=review_status, min_confidence=min_confidence,
        )
