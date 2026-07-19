"""Discovery through canonical graph ingestion orchestration."""

from hashlib import sha256
from pathlib import Path

from app.knowledge.discovery.cache import CachedProvider
from app.knowledge.discovery.engine import LiteratureDiscoveryEngine
from app.knowledge.discovery.persistence import DiscoverySnapshotStore, RawPageStore
from app.knowledge.discovery.providers import LiteratureProvider
from app.knowledge.discovery.source_registry import CanonicalSourceRegistry
from app.knowledge.extraction.engine import EvidenceExtractionEngine
from app.knowledge.extraction.models import ExtractionReviewState
from app.knowledge.extraction.persistence import ExtractionManifestStore
from app.knowledge.extraction.semantic_reextraction import (
    SemanticReextractionEngine,
)
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
from app.knowledge.modeling.models import (
    KnowledgeEdgeType, KnowledgeRelationAssertion,
)
from app.knowledge.modeling.persistence import KnowledgeGraphStore
from app.knowledge.modeling.relation_persistence import SemanticRelationStore
from app.knowledge.modeling.relation_review import (
    ADMISSIBLE_SEMANTIC_RELATION_TYPES, SemanticRelation,
    SemanticRelationState,
)
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
        self.semantic_reextraction_engine = SemanticReextractionEngine()
        self.extraction_store = ExtractionManifestStore(output_root / "extractions")
        self.graph_builder = ScientificKnowledgeGraphBuilder()
        self.graph_store = KnowledgeGraphStore(output_root / "graphs")
        self.intake_store = KnowledgeIntakeStore(output_root / "intakes")
        self.relation_store = SemanticRelationStore(
            output_root / "semantic-relations"
        )
        self.runs: dict[str, DiscoveryRun] = {}
        self.extractions = {}
        self.inspections = {}
        self.screening_decisions = {}
        self.graphs = {
            item.graph_id: item for item in self.graph_store.load_all()
        }
        self.semantic_relations = {
            item.relation_id: item for item in self.relation_store.load_all()
        }

    def semantic_reextract(
        self, extraction_id: str, *,
        evidence_object_ids: tuple[str, ...] = (),
    ):
        if self.data_repository is None:
            raise ValueError(
                "Canonical repository is required for semantic re-extraction"
            )
        parent = self.data_repository.load_extraction_manifest(extraction_id)
        parent_ids = tuple(item.object_id for item in parent.objects)
        admissions = self.data_repository.resolve_evidence_admissions(parent_ids)
        requested = (
            tuple(evidence_object_ids)
            if evidence_object_ids else
            tuple(
                item.evidence_object_id for item in admissions
                if item.review_state is ExtractionReviewState.ACCEPTED
            )
        )
        accepted = self.graph_builder.admission_gate.admit(
            parent, admissions, requested,
        )
        admission_times = sorted(
            item.review_event.occurred_at
            for item in admissions
            if (
                item.evidence_object_id in accepted
                and item.review_event is not None
            )
        )
        manifest = self.semantic_reextraction_engine.extract(
            parent, tuple(sorted(accepted)),
            # The latest source-admission event is a stable, meaningful
            # boundary for this deterministic derivation.  Using wall-clock
            # time here would give the same extraction key a different hash
            # when an identical request is safely retried.
            created_at=(
                admission_times[-1] if admission_times else parent.created_at
            ),
        )
        try:
            existing = self.data_repository.load_extraction_manifest(
                manifest.extraction_id
            )
        except KeyError:
            existing = None
        if existing is not None:
            if (
                existing.parser_name != manifest.parser_name
                or existing.parser_version != manifest.parser_version
                or existing.configuration_hash != manifest.configuration_hash
                or tuple(item.object_id for item in existing.objects)
                != tuple(item.object_id for item in manifest.objects)
            ):
                raise RuntimeError(
                    "Semantic re-extraction integrity conflict"
                )
            self.extractions[existing.extraction_id] = existing
            return existing, self.extraction_store.save(existing)
        self.data_repository.persist_evidence(
            None, manifest, source_extraction_id=extraction_id,
        )
        self.extractions[manifest.extraction_id] = manifest
        return manifest, self.extraction_store.save(manifest)

    def propose_semantic_relation(
        self, extraction_id: str, *, source_object_id: str,
        target_object_id: str, edge_type: str, provenance_object_id: str,
        proposed_by: str, rationale: str, proposed_at: str,
    ):
        if self.data_repository is None:
            raise ValueError(
                "Canonical repository is required for semantic relation proposal"
            )
        if source_object_id == target_object_id:
            raise ValueError("Semantic relation cannot be self-referential")
        if not rationale.strip():
            raise ValueError("Semantic relation proposal rationale is required")
        manifest = self.data_repository.load_extraction_manifest(extraction_id)
        manifest_ids = {item.object_id for item in manifest.objects}
        referenced = {
            source_object_id, target_object_id, provenance_object_id,
        }
        missing = sorted(referenced - manifest_ids)
        if missing:
            raise ValueError(
                "Semantic relation evidence does not belong to extraction: "
                f"{missing[0]}"
            )
        admissions = self.data_repository.resolve_evidence_admissions(
            tuple(sorted(referenced))
        )
        self.graph_builder.admission_gate.admit(
            manifest, admissions, tuple(sorted(referenced)),
        )
        relation_type = KnowledgeEdgeType(edge_type)
        if relation_type not in ADMISSIBLE_SEMANTIC_RELATION_TYPES:
            raise ValueError(
                f"Relation type is not an admissible scientific assertion: "
                f"{relation_type.value}"
            )
        identity = (
            f"{extraction_id}:{source_object_id}:{relation_type.value}:"
            f"{target_object_id}:{provenance_object_id}:"
            f"{proposed_by}:{proposed_at}"
        )
        relation = SemanticRelation(
            f"semantic-relation-{sha256(identity.encode()).hexdigest()[:24]}",
            extraction_id, source_object_id, target_object_id, relation_type,
            provenance_object_id, proposed_by, rationale.strip(), proposed_at,
        ).finalized()
        existing = self.semantic_relations.get(relation.relation_id)
        if existing is not None:
            if existing.content_hash != relation.content_hash:
                raise RuntimeError("Semantic relation proposal conflict")
            return existing, self.relation_store.save(existing)
        self.semantic_relations[relation.relation_id] = relation
        return relation, self.relation_store.save(relation)

    def review_semantic_relation(
        self, relation_id: str, *, decision: str, reviewer: str,
        rationale: str, occurred_at: str,
    ):
        relation = self.semantic_relations.get(relation_id)
        if relation is None:
            raise KeyError(f"Unknown semantic relation: {relation_id}")
        if decision == SemanticRelationState.ACCEPTED.value:
            manifest = self.data_repository.load_extraction_manifest(
                relation.extraction_id
            )
            referenced = tuple(sorted({
                relation.source_object_id, relation.target_object_id,
                relation.provenance_object_id,
            }))
            admissions = self.data_repository.resolve_evidence_admissions(
                referenced
            )
            self.graph_builder.admission_gate.admit(
                manifest, admissions, referenced,
            )
        reviewed = relation.review(
            decision=SemanticRelationState(decision), reviewer=reviewer,
            rationale=rationale, occurred_at=occurred_at,
        )
        self.semantic_relations[relation_id] = reviewed
        return reviewed, self.relation_store.save(reviewed)

    def list_semantic_relations(
        self, *, extraction_id: str | None = None,
    ) -> tuple[SemanticRelation, ...]:
        return tuple(sorted(
            (
                item for item in self.semantic_relations.values()
                if extraction_id is None or item.extraction_id == extraction_id
            ),
            key=lambda item: item.relation_id,
        ))

    def relation_dependencies_for_graph(
        self, graph_id: str,
    ) -> tuple[tuple[str, str], ...]:
        return tuple(sorted(
            (
                relation.relation_id, relation.state.value
            )
            for relation in self.semantic_relations.values()
            if any(
                event.graph_id == graph_id for event in relation.admissions
            )
        ))

    def semantic_relation_review_queue(self, extraction_id: str) -> dict:
        if self.data_repository is None:
            raise ValueError(
                "Canonical repository is required for semantic relation queue"
            )
        manifest = self.data_repository.load_extraction_manifest(extraction_id)
        object_ids = tuple(item.object_id for item in manifest.objects)
        admissions = self.data_repository.resolve_evidence_admissions(object_ids)
        admission_by_id = {
            item.evidence_object_id: item for item in admissions
        }
        accepted_objects = tuple(
            item for item in manifest.objects
            if (
                item.object_id in admission_by_id
                and admission_by_id[item.object_id].review_state is
                ExtractionReviewState.ACCEPTED
                and admission_by_id[item.object_id].review_event is not None
            )
        )
        review_context = tuple({
            "object_id": item.object_id,
            "review_state": admission_by_id[item.object_id].review_state.value,
            "review_event": admission_by_id[item.object_id].review_event,
        } for item in accepted_objects)
        object_by_id = {item.object_id: item for item in accepted_objects}
        relations = self.list_semantic_relations(extraction_id=extraction_id)
        proposals = tuple({
            "relation": relation,
            "source": object_by_id.get(relation.source_object_id),
            "target": object_by_id.get(relation.target_object_id),
            "provenance": object_by_id.get(relation.provenance_object_id),
        } for relation in relations)
        required_types = ("population", "variable", "measurement", "limitation")
        present_types = {item.object_type.value for item in accepted_objects}
        coverage = tuple({
            "object_type": kind,
            "status": "present" if kind in present_types else "missing",
        } for kind in required_types)
        blockers = []
        if len(accepted_objects) < 2:
            blockers.append(
                "At least two accepted objects are required for a relation"
            )
        if not relations:
            blockers.append(
                "No provenance-bound semantic relation has been proposed"
            )
        missing_types = tuple(
            item["object_type"] for item in coverage
            if item["status"] == "missing"
        )
        if missing_types:
            blockers.append(
                "Structured annotation is missing: " + ", ".join(missing_types)
            )
        return {
            "extraction_id": extraction_id,
            "manifest_hash": manifest.manifest_hash,
            "accepted_objects": accepted_objects,
            "review_context": review_context,
            "annotation_coverage": coverage,
            "proposals": proposals,
            "counts": {
                "accepted_objects": len(accepted_objects),
                "proposed": sum(
                    item.state is SemanticRelationState.PROPOSED
                    for item in relations
                ),
                "accepted": sum(
                    item.state is SemanticRelationState.ACCEPTED
                    for item in relations
                ),
                "rejected": sum(
                    item.state is SemanticRelationState.REJECTED
                    for item in relations
                ),
            },
            "blockers": tuple(blockers),
        }

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
            record = next((
                record
                for run in reversed(tuple(self.runs.values()))
                for record in run.records
                if record.record_id == document.record_id
                and any(
                    source.query_family_id == document.query_family_id
                    and source.source_definition_id == document.source_definition_id
                    for source in record.source_records
                )
            ), None)
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
        run_record = next((
            (run, item)
            for run in reversed(tuple(self.runs.values()))
            for item in run.records
            if item.record_id == document.record_id
            and any(
                source.query_family_id == document.query_family_id
                and source.source_definition_id == document.source_definition_id
                for source in item.source_records
            )
        ), None)
        run, record = run_record if run_record is not None else (None, None)
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
        semantic_relation_ids: tuple[str, ...] = (),
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
        relation_ids = tuple(sorted(set(semantic_relation_ids)))
        if len(relation_ids) != len(semantic_relation_ids):
            raise ValueError("Semantic relation selection contains duplicates")
        relations = []
        for relation_id in relation_ids:
            relation = self.semantic_relations.get(relation_id)
            if relation is None:
                raise ValueError(f"Unknown semantic relation: {relation_id}")
            if relation.extraction_id != extraction_id:
                raise ValueError(
                    "Semantic relation belongs to another extraction: "
                    f"{relation_id}"
                )
            if relation.state is not SemanticRelationState.ACCEPTED:
                raise ValueError(
                    f"Semantic relation is not accepted: {relation_id}"
                )
            referenced = {
                relation.source_object_id, relation.target_object_id,
                relation.provenance_object_id,
            }
            missing = sorted(referenced - set(admitted))
            if missing:
                raise ValueError(
                    "Semantic relation requires admitted evidence: "
                    f"{missing[0]}"
                )
            relations.append(KnowledgeRelationAssertion(
                relation.source_object_id, relation.target_object_id,
                relation.edge_type, relation.provenance_object_id,
            ))
        graph = self.graph_builder.build(
            manifest, admissions, admitted, relations=tuple(relations),
        )
        identity = (
            f"{manifest.extraction_id}:{manifest.manifest_hash}:"
            f"{','.join(requested_ids)}:{','.join(relation_ids)}:"
            f"{actor_id}:{occurred_at}"
        )
        intake = KnowledgeIntakeManifest(
            f"intake-{sha256(identity.encode()).hexdigest()[:24]}",
            manifest.extraction_id, manifest.manifest_hash,
            graph.graph_id, graph.content_hash, requested_ids, admitted,
            tuple(decisions), actor_id, occurred_at,
            schema_version="1.1" if relation_ids else "1.0",
            semantic_relation_ids=relation_ids,
        ).finalized()
        self.data_repository.persist_graph(
            graph, occurred_at=occurred_at, intake=intake,
        )
        for relation_id in relation_ids:
            relation = self.semantic_relations[relation_id].admit(
                graph_id=graph.graph_id, intake_id=intake.intake_id,
                indexer=actor_id, occurred_at=occurred_at,
            )
            self.semantic_relations[relation_id] = relation
            self.relation_store.save(relation)
        self.graphs[graph.graph_id] = graph
        graph_snapshot = self.graph_store.save(graph)
        intake_snapshot = self.intake_store.save(intake)
        return intake, graph, intake_snapshot, graph_snapshot
