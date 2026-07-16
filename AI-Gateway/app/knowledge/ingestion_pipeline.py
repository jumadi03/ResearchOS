"""Discovery through canonical graph ingestion orchestration."""

from pathlib import Path

from app.knowledge.discovery.cache import CachedProvider
from app.knowledge.discovery.engine import LiteratureDiscoveryEngine
from app.knowledge.discovery.persistence import DiscoverySnapshotStore, RawPageStore
from app.knowledge.discovery.providers import LiteratureProvider
from app.knowledge.discovery.source_registry import CanonicalSourceRegistry
from app.knowledge.extraction.engine import EvidenceExtractionEngine
from app.knowledge.extraction.persistence import ExtractionManifestStore
from app.knowledge.ingestion.acquisition import DocumentAcquirer
from app.knowledge.ingestion.models import DocumentCandidate
from app.knowledge.ingestion.registry import DocumentRegistry
from app.knowledge.modeling.graph_builder import ScientificKnowledgeGraphBuilder
from app.knowledge.modeling.persistence import KnowledgeGraphStore
from app.knowledge.models import (
    DiscoveryContract, DiscoveryRun, ScientificQuestion, SearchPlan,
)
from app.knowledge.retrieval.collector import MetadataCollector
from app.knowledge.retrieval.persistence import MetadataSnapshotStore


class KnowledgeIngestionPipeline:
    def __init__(
        self, providers: tuple[LiteratureProvider, ...], output_root: Path,
        *, document_acquirer=None, data_repository=None, object_store=None,
    ) -> None:
        source_registry = CanonicalSourceRegistry.for_providers(providers)
        cached = tuple(
            CachedProvider(provider, output_root / "cache") for provider in providers
        )
        self.engine = LiteratureDiscoveryEngine(
            cached, raw_page_store=RawPageStore(output_root / "runs"),
            source_registry=source_registry,
        )
        self.snapshots = DiscoverySnapshotStore(output_root / "runs")
        self.metadata_snapshots = MetadataSnapshotStore(output_root / "runs")
        self.metadata_collector = MetadataCollector()
        self.data_repository = data_repository
        self.object_store = object_store
        self.document_acquirer = document_acquirer or DocumentAcquirer()
        self.document_registry = DocumentRegistry(output_root / "documents")
        self.extraction_engine = EvidenceExtractionEngine()
        self.extraction_store = ExtractionManifestStore(output_root / "extractions")
        self.graph_builder = ScientificKnowledgeGraphBuilder()
        self.graph_store = KnowledgeGraphStore(output_root / "graphs")
        self.runs: dict[str, DiscoveryRun] = {}
        self.extractions = {}
        self.graphs = {}

    def discover(
        self, question: ScientificQuestion, contract: DiscoveryContract,
        plan: SearchPlan,
    ):
        run = self.engine.discover(question, contract, plan)
        if self.data_repository is not None:
            self.data_repository.persist_discovery(run)
        self.runs[run.run_id] = run
        return run, self.snapshots.save(run)

    def collect_metadata(self, run_id: str):
        run = self.runs.get(run_id)
        if run is None:
            raise KeyError(f"Unknown discovery run: {run_id}")
        metadata = self.metadata_collector.collect(
            run, created_at=DiscoveryRun.timestamp()
        )
        if self.data_repository is not None:
            self.data_repository.persist_metadata(metadata)
        return metadata, self.metadata_snapshots.save(metadata)

    def acquire_document(self, run_id: str, candidate: DocumentCandidate):
        run = self.runs.get(run_id)
        if run is None:
            raise KeyError(f"Unknown discovery run: {run_id}")
        record = next(
            (item for item in run.records if item.record_id == candidate.record_id), None
        )
        if record is None:
            raise ValueError("record_id does not belong to discovery run")
        if not any(
            source.provider == candidate.source_provider
            and source.response_hash == candidate.source_response_hash
            for source in record.source_records
        ):
            raise ValueError("Document candidate provenance does not match discovery run")
        result = self.document_acquirer.acquire(
            candidate, acquired_at=DiscoveryRun.timestamp()
        )
        registered = self.document_registry.register(result)
        if result.content is not None and self.object_store is not None:
            if self.data_repository is None:
                raise RuntimeError("Object storage requires a canonical data repository")
            storage_uri = self.object_store.put(result)
            self.data_repository.persist_representation(record, result, storage_uri)
        return registered

    def extract_document(self, document_id: str):
        document = self.document_registry.get(document_id)
        record = None
        if self.object_store is not None:
            if self.data_repository is None or not document.content_hash:
                raise RuntimeError("Canonical repository is required for object retrieval")
            record = next(
                (record for run in self.runs.values() for record in run.records
                 if record.record_id == document.record_id), None,
            )
            if record is None:
                raise KeyError(f"Discovery record missing for document: {document_id}")
            representation = self.data_repository.get_representation(
                record, document.content_hash
            )
            content = self.object_store.read_verified(representation)
        else:
            content = self.document_registry.read_verified_content(document)
        manifest = self.extraction_engine.extract(
            document, content, created_at=DiscoveryRun.timestamp()
        )
        if self.data_repository is not None and self.object_store is not None:
            self.data_repository.persist_evidence(record, manifest)
        self.extractions[manifest.extraction_id] = manifest
        return manifest, self.extraction_store.save(manifest)

    def build_knowledge_graph(self, extraction_id: str):
        manifest = self.extractions.get(extraction_id)
        if manifest is None:
            raise KeyError(f"Unknown extraction manifest: {extraction_id}")
        if self.data_repository is None:
            raise ValueError(
                "Canonical repository is required for evidence admission"
            )
        admissions = self.data_repository.resolve_evidence_admissions(
            tuple(item.object_id for item in manifest.objects)
        )
        graph = self.graph_builder.build(manifest, admissions)
        if self.data_repository is not None:
            self.data_repository.persist_graph(graph, occurred_at=manifest.created_at)
        self.graphs[graph.graph_id] = graph
        return graph, self.graph_store.save(graph)
