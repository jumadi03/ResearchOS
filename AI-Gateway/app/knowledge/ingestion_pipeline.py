"""Discovery through canonical graph ingestion orchestration."""

from hashlib import sha256
from pathlib import Path

from app.knowledge.discovery.cache import CachedProvider
from app.knowledge.discovery.engine import LiteratureDiscoveryEngine
from app.knowledge.discovery.persistence import DiscoverySnapshotStore, RawPageStore
from app.knowledge.discovery.providers import LiteratureProvider
from app.knowledge.discovery.source_registry import CanonicalSourceRegistry
from app.knowledge.extraction.engine import EvidenceExtractionEngine
from app.knowledge.extraction.persistence import ExtractionManifestStore
from app.knowledge.ingestion.acquisition import (
    DocumentAcquirer, bind_candidate_to_source,
)
from app.knowledge.ingestion.models import DocumentCandidate
from app.knowledge.ingestion.registry import DocumentRegistry
from app.knowledge.inspection.engine import SourceInspectionEngine
from app.knowledge.inspection.persistence import SourceInspectionStore
from app.knowledge.screening.engine import ScientificScreeningEngine
from app.knowledge.screening.persistence import ScreeningDecisionStore
from app.knowledge.modeling.graph_builder import ScientificKnowledgeGraphBuilder
from app.knowledge.modeling.persistence import KnowledgeGraphStore
from app.knowledge.intake.models import (
    KnowledgeIntakeDecision, KnowledgeIntakeManifest,
)
from app.knowledge.intake.persistence import KnowledgeIntakeStore
from app.knowledge.models import (
    DiscoveryContract, DiscoveryRun, ScientificQuestion, SearchPlan,
)
from app.knowledge.retrieval.collector import MetadataCollector
from app.knowledge.retrieval.persistence import MetadataSnapshotStore
from app.knowledge.retrieval.snowballing import (
    CitationDirection, CitationSnowballingEngine,
)
from app.knowledge.retrieval.snowballing_persistence import (
    CitationTraversalSnapshotStore,
)


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
        self.citation_engine = CitationSnowballingEngine(providers)
        self.citation_snapshots = CitationTraversalSnapshotStore(
            output_root / "runs"
        )
        self.data_repository = data_repository
        self.object_store = object_store
        self.document_acquirer = document_acquirer or DocumentAcquirer()
        self.document_registry = DocumentRegistry(output_root / "documents")
        self.inspection_engine = SourceInspectionEngine()
        self.inspection_store = SourceInspectionStore(output_root / "inspections")
        self.screening_engine = ScientificScreeningEngine()
        self.screening_store = ScreeningDecisionStore(output_root / "screenings")
        self.extraction_engine = EvidenceExtractionEngine()
        self.extraction_store = ExtractionManifestStore(output_root / "extractions")
        self.graph_builder = ScientificKnowledgeGraphBuilder()
        self.graph_store = KnowledgeGraphStore(output_root / "graphs")
        self.intake_store = KnowledgeIntakeStore(output_root / "intakes")
        self.runs: dict[str, DiscoveryRun] = {}
        self.extractions = {}
        self.inspections = {}
        self.screening_decisions = {}
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

    def traverse_citations(
        self, run_id: str, *, seed_record_id: str,
        directions: tuple[CitationDirection, ...], maximum_depth: int,
        retrieval_budget: int,
    ):
        run = self.runs.get(run_id)
        if run is None:
            raise KeyError(f"Unknown discovery run: {run_id}")
        traversal = self.citation_engine.traverse(
            run, seed_record_id=seed_record_id, directions=directions,
            maximum_depth=maximum_depth, retrieval_budget=retrieval_budget,
            created_at=DiscoveryRun.timestamp(),
        )
        if self.data_repository is not None:
            self.data_repository.persist_citation_traversal(traversal)
        return traversal, self.citation_snapshots.save(traversal)

    def acquire_document(self, run_id: str, candidate: DocumentCandidate):
        run = self.runs.get(run_id)
        if run is None:
            raise KeyError(f"Unknown discovery run: {run_id}")
        record = next(
            (item for item in run.records if item.record_id == candidate.record_id), None
        )
        if record is None:
            raise ValueError("record_id does not belong to discovery run")
        source = next((
            source for source in record.source_records
            if source.provider == candidate.source_provider
            and source.response_hash == candidate.source_response_hash
        ), None)
        if source is None:
            raise ValueError("Document candidate provenance does not match discovery run")
        candidate = bind_candidate_to_source(candidate, source)
        result = self.document_acquirer.acquire(
            candidate, acquired_at=DiscoveryRun.timestamp()
        )
        storage_uri = None
        if result.content is not None and self.object_store is not None:
            if self.data_repository is None:
                raise RuntimeError("Object storage requires a canonical data repository")
            storage_uri = self.object_store.put(result)
            self.object_store.verify_capture(result, storage_uri)
            self.data_repository.persist_representation(record, result, storage_uri)
        return self.document_registry.register(result, storage_uri=storage_uri)

    def _verified_document_content(self, document_id: str):
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
        return document, record, content

    def inspect_document(self, document_id: str):
        document, record, content = self._verified_document_content(document_id)
        existing = self.inspection_store.find(
            document.document_id, document.content_hash or "",
            self.inspection_engine.inspector_name,
            self.inspection_engine.inspector_version,
        )
        if existing is not None:
            self.inspections[existing.inspection_id] = existing
            return existing, self.inspection_store.save(existing)
        inspection = self.inspection_engine.inspect(
            document, content, inspected_at=DiscoveryRun.timestamp(),
        )
        if self.data_repository is not None and self.object_store is not None:
            self.data_repository.persist_source_inspection(record, inspection)
        self.inspections[inspection.inspection_id] = inspection
        return inspection, self.inspection_store.save(inspection)

    def extract_document(self, document_id: str):
        inspection = next((
            item for item in self.inspections.values()
            if item.document_id == document_id
        ), None)
        if inspection is None:
            inspection, _ = self.inspect_document(document_id)
        document, record, content = self._verified_document_content(document_id)
        decision = self.screening_store.find_eligible(
            document_id, document.content_hash or "", inspection.manifest_hash,
        )
        if decision is None:
            raise ValueError("Eligible screening decision is required for evidence extraction")
        if self.data_repository is not None and self.object_store is not None:
            self.data_repository.validate_screening_decision(decision)
        manifest = self.extraction_engine.extract(
            document, content, created_at=DiscoveryRun.timestamp(),
            inspection=inspection, screening_decision=decision,
        )
        if self.data_repository is not None and self.object_store is not None:
            self.data_repository.persist_evidence(record, manifest)
        self.extractions[manifest.extraction_id] = manifest
        return manifest, self.extraction_store.save(manifest)

    def screen_document(self, document_id: str):
        inspection = next((
            item for item in self.inspections.values()
            if item.document_id == document_id
        ), None)
        if inspection is None:
            inspection, _ = self.inspect_document(document_id)
        document, record, _ = self._verified_document_content(document_id)
        run = next((
            run for run in self.runs.values()
            if any(item.record_id == document.record_id for item in run.records)
        ), None)
        if run is not None and record is None:
            record = next(
                item for item in run.records
                if item.record_id == document.record_id
            )
        if run is None or record is None:
            raise ValueError("Discovery contract provenance is required for screening")
        decision = self.screening_engine.screen(
            record, document, inspection, run.discovery_contract,
            decided_at=DiscoveryRun.timestamp(),
        )
        if self.data_repository is not None and self.object_store is not None:
            self.data_repository.persist_screening_decision(record, decision)
        self.screening_decisions[decision.decision_id] = decision
        return decision, self.screening_store.save(decision)

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

    def intake_accepted_evidence(
        self, extraction_id: str, *, evidence_object_ids: tuple[str, ...],
        actor_id: str, occurred_at: str,
    ):
        if self.data_repository is None:
            raise ValueError(
                "Canonical repository is required for knowledge intake"
            )
        manifest = self.data_repository.load_extraction_manifest(extraction_id)
        manifest_ids = tuple(sorted(item.object_id for item in manifest.objects))
        requested_ids = tuple(sorted(set(evidence_object_ids or manifest_ids)))
        if not requested_ids:
            raise ValueError("Knowledge intake requires at least one evidence object")
        unknown = sorted(set(requested_ids) - set(manifest_ids))
        if unknown:
            raise ValueError(
                "Evidence does not belong to extraction manifest: "
                + ", ".join(unknown)
            )
        admissions = self.data_repository.resolve_evidence_admissions(requested_ids)
        admitted_ids = []
        decisions = []
        for object_id in requested_ids:
            try:
                accepted = self.graph_builder.admission_gate.admit(
                    manifest, admissions, (object_id,),
                )
            except ValueError as exc:
                decisions.append(KnowledgeIntakeDecision(
                    object_id, False, str(exc),
                ))
            else:
                admitted_ids.append(object_id)
                decisions.append(KnowledgeIntakeDecision(
                    object_id, True, "Accepted human review verified",
                    accepted[object_id].provenance_id,
                ))
        if not admitted_ids:
            reasons = "; ".join(
                f"{item.evidence_object_id}: {item.reason}" for item in decisions
            )
            raise ValueError(f"Knowledge intake admitted no evidence: {reasons}")
        admitted = tuple(admitted_ids)
        graph = self.graph_builder.build(manifest, admissions, admitted)
        identity = (
            f"{manifest.extraction_id}:{manifest.manifest_hash}:"
            f"{','.join(requested_ids)}:{actor_id}:{occurred_at}"
        )
        intake = KnowledgeIntakeManifest(
            f"intake-{sha256(identity.encode()).hexdigest()[:24]}",
            manifest.extraction_id, manifest.manifest_hash,
            graph.graph_id, graph.content_hash, requested_ids, admitted,
            tuple(decisions), actor_id, occurred_at,
        ).finalized()
        self.data_repository.persist_graph(
            graph, occurred_at=occurred_at, intake=intake,
        )
        self.graphs[graph.graph_id] = graph
        graph_snapshot = self.graph_store.save(graph)
        intake_snapshot = self.intake_store.save(intake)
        return intake, graph, intake_snapshot, graph_snapshot
