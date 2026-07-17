"""Application service wiring SK-001A infrastructure and domain pipeline."""

from pathlib import Path

from app.knowledge.discovery.providers import LiteratureProvider
from app.knowledge.models import (
    DiscoveryContract, DiscoveryRun, ScientificQuestion, SearchPlan,
)
from app.knowledge.ingestion.models import DocumentCandidate
from app.knowledge.discovery.query_planner import ScientificQueryPlanner
from app.knowledge.repository_service import KnowledgeRepositoryService
from app.knowledge.ingestion_pipeline import KnowledgeIngestionPipeline
from app.knowledge.theory_pipeline import KnowledgeTheoryPipeline
from app.knowledge.object_translation import ObjectTranslation, ObjectTranslationStore
from dataclasses import asdict, replace
from hashlib import sha256


class KnowledgeDiscoveryService:
    def __init__(
        self, providers: tuple[LiteratureProvider, ...], output_root: Path,
        *, document_acquirer=None, data_repository=None, object_store=None,
    ) -> None:
        self.output_root = output_root
        self.query_planner = ScientificQueryPlanner()
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
        self.object_translation_store = ObjectTranslationStore(
            output_root / "object-translations"
        )
        self.object_translations = {
            item.translation_id: item
            for item in self.object_translation_store.load_all()
        }

    def object_translation_source(self, project_id, object_id, principal):
        obj = self.get_object_read_model(object_id, project_id, principal)
        text = obj["summary"]["title"].strip()
        if not text:
            document = obj.get("document") or {}
            journal = document.get("journal") or "Unknown journal"
            doi = document.get("doi") or obj["identity"]["stable_key"]
            text = f"Untitled scientific document — {journal} — {doi}"
        return {
            "project_id": project_id, "object_id": obj["identity"]["object_id"],
            "source_text": text,
            "source_hash": ObjectTranslation.source_digest(text),
        }

    def record_object_translation(
        self, project_id, object_id, *, translated_text, provider, model,
        generated_by, generated_at, principal,
    ):
        source = self.object_translation_source(project_id, object_id, principal)
        if not translated_text.strip():
            raise ValueError("Translated object text is required")
        identity = f"{project_id}:{source['object_id']}:id:{source['source_hash']}"
        item = ObjectTranslation(
            f"object-translation-{sha256(identity.encode()).hexdigest()[:24]}",
            project_id, source["object_id"], source["source_text"],
            source["source_hash"], translated_text.strip(), provider, model,
            generated_by, generated_at,
        ).finalized()
        self.object_translations[item.translation_id] = item
        return item, self.object_translation_store.save(item)

    def list_object_translations(self, project_id, principal):
        current = []
        for item in self.object_translations.values():
            if item.project_id != project_id:
                continue
            try:
                source = self.object_translation_source(
                    project_id, item.object_id, principal
                )
            except KeyError:
                continue
            if source["source_hash"] == item.source_hash:
                current.append(asdict(item))
        return tuple(current)

    def review_object_translation(
        self, translation_id, *, reviewer, rationale, reviewed_at,
        corrected_text, principal,
    ):
        item = self.object_translations.get(translation_id)
        if item is None:
            raise KeyError(f"Unknown object translation: {translation_id}")
        source = self.object_translation_source(
            item.project_id, item.object_id, principal
        )
        if source["source_hash"] != item.source_hash:
            raise ValueError("Object translation source has changed")
        if not rationale.strip() or not corrected_text.strip():
            raise ValueError("Reviewed translation and rationale are required")
        reviewed = replace(
            item, translated_text=corrected_text.strip(), status="reviewed",
            reviewer=reviewer, rationale=rationale.strip(),
            reviewed_at=reviewed_at, content_hash="",
        ).finalized()
        self.object_translations[translation_id] = reviewed
        return reviewed, self.object_translation_store.save(reviewed)

    def discover(
        self, question: ScientificQuestion, contract: DiscoveryContract,
        plan: SearchPlan, concepts,
    ):
        sources = self.ingestion_pipeline.engine.resolve_sources(plan, contract)
        planned = self.query_planner.plan(
            question, contract, plan, concepts, sources,
        )
        return self.ingestion_pipeline.discover(question, contract, planned)

    def discovery_source_definitions(self):
        return self.ingestion_pipeline.engine.source_definitions

    def collect_metadata(self, run_id: str):
        return self.ingestion_pipeline.collect_metadata(run_id)

    def acquire_document(self, run_id: str, candidate: DocumentCandidate):
        return self.ingestion_pipeline.acquire_document(run_id, candidate)

    def inspect_document(self, document_id: str):
        return self.ingestion_pipeline.inspect_document(document_id)

    def screen_document(self, document_id: str):
        return self.ingestion_pipeline.screen_document(document_id)

    def extract_document(self, document_id: str):
        return self.ingestion_pipeline.extract_document(document_id)

    def build_knowledge_graph(self, extraction_id: str):
        return self.ingestion_pipeline.build_knowledge_graph(extraction_id)

    def intake_accepted_evidence(
        self, extraction_id: str, *, evidence_object_ids: tuple[str, ...],
        actor_id: str, occurred_at: str,
    ):
        return self.ingestion_pipeline.intake_accepted_evidence(
            extraction_id, evidence_object_ids=evidence_object_ids,
            actor_id=actor_id, occurred_at=occurred_at,
        )

    def review_evidence(
        self, evidence_object_id: str, *, decision: str, reviewer: str,
        rationale: str, occurred_at: str, assessment,
    ):
        return self.repository_service.review_evidence(
            evidence_object_id, decision=decision, reviewer=reviewer,
            rationale=rationale, occurred_at=occurred_at, assessment=assessment,
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

    def alignment_candidate_metadata(self):
        return self.theory_pipeline.alignment_candidate_metadata()

    def theory_translation_source(self, bundle_id, theory_id):
        return self.theory_pipeline.theory_translation_source(
            bundle_id, theory_id
        )

    def record_theory_translation(self, bundle_id, theory_id, **options):
        return self.theory_pipeline.record_theory_translation(
            bundle_id, theory_id, **options
        )

    def theory_translations(self, bundle_id):
        return self.theory_pipeline.theory_translations(bundle_id)

    def review_theory_translation(self, translation_id, **options):
        return self.theory_pipeline.review_theory_translation(
            translation_id, **options
        )

    def alignment_quality(self, bundle_id, *, threshold=None):
        return self.theory_pipeline.alignment_quality(
            bundle_id, threshold=threshold
        )

    def alignment_calibration_summary(self):
        return self.theory_pipeline.alignment_calibration_summary()

    def refresh_calibration_queue(self, **options):
        return self.theory_pipeline.refresh_calibration_queue(**options)

    def next_calibration_case(self, **options):
        return self.theory_pipeline.next_calibration_case(**options)

    def review_calibration_case(self, case_id, **options):
        return self.theory_pipeline.review_calibration_case(case_id, **options)

    def calibration_disputes(self, **options):
        return self.theory_pipeline.calibration_disputes(**options)

    def adjudicate_calibration_case(self, case_id, **options):
        return self.theory_pipeline.adjudicate_calibration_case(
            case_id, **options
        )

    def propose_alignment_calibration(self, **options):
        return self.theory_pipeline.propose_alignment_calibration(**options)

    def approve_alignment_calibration(self, calibration_id, **options):
        return self.theory_pipeline.approve_alignment_calibration(
            calibration_id, **options
        )

    def rollback_alignment_calibration(self, **options):
        return self.theory_pipeline.rollback_alignment_calibration(**options)

    def keep_theories_separate(self, bundle_id, **options):
        return self.theory_pipeline.keep_theories_separate(bundle_id, **options)

    def alignment_history(self, bundle_id):
        return self.theory_pipeline.alignment_history(bundle_id)

    def list_theory_bundles(self):
        return self.theory_pipeline.list_theory_bundles()

    def detect_research_gaps(self, bundle_id: str, *, generated_by: str = "researchos"):
        return self.theory_pipeline.detect_research_gaps(
            bundle_id, generated_by=generated_by
        )

    def validate_theories(self, bundle_id, **options):
        return self.theory_pipeline.validate_theories(bundle_id, **options)

    def validation_history(self, bundle_id):
        return self.theory_pipeline.validation_history(bundle_id)

    def publish(self, bundle_id, **options):
        return self.theory_pipeline.publish(bundle_id, **options)

    def publication_readiness(self, bundle_id, **options):
        return self.theory_pipeline.publication_readiness(bundle_id, **options)

    def preview_publication(self, bundle_id, **options):
        return self.theory_pipeline.preview_publication(bundle_id, **options)

    def publication_history(self, bundle_id):
        return self.theory_pipeline.publication_history(bundle_id)

    def publication_package(self, bundle_id, publication_id):
        return self.theory_pipeline.publication_package(bundle_id, publication_id)

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
