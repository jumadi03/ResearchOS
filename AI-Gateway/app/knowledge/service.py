"""Application service wiring SK-001A infrastructure and domain pipeline."""

from dataclasses import asdict
from pathlib import Path

from app.knowledge.discovery.providers import LiteratureProvider
from app.knowledge.models import DiscoveryRun, ScientificQuestion, SearchPlan
from app.knowledge.ingestion.models import DocumentCandidate
from app.knowledge.theory.builder import TheoryBuilder
from app.knowledge.theory.models import TheoryReviewState
from app.knowledge.theory.persistence import TheoryBundleStore
from app.knowledge.gaps.detector import ResearchGapDetector
from app.knowledge.gaps.persistence import GapAnalysisStore
from app.knowledge.validation.engine import ValidationEngine
from app.knowledge.validation.models import RiskOfBias
from app.knowledge.validation.persistence import ValidationReportStore
from app.knowledge.publication.engine import PublicationEngine
from app.knowledge.publication.models import PublicationKind
from app.knowledge.publication.persistence import PublicationStore
from app.knowledge.repository_service import KnowledgeRepositoryService
from app.knowledge.ingestion_pipeline import KnowledgeIngestionPipeline


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
        self.theory_builder = TheoryBuilder()
        self.theory_store = TheoryBundleStore(output_root / "theories")
        self._graphs = self.ingestion_pipeline.graphs
        self._theory_bundles = {}
        self.gap_detector = ResearchGapDetector()
        self.gap_store = GapAnalysisStore(output_root / "gaps")
        self.validation_engine = ValidationEngine()
        self.validation_store = ValidationReportStore(output_root / "validations")
        self.publication_engine = PublicationEngine()
        self.publication_store = PublicationStore(output_root / "publications")
        self._validation_reports = {}

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
        missing = [item for item in graph_ids if item not in self._graphs]
        if missing:
            raise KeyError(f"Unknown knowledge graph: {missing[0]}")
        bundle = self.theory_builder.build(
            tuple(self._graphs[item] for item in graph_ids),
            created_at=DiscoveryRun.timestamp(),
        )
        self._theory_bundles[bundle.bundle_id] = bundle
        if self.data_repository is not None:
            self.data_repository.persist_artifact(
                artifact_id=bundle.bundle_id, project_id=bundle.bundle_id,
                artifact_type="theory_bundle", title="Scientific theory bundle",
                status="draft", metadata=asdict(bundle), actor_id=generated_by,
                occurred_at=bundle.created_at,
            )
        return bundle, self.theory_store.save(bundle)

    def review_theory(self, bundle_id, *, theory_id, decision, reviewer, rationale, occurred_at):
        bundle = self._theory_bundles.get(bundle_id)
        if bundle is None:
            raise KeyError(f"Unknown theory bundle: {bundle_id}")
        reviewed = self.theory_builder.review(
            bundle, theory_id=theory_id, decision=TheoryReviewState(decision),
            reviewer=reviewer, rationale=rationale, occurred_at=occurred_at,
        )
        self._theory_bundles[bundle_id] = reviewed
        return reviewed, self.theory_store.save(reviewed)

    def detect_research_gaps(self, bundle_id: str, *, generated_by: str = "researchos"):
        bundle = self._theory_bundles.get(bundle_id)
        if bundle is None:
            raise KeyError(f"Unknown theory bundle: {bundle_id}")
        analysis = self.gap_detector.analyze(bundle, created_at=DiscoveryRun.timestamp())
        if self.data_repository is not None:
            self.data_repository.persist_artifact(
                artifact_id=analysis.analysis_id, project_id=bundle_id,
                artifact_type="gap_analysis", title="Research gap analysis",
                status="draft", metadata=asdict(analysis), actor_id=generated_by,
                occurred_at=analysis.created_at,
            )
        return analysis, self.gap_store.save(analysis)

    def validate_theories(self, bundle_id, *, assessed_at, search_completed_at, max_age_days, risk_of_bias_by_theory, reviewer):
        bundle = self._theory_bundles.get(bundle_id)
        if bundle is None: raise KeyError(f"Unknown theory bundle: {bundle_id}")
        report = self.validation_engine.validate(
            bundle, assessed_at=assessed_at, search_completed_at=search_completed_at,
            max_age_days=max_age_days,
            bias_by_theory={key: RiskOfBias(value) for key, value in risk_of_bias_by_theory.items()},
            reviewer=reviewer,
        )
        self._validation_reports[report.report_id] = report
        if self.data_repository is not None:
            self.data_repository.persist_artifact(
                artifact_id=report.report_id, project_id=bundle_id,
                artifact_type="validation_report", title="Theory validation report",
                status="validated", metadata=asdict(report), actor_id=reviewer,
                occurred_at=report.assessed_at,
            )
        return report, self.validation_store.save(report)

    def publish(self, bundle_id, *, validation_report_id, kind, generated_at, generated_by):
        bundle = self._theory_bundles.get(bundle_id)
        if bundle is None: raise KeyError(f"Unknown theory bundle: {bundle_id}")
        report = self._validation_reports.get(validation_report_id)
        if report is None: raise KeyError(f"Unknown validation report: {validation_report_id}")
        package = self.publication_engine.publish(
            bundle, report, kind=PublicationKind(kind), generated_at=generated_at,
            generated_by=generated_by,
        )
        if self.data_repository is not None:
            self.data_repository.persist_artifact(
                artifact_id=package.manifest.publication_id, project_id=bundle_id,
                artifact_type="publication_package",
                title=package.manifest.kind.value.replace("_", " ").title(),
                status="published", metadata=asdict(package), actor_id=generated_by,
                occurred_at=generated_at,
            )
        if self.object_store is not None:
            if self.data_repository is None:
                raise RuntimeError("Publication object storage requires canonical repository")
            markdown = package.markdown.encode("utf-8")
            storage_uri = self.object_store.put_bytes(
                markdown, media_type="text/markdown",
                checksum_sha256=package.manifest.markdown_hash,
                extension="md", namespace="publications",
            )
            self.data_repository.persist_publication_representation(
                package.manifest.publication_id, storage_uri=storage_uri,
                media_type="text/markdown",
                checksum_sha256=package.manifest.markdown_hash,
                file_size=len(markdown), representation_type="markdown",
                edition_type="canonical", published_at=generated_at,
            )
        return package, self.publication_store.save(package)

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

