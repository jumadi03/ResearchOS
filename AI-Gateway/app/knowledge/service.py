"""Application service wiring SK-001A infrastructure and domain pipeline."""

from dataclasses import asdict
from pathlib import Path

from app.knowledge.discovery.cache import CachedProvider
from app.knowledge.discovery.engine import LiteratureDiscoveryEngine
from app.knowledge.discovery.persistence import DiscoverySnapshotStore, RawPageStore
from app.knowledge.discovery.providers import LiteratureProvider
from app.knowledge.models import DiscoveryRun, ScientificQuestion, SearchPlan
from app.knowledge.retrieval.collector import MetadataCollector
from app.knowledge.retrieval.persistence import MetadataSnapshotStore
from app.knowledge.ingestion.acquisition import DocumentAcquirer
from app.knowledge.ingestion.models import DocumentCandidate
from app.knowledge.ingestion.registry import DocumentRegistry
from app.knowledge.extraction.engine import EvidenceExtractionEngine
from app.knowledge.extraction.persistence import ExtractionManifestStore
from app.knowledge.modeling.graph_builder import ScientificKnowledgeGraphBuilder
from app.knowledge.modeling.persistence import KnowledgeGraphStore
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
from app.knowledge.authentication import KnowledgeRole


class KnowledgeDiscoveryService:
    def __init__(
        self, providers: tuple[LiteratureProvider, ...], output_root: Path,
        *, document_acquirer=None, data_repository=None, object_store=None,
    ) -> None:
        self.output_root = output_root
        cached = tuple(CachedProvider(provider, output_root / "cache") for provider in providers)
        self.engine = LiteratureDiscoveryEngine(
            cached, raw_page_store=RawPageStore(output_root / "runs")
        )
        self.snapshots = DiscoverySnapshotStore(output_root / "runs")
        self.metadata_snapshots = MetadataSnapshotStore(output_root / "runs")
        self.metadata_collector = MetadataCollector()
        self._runs: dict[str, DiscoveryRun] = {}
        self.data_repository = data_repository
        self.object_store = object_store
        self.document_acquirer = document_acquirer or DocumentAcquirer()
        self.document_registry = DocumentRegistry(output_root / "documents")
        self.extraction_engine = EvidenceExtractionEngine()
        self.extraction_store = ExtractionManifestStore(output_root / "extractions")
        self.graph_builder = ScientificKnowledgeGraphBuilder()
        self.graph_store = KnowledgeGraphStore(output_root / "graphs")
        self._extractions = {}
        self.theory_builder = TheoryBuilder()
        self.theory_store = TheoryBundleStore(output_root / "theories")
        self._graphs = {}
        self._theory_bundles = {}
        self.gap_detector = ResearchGapDetector()
        self.gap_store = GapAnalysisStore(output_root / "gaps")
        self.validation_engine = ValidationEngine()
        self.validation_store = ValidationReportStore(output_root / "validations")
        self.publication_engine = PublicationEngine()
        self.publication_store = PublicationStore(output_root / "publications")
        self._validation_reports = {}

    def discover(self, question: ScientificQuestion, plan: SearchPlan) -> tuple[DiscoveryRun, Path]:
        run = self.engine.discover(question, plan)
        if self.data_repository is not None:
            self.data_repository.persist_discovery(run)
        self._runs[run.run_id] = run
        return run, self.snapshots.save(run)

    def collect_metadata(self, run_id: str):
        run = self._runs.get(run_id)
        if run is None:
            raise KeyError(f"Unknown discovery run: {run_id}")
        metadata = self.metadata_collector.collect(run, created_at=DiscoveryRun.timestamp())
        if self.data_repository is not None:
            self.data_repository.persist_metadata(metadata)
        return metadata, self.metadata_snapshots.save(metadata)

    def acquire_document(self, run_id: str, candidate: DocumentCandidate):
        run = self._runs.get(run_id)
        if run is None:
            raise KeyError(f"Unknown discovery run: {run_id}")
        record = next((item for item in run.records if item.record_id == candidate.record_id), None)
        if record is None:
            raise ValueError("record_id does not belong to discovery run")
        provenance = any(
            source.provider == candidate.source_provider
            and source.response_hash == candidate.source_response_hash
            for source in record.source_records
        )
        if not provenance:
            raise ValueError("Document candidate provenance does not match discovery run")
        result = self.document_acquirer.acquire(candidate, acquired_at=DiscoveryRun.timestamp())
        registered = self.document_registry.register(result)
        if result.content is not None and self.object_store is not None:
            if self.data_repository is None:
                raise RuntimeError("Object storage requires a canonical data repository")
            storage_uri = self.object_store.put(result)
            self.data_repository.persist_representation(record, result, storage_uri)
        return registered

    def extract_document(self, document_id: str):
        document = self.document_registry.get(document_id)
        if self.object_store is not None:
            if self.data_repository is None or not document.content_hash:
                raise RuntimeError("Canonical repository is required for object retrieval")
            record = next(
                (record for run in self._runs.values() for record in run.records
                 if record.record_id == document.record_id),
                None,
            )
            if record is None:
                raise KeyError(f"Discovery record missing for document: {document_id}")
            representation = self.data_repository.get_representation(
                record, document.content_hash,
            )
            content = self.object_store.read_verified(representation)
        else:
            content = self.document_registry.read_verified_content(document)
        manifest = self.extraction_engine.extract(
            document, content, created_at=DiscoveryRun.timestamp()
        )
        if self.data_repository is not None and self.object_store is not None:
            self.data_repository.persist_evidence(record, manifest)
        self._extractions[manifest.extraction_id] = manifest
        return manifest, self.extraction_store.save(manifest)

    def build_knowledge_graph(self, extraction_id: str):
        manifest = self._extractions.get(extraction_id)
        if manifest is None:
            raise KeyError(f"Unknown extraction manifest: {extraction_id}")
        graph = self.graph_builder.build(manifest)
        if self.data_repository is not None and self.object_store is not None:
            self.data_repository.persist_graph(graph, occurred_at=manifest.created_at)
        self._graphs[graph.graph_id] = graph
        return graph, self.graph_store.save(graph)

    def review_evidence(
        self, evidence_object_id: str, *, decision: str, reviewer: str,
        rationale: str, occurred_at: str,
    ):
        if self.data_repository is None:
            raise RuntimeError("Canonical repository is required for evidence review")
        return self.data_repository.review_evidence(
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
        if self.data_repository is None:
            raise RuntimeError("Canonical repository is required for artifact lifecycle")
        return self.data_repository.transition_artifact(
            artifact_id, to_status=to_status, actor_id=actor_id,
            rationale=rationale, occurred_at=occurred_at,
        )

    def enqueue_semantic_index(
        self, *, object_type: str, object_id: str, model: str,
        embedding: tuple[float, ...], metadata: dict,
    ):
        if self.data_repository is None:
            raise RuntimeError("Canonical repository is required for semantic indexing")
        return self.data_repository.enqueue_semantic_index(
            object_type=object_type, object_id=object_id, model=model,
            embedding=embedding, metadata=metadata,
        )

    def semantic_search(
        self, *, model: str, query_embedding: tuple[float, ...], limit: int,
        object_types: tuple[str, ...],
    ):
        if self.data_repository is None:
            raise RuntimeError("Canonical repository is required for semantic retrieval")
        return self.data_repository.semantic_search(
            model=model, query_embedding=query_embedding, limit=limit,
            object_types=object_types,
        )

    def list_projects(self):
        if self.data_repository is None:
            raise RuntimeError("Canonical repository is required for product reads")
        return self.data_repository.list_projects()

    def list_objects(
        self, project_id: str, *, limit: int = 50, cursor: str | None = None,
        query: str | None = None, object_types: tuple[str, ...] = (),
    ):
        if self.data_repository is None:
            raise RuntimeError("Canonical repository is required for product reads")
        return self.data_repository.list_objects(
            project_id, limit=limit, cursor=cursor, query=query,
            object_types=object_types,
        )

    def get_object_read_model(self, object_ref: str, project_id: str, principal):
        if self.data_repository is None:
            raise RuntimeError("Canonical repository is required for product reads")
        result = self.data_repository.get_object_read_model(object_ref, project_id)
        actions = []
        evidence = result.get("evidence")
        artifact = result.get("artifact")
        if evidence and evidence.get("review_status") == "pending" and principal.has_role(KnowledgeRole.REVIEWER):
            actions.extend((
                {"action": "evidence:accept", "method": "POST", "href": f"/knowledge/evidence/{result['identity']['object_id']}/reviews"},
                {"action": "evidence:reject", "method": "POST", "href": f"/knowledge/evidence/{result['identity']['object_id']}/reviews"},
            ))
        if evidence and evidence.get("review_status") == "accepted" and principal.has_role(KnowledgeRole.INDEXER):
            actions.append({"action": "semantic:index", "method": "POST", "href": "/knowledge/semantic-index/jobs"})
        if artifact:
            transitions = {"draft": "validated", "validated": "ratified", "ratified": "published"}
            next_status = transitions.get(artifact.get("status"))
            if next_status and principal.has_role(KnowledgeRole.REVIEWER):
                actions.append({
                    "action": "artifact:transition", "method": "POST",
                    "href": f"/knowledge/artifacts/{result['identity']['object_id']}/transitions",
                    "to_status": next_status,
                })
            if artifact.get("status") in {"validated", "ratified", "published"} and principal.has_role(KnowledgeRole.INDEXER):
                actions.append({"action": "semantic:index", "method": "POST", "href": "/knowledge/semantic-index/jobs"})
        result["permissions"] = {
            "can_read": True,
            "roles": sorted(role.value for role in principal.roles),
            "available_actions": actions,
        }
        return result

    def get_work_queue(self, project_id: str, principal):
        if self.data_repository is None:
            raise RuntimeError("Canonical repository is required for workflow reads")
        queue = self.data_repository.get_work_queue(project_id)
        queue["permissions"] = {
            "can_review": principal.has_role(KnowledgeRole.REVIEWER),
            "can_index": principal.has_role(KnowledgeRole.INDEXER),
            "roles": sorted(role.value for role in principal.roles),
        }
        return queue

    def get_project_graph(
        self, project_id: str, *, limit: int = 100,
        relationship_types: tuple[str, ...] = (), review_status: str | None = None,
        min_confidence: float = 0.0,
    ):
        if self.data_repository is None:
            raise RuntimeError("Canonical repository is required for graph reads")
        return self.data_repository.get_project_graph(
            project_id, limit=limit, relationship_types=relationship_types,
            review_status=review_status, min_confidence=min_confidence,
        )
