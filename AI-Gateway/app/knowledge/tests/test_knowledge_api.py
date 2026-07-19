from pathlib import Path
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.knowledge.authentication import KnowledgeAuthenticator, KnowledgePrincipal, KnowledgeRole
from app.knowledge.discovery.providers import CitationPage, ProviderPage
from app.knowledge.service import KnowledgeDiscoveryService
from app.knowledge.ingestion.acquisition import DocumentAcquirer
from app.knowledge.repositories.models import StoredRepresentation
from app.knowledge.extraction.models import (
    EpistemicClassification, EvidenceAdmission, EvidenceReviewAssessment,
    EvidenceReviewEvent, ExtractionReviewState,
)
from app.knowledge.repositories.artifacts import ArtifactLifecycleEvent
from app.knowledge.repositories.semantic import SemanticIndexJob, SemanticSearchHit
from app.knowledge.repositories.read_models import ObjectPage, ObjectSummary, ProjectSummary
from app.knowledge.monitoring.models import (
    FollowUpCaseTarget, ImpactReviewDecision, ImpactReviewResolution,
    ScientificSourceWatch,
    SourceWatchStatus, SourceWatchTransition,
)
from app.router.knowledge import router
from app.router.workspace import router as workspace_router
from app.router.session import router as session_router
from app.runtime.models.runtime_response import RuntimeResponse


class Provider:
    name = "openalex"
    citation_directions = ("backward", "forward")

    def search(self, plan):
        return (ProviderPage(({
            "id": "W1", "title": "Result",
            "open_access": {
                "is_oa": True,
                "oa_url": "https://example.test/paper.pdf",
            },
            "license": "CC-BY-4.0",
        },), "https://example.test"),)

    def citation_links(self, identifier, direction, limit):
        candidates = (
            ({"identifier": "W0"},)
            if str(direction) == "backward"
            else ({"identifier": "W2"},)
        )
        return (CitationPage(
            candidates[:limit],
            f"https://example.test/citations/{identifier}/{direction}",
        ),)


class RecordingRepository:
    def __init__(self):
        self.discovery_runs = []
        self.metadata_runs = []
        self.citation_traversals = []
        self.representations = []
        self.inspections = []
        self.screening_decisions = []
        self.evidence_manifests = []
        self.evidence_reviews = []
        self.graphs = []
        self.artifacts = []
        self.artifact_transitions = []
        self.publication_representations = []
        self.publication_relationships = []
        self.semantic_jobs = []
        self.object_title = "Governance matters"
        self.admission_states = {}
        self.source_watches = []
        self.watch_transitions = []
        self.change_acknowledgements = []
        self.impact_resolutions = []
        self.follow_up_targets = []

    def persist_discovery(self, run): self.discovery_runs.append(run)
    def persist_metadata(self, run): self.metadata_runs.append(run)
    def persist_citation_traversal(self, run):
        assert run.verify()
        self.citation_traversals.append(run)
    def create_source_watch(self, baseline, **values):
        watch = ScientificSourceWatch(
            "watch-1", baseline.discovery_contract.project_id,
            baseline.discovery_contract.contract_id,
            baseline.question.question_id, baseline.search_plan.plan_id,
            values["cadence_minutes"], values["owner_id"],
            baseline.discovery_contract.human_review_policy,
            values["created_at"], values["next_run_at"],
            maximum_runs=values["maximum_runs"], ends_at=values["ends_at"],
        ).finalized()
        self.source_watches.append(watch)
        return watch
    def list_source_watches(self, project_id):
        return tuple(
            item for item in self.source_watches if item.project_id == project_id
        )
    def transition_source_watch(self, watch_id, **values):
        watch = next(item for item in self.source_watches if item.watch_id == watch_id)
        if watch.owner_id != values["actor_id"]:
            raise PermissionError(
                "Only the scientific source watch owner may change its lifecycle"
            )
        transition = SourceWatchTransition(
            "transition-1", watch_id, watch.status,
            SourceWatchStatus(values["to_status"]), values["actor_id"],
            values["rationale"], values["occurred_at"], values["next_run_at"],
        )
        if not transition.verify():
            raise ValueError("Scientific source watch transition is invalid")
        self.watch_transitions.append(transition)
        return transition
    def list_monitoring_runs(self, watch_id):
        return ({"monitoring_run_id": "monitoring-1", "watch_id": watch_id},)
    def list_scientific_changes(self, watch_id, **values):
        items = ({
            "change_id": "change-1", "monitoring_run_id": "monitoring-1",
            "kind": "new_candidate", "record_key": "doi:10.1/new",
            "acknowledged": False, "candidate_status": "discovery_only",
        },)
        return items if not values["unacknowledged_only"] else items
    def acknowledge_scientific_change(self, change_id, **values):
        if change_id != "change-1":
            raise KeyError(f"Unknown scientific change: {change_id}")
        self.change_acknowledgements.append((change_id, values))
        return "ack-1"
    def resolve_impact_review(self, change_id, **values):
        if change_id != "change-retracted":
            raise KeyError(f"Unknown scientific change: {change_id}")
        item = ImpactReviewResolution(
            "impact-resolution-1", change_id,
            ImpactReviewDecision(values["decision"]), values["reviewer_id"],
            values["rationale"], values["occurred_at"], "provenance-1",
        )
        self.impact_resolutions.append(item)
        return item
    def select_follow_up_target(self, resolution_id, **values):
        if resolution_id != "impact-resolution-1":
            raise KeyError(f"Unknown impact resolution: {resolution_id}")
        item = FollowUpCaseTarget(
            "selection-1", resolution_id, values["target_kind"],
            values["target_object_id"], values["selector_id"],
            values["rationale"], values["occurred_at"], "provenance-2",
        )
        self.follow_up_targets.append(item)
        return item
    def persist_representation(self, record, result, storage_uri):
        self.representations.append((record, result, storage_uri))
        return "representation-1", 1
    def get_representation(self, record, checksum_sha256):
        persisted_record, result, uri = next(
            item for item in self.representations
            if item[0].record_id == record.record_id and item[1].content_hash == checksum_sha256
        )
        return StoredRepresentation(
            "representation-1", "object-1", "pdf", uri, result.media_type,
            result.content_hash, result.byte_size, 1,
        )
    def persist_source_inspection(self, record, inspection):
        assert inspection.verify()
        self.inspections.append((record, inspection))
        return "inspection-row-1"
    def persist_screening_decision(self, record, decision):
        assert decision.verify()
        self.screening_decisions.append((record, decision))
        return "screening-row-1"
    def validate_screening_decision(self, decision):
        assert any(item[1] == decision for item in self.screening_decisions)
    def persist_evidence(self, record, manifest, **values):
        assert manifest.verify()
        self.evidence_manifests.append((record, manifest))
        return tuple(f"evidence-{index}" for index, _ in enumerate(manifest.objects, 1))
    def load_extraction_manifest(self, extraction_id):
        try:
            return next(
                manifest for _, manifest in self.evidence_manifests
                if manifest.extraction_id == extraction_id
            )
        except StopIteration as exc:
            raise KeyError(extraction_id) from exc
    def review_evidence(self, evidence_object_id, **values):
        self.evidence_reviews.append((evidence_object_id, values))
        assessment = values["assessment"]
        event = EvidenceReviewEvent(
            "review-1", evidence_object_id,
            ExtractionReviewState(values["decision"]), values["reviewer"],
            values["rationale"], values["occurred_at"], "provenance-1", "pending",
            assessment, assessment.digest(),
        )
        self.admission_states[evidence_object_id] = EvidenceAdmission(
            evidence_object_id, event.decision, event,
        )
        return event
    def resolve_evidence_admissions(self, evidence_object_ids):
        resolved = []
        for evidence_object_id in evidence_object_ids:
            existing = self.admission_states.get(evidence_object_id)
            if existing is not None:
                resolved.append(existing)
                continue
            manifest = next((
                manifest for _, manifest in self.evidence_manifests
                if any(item.object_id == evidence_object_id for item in manifest.objects)
            ), None)
            extracted = next((
                item for item in manifest.objects
                if item.object_id == evidence_object_id
            ), None) if manifest is not None else None
            assessment = EvidenceReviewAssessment(
                True, True, True, .9,
                EpistemicClassification.OBSERVED_FACT,
                extracted.coordinates.quote_hash if extracted else "a" * 64,
                manifest.manifest_hash if manifest else "b" * 64,
            )
            event = EvidenceReviewEvent(
                f"review-{evidence_object_id}", evidence_object_id,
                ExtractionReviewState.ACCEPTED, "reviewer@example",
                "Canonical evidence reviewed", "2026-07-16T00:00:00Z",
                f"provenance-{evidence_object_id}", "pending", assessment,
                assessment.digest(),
            )
            resolved.append(EvidenceAdmission(
                evidence_object_id, ExtractionReviewState.ACCEPTED, event,
            ))
        return tuple(resolved)
    def persist_graph(self, graph, *, occurred_at, intake=None):
        graph.validate_evidence_admission()
        if intake is not None:
            assert intake.verify()
        self.graphs.append((graph, occurred_at))
        return tuple(f"edge-{index}" for index, _ in enumerate(graph.edges, 1))
    def persist_artifact(self, **values):
        self.artifacts.append(values)
        return ArtifactLifecycleEvent(
            "lifecycle-create", values["artifact_id"], None, values["status"],
            values["actor_id"], "Artifact created", values["occurred_at"], "provenance-create",
        )
    def transition_artifact(self, artifact_id, **values):
        self.artifact_transitions.append((artifact_id, values))
        return ArtifactLifecycleEvent(
            "lifecycle-transition", artifact_id, "draft", values["to_status"],
            values["actor_id"], values["rationale"], values["occurred_at"],
            "provenance-transition",
        )
    def persist_publication_representation(self, publication_id, **values):
        self.publication_representations.append((publication_id, values))

    def record_publication_relationship(self, relationship):
        self.publication_relationships.append(relationship)
        return relationship
        return StoredRepresentation(
            "publication-representation", "publication-object", values["representation_type"],
            values["storage_uri"], values["media_type"], values["checksum_sha256"],
            values["file_size"], 1,
        )
    def enqueue_semantic_index(self, **values):
        self.semantic_jobs.append(values)
        return SemanticIndexJob(
            "job-1", values["object_type"], values["object_id"], "canonical-1",
            "a" * 64, values["model"], len(values["embedding"]), "pending",
        )
    def semantic_search(self, **values):
        return (SemanticSearchHit(
            "canonical-1", "evidence:object-1", "evidence", "object-1",
            "a" * 64, values["model"], 0.99, {"purpose": "test"},
            "provenance-1", "reviewer@example",
        ),)
    def list_projects(self):
        return (ProjectSummary("researchos-default", "ResearchOS", "Default project", "active", 2),)
    def list_objects(self, project_id, **values):
        items = (
            ObjectSummary("object-1", "evidence:object-1", "evidence", "active", 1, self.object_title, "2026-07-16T00:00:00+00:00"),
        )
        return ObjectPage(items, "evidence:object-1" if values["limit"] == 1 else None)
    def get_object_read_model(self, object_ref, project_id):
        return {
            "identity": {"object_id": "object-1", "stable_key": "evidence:object-1", "object_type": "evidence", "deep_link": f"/knowledge/projects/{project_id}/objects/object-1"},
            "summary": {"title": self.object_title},
            "document": None,
            "evidence": {"review_status": "pending", "confidence": 0.95},
            "artifact": None,
            "representations": [], "relationships": [], "timeline": [],
            "project_id": project_id,
        }
    def get_work_queue(self, project_id):
        return {
            "project_id": project_id,
            "pending_reviews": [{"object_id": "object-1", "title": "Governance matters"}],
            "pending_transitions": [], "index_jobs": [],
            "impact_reviews": [{
                "task_id": "impact-review:change-retracted",
                "change_id": "change-retracted", "signal": "retracted",
                "status": "pending_human_review",
            }],
            "follow_up_cases": [{
                "case_id": "follow-up:impact-resolution-1",
                "source_resolution_id": "impact-resolution-1",
                "change_id": "change-retracted",
                "case_type": "evidence_review",
                "required_role": "reviewer", "status": "target_selected",
                "decision_automation": False,
                "blocked_reason": "Canonical impacted object selection required.",
                "target_selection": {
                    "selection_id": "selection-1", "target_kind": "evidence",
                    "target_object_id": "canonical-evidence-1",
                    "target_stable_key": "evidence:object-1",
                    "selector_id": "reviewer@example",
                    "reviewed_statement_hash": "a" * 64,
                    "extraction_manifest_hash": "b" * 64,
                },
            }, {
                "case_id": "follow-up:impact-resolution-2",
                "source_resolution_id": "impact-resolution-2",
                "change_id": "change-retracted-2",
                "case_type": "publication_review",
                "required_role": "publisher", "status": "target_selected",
                "decision_automation": False,
                "blocked_reason": "Canonical impacted object selection required.",
                "target_selection": {
                    "selection_id": "selection-2", "target_kind": "publication",
                    "target_object_id": "canonical-publication-1",
                    "target_stable_key": "artifact:publication-1",
                    "selector_id": "publisher@example",
                },
            }],
            "completed_follow_up_cases": [{
                "case_id": "follow-up:impact-resolution-closed",
                "source_resolution_id": "impact-resolution-closed",
                "change_id": "change-retracted-closed",
                "case_type": "publication_review",
                "required_role": "publisher", "status": "closed",
                "target_selection": {
                    "selection_id": "selection-closed",
                    "target_kind": "publication",
                    "target_object_id": "canonical-publication-closed",
                    "target_stable_key": "artifact:publication-closed",
                },
                "action_completion": {
                    "action_id": "relationship-closed",
                    "audit_workflow": "publication_relationship",
                    "outcome": "retracts",
                    "completed_at": "2026-07-18T00:00:00Z",
                },
                "workflow_timeline": [
                    {"stage": "impact_resolved"},
                    {"stage": "target_selected"},
                    {"stage": "action_completed"},
                    {"stage": "case_closed"},
                ],
            }],
            "counts": {"pending_reviews": 1, "pending_transitions": 0,
                       "index_jobs": 0, "failed_jobs": 0, "impact_reviews": 1,
                       "follow_up_cases": 2,
                       "completed_follow_up_cases": 1},
        }
    def get_project_graph(self, project_id, **values):
        return {
            "project_id": project_id,
            "nodes": [
                {"object_id": "object-1", "stable_key": "evidence:object-1", "object_type": "evidence", "title": "Governance matters"},
                {"object_id": "object-2", "stable_key": "artifact:object-2", "object_type": "research_artifact", "title": "Theory"},
            ],
            "edges": [{"edge_id": "edge-1", "source": "object-1", "target": "object-2", "relationship_type": "supports", "confidence": .9, "review_status": "accepted", "provenance_id": "provenance-1"}],
            "available_relationship_types": ["supports"], "truncated": False,
        }


class RecordingObjectStore:
    def __init__(self, *, corrupt=False):
        self.results = []
        self.reads = []
        self.corrupt = corrupt
        self.byte_objects = []
    def put(self, result):
        self.results.append(result)
        return (
            "s3://researchos-documents/representations/"
            f"{result.content_hash[:2]}/{result.content_hash}.pdf"
        )
    def verify_capture(self, result, storage_uri):
        assert storage_uri.endswith(f"/{result.content_hash}.pdf")
        assert result.content is not None
    def read_verified(self, representation):
        self.reads.append(representation)
        if self.corrupt:
            raise ValueError("Representation object payload checksum does not match")
        return next(
            result.content for result in self.results
            if result.content_hash == representation.checksum_sha256
        )
    def put_bytes(self, content, **values):
        self.byte_objects.append((content, values))
        return f"s3://researchos-documents/publications/{values['checksum_sha256']}.md"


class FakeSessionManager:
    session_hours = 12
    active = False
    def login(self, username, password, user_agent):
        if username != "researcher" or password != "correct-password":
            raise PermissionError("Invalid username or password")
        self.active = True
        return "session-token", "csrf-token", datetime.now(timezone.utc) + timedelta(hours=12), {
            "username": username, "display_name": "Researcher", "roles": ["discoverer"],
        }
    def authenticate(self, token, csrf=None, *, require_csrf=False):
        if not self.active or token != "session-token" or (require_csrf and csrf != "csrf-token"):
            raise PermissionError("Workspace session is invalid or expired")
        return KnowledgePrincipal("researcher", frozenset({KnowledgeRole.DISCOVERER})), datetime.now(timezone.utc) + timedelta(hours=12)
    def refresh_csrf(self, token):
        principal, expires = self.authenticate(token)
        return principal, expires, "csrf-token"
    def logout(self, token): self.active = False


def client(
    tmp_path: Path, token: str | None = "token", repository=None, object_store=None,
) -> TestClient:
    from io import BytesIO
    from reportlab.pdfgen import canvas
    output = BytesIO()
    pdf = canvas.Canvas(output)
    pdf.drawString(40, 800, "Results")
    pdf.drawString(40, 780, "We find that governance matters.")
    pdf.drawString(
        40, 765, "The final sample comprised 425 researchers (n = 425)."
    )
    pdf.drawString(40, 750, "Conclusion")
    pdf.drawString(40, 730, "Governance improves village performance.")
    pdf.save()
    valid_pdf = output.getvalue()
    app = FastAPI()
    class PdfResponse:
        headers = {"Content-Type": "application/pdf"}
        content = valid_pdf
        def raise_for_status(self): return None
    acquirer = DocumentAcquirer(transport=lambda *args, **kwargs: PdfResponse())
    app.state.knowledge_service = KnowledgeDiscoveryService(
        (Provider(),), tmp_path, document_acquirer=acquirer,
        data_repository=repository, object_store=object_store,
    )
    app.state.knowledge_authenticator = KnowledgeAuthenticator({
        "token": {"actor_id": "researcher@example", "roles": ["discoverer"]},
        "audit": {"actor_id": "auditor@example", "roles": ["auditor"]},
        "review": {"actor_id": "reviewer@example", "roles": ["reviewer"]},
        "index": {"actor_id": "indexer@example", "roles": ["indexer"]},
        "publish": {"actor_id": "publisher@example", "roles": ["publisher"]},
    })
    app.state.workspace_sessions = FakeSessionManager()
    app.include_router(router)
    app.include_router(workspace_router)
    app.include_router(session_router)
    headers = {"Authorization": f"Bearer {token}"} if token else None
    return TestClient(app, headers=headers)


def payload():
    return {
        "question": {"question_id": "q1", "text": "Why?"},
        "discovery_contract": {
            "contract_id": "c1",
            "project_id": "researchos-default",
            "research_question_id": "q1",
            "search_plan_id": "p1",
            "scope": "Tourism research",
            "source_categories": ["scholarly_index"],
            "inclusion_rules": ["Relevant scientific studies"],
            "exclusion_rules": ["Non-scientific commentary"],
            "languages": ["en"],
            "document_types": ["journal_article"],
            "evidence_types": ["reported_result"],
            "maximum_depth": 1,
            "retrieval_budget": 10,
            "license_policy": "metadata_only",
            "human_review_policy": "human_review_required",
            "stopping_conditions": ["retrieval budget exhausted"],
        },
        "query_concepts": [
            {
                "concept_id": "concept-tourism",
                "preferred_term": "tourism",
                "synonyms": ["travel industry"],
                "disciplines": ["tourism studies"],
                "attributed_by": "researcher@example",
                "rationale": "Primary domain in the research question",
            }
        ],
        "search_plan": {
            "plan_id": "p1", "query": "tourism", "providers": ["openalex"],
            "limit_per_provider": 10,
        },
    }


def test_discovery_api_is_authenticated_and_persists_run(tmp_path: Path) -> None:
    response = client(tmp_path).post("/knowledge/discovery/runs", json=payload())
    assert response.status_code == 201
    body = response.json()
    assert body["records"][0]["title"] == "Result"
    assert body["discovery_contract"]["contract_id"] == "c1"
    assert body["search_plan"]["planning_method"] == (
        "scientific-query-planner-v1"
    )
    assert body["search_plan"]["source_queries"][0]["provider"] == "openalex"
    assert body["enumerations"] == [{
        "provider": "openalex",
        "source_definition_id": "source-openalex",
        "query_family_id": body["search_plan"]["query_families"][0]["family_id"],
        "requested_limit": 10,
        "enumerated_count": 1,
        "total_available": None,
        "page_count": 1,
        "truncated": False,
        "status": "complete",
    }]
    source = body["records"][0]["source_records"][0]
    assert source["discovery_rank"] == 1
    assert source["page_number"] == 1
    assert source["request_url"] == "https://example.test"
    assert source["source_query"]
    assert "raw" not in body["records"][0]["source_records"][0]
    assert tuple((tmp_path / "runs" / body["run_id"]).glob("discovery-*.json"))
    assert tuple((tmp_path / "runs" / body["run_id"] / "raw").rglob("*.json"))


def test_discovery_api_requires_a_bound_safe_contract(tmp_path: Path) -> None:
    api = client(tmp_path)
    missing = payload()
    missing.pop("discovery_contract")
    assert api.post("/knowledge/discovery/runs", json=missing).status_code == 422

    mismatched = payload()
    mismatched["discovery_contract"]["research_question_id"] = "other"
    response = api.post("/knowledge/discovery/runs", json=mismatched)
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Discovery contract does not match research question"
    )

    over_budget = payload()
    over_budget["discovery_contract"]["retrieval_budget"] = 5
    response = api.post("/knowledge/discovery/runs", json=over_budget)
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Search plan exceeds discovery contract retrieval budget"
    )


def test_discovery_capabilities_expose_required_contract_bounds(
    tmp_path: Path,
) -> None:
    response = client(tmp_path).get("/knowledge/discovery/capabilities")
    assert response.status_code == 200
    assert response.json()["providers"] == [
        "openalex", "crossref", "semantic_scholar",
    ]
    assert {
        item["name"] for item in response.json()["source_definitions"]
    } == {"openalex", "crossref", "semantic_scholar"}
    assert all(
        item["status"] == "active"
        and item["authority_level"] == "A2"
        and item["access_method"] == "official_api"
        for item in response.json()["source_definitions"]
    )
    assert response.json()["discovery_contract"] == {
        "required": True,
        "maximum_depth": {"minimum": 1, "maximum": 10},
        "retrieval_budget": {"minimum": 1, "maximum": 100000},
        "binding": [
            "research_question_id", "search_plan_id", "date_range",
        ],
    }
    assert response.json()["query_planner"] == {
        "required": True,
        "method": "scientific-query-planner-v1",
        "concept_authority": "human_attributed",
        "source_specific_queries": True,
    }
    assert response.json()["citation_snowballing"] == {
        "directions": ["backward", "forward"],
        "contract_bound": True,
        "candidate_status": "discovery_only",
        "provider_directions": {
            "openalex": ["backward", "forward"],
            "crossref": ["backward"],
            "semantic_scholar": ["backward", "forward"],
        },
    }


def test_discovery_and_metadata_use_repository_port(tmp_path: Path) -> None:
    repository = RecordingRepository()
    api = client(tmp_path, repository=repository)
    discovered = api.post("/knowledge/discovery/runs", json=payload()).json()
    metadata = api.post(f"/knowledge/discovery/runs/{discovered['run_id']}/metadata")
    assert metadata.status_code == 201
    assert metadata.json()["summary"] == {
        "status": "enriched", "record_count": 1, "observation_count": 1,
        "citation_edge_count": 0, "conflict_count": 0,
    }
    assert repository.discovery_runs[0].run_id == discovered["run_id"]
    assert repository.metadata_runs[0].discovery_run_id == discovered["run_id"]


def test_citation_snowballing_is_contract_bound_and_persisted(
    tmp_path: Path,
) -> None:
    repository = RecordingRepository()
    api = client(tmp_path, repository=repository)
    discovered = api.post("/knowledge/discovery/runs", json=payload()).json()
    endpoint = f"/knowledge/discovery/runs/{discovered['run_id']}/citations"
    request = {
        "seed_record_id": discovered["records"][0]["record_id"],
        "directions": ["backward", "forward"],
        "maximum_depth": 1,
        "retrieval_budget": 2,
    }

    response = api.post(endpoint, json=request)

    assert response.status_code == 201
    assert response.json()["integrity_verified"] is True
    assert response.json()["summary"] == {
        "candidate_count": 2, "edge_count": 2, "failure_count": 0,
        "maximum_depth_reached": 1,
        "candidate_status": "discovery_only",
    }
    assert response.json()["snapshot"].startswith("v1.0-")
    assert repository.citation_traversals[0].discovery_run_id == discovered["run_id"]
    request["maximum_depth"] = 2
    bypass = api.post(endpoint, json=request)
    assert bypass.status_code == 422
    assert "maximum depth" in bypass.json()["detail"]


def test_citation_snowballing_rejects_unknown_run_and_seed(tmp_path: Path) -> None:
    api = client(tmp_path)
    request = {
        "seed_record_id": "missing", "directions": ["backward"],
        "maximum_depth": 1, "retrieval_budget": 1,
    }
    assert api.post(
        "/knowledge/discovery/runs/missing/citations", json=request,
    ).status_code == 404
    discovered = api.post("/knowledge/discovery/runs", json=payload()).json()
    assert api.post(
        f"/knowledge/discovery/runs/{discovered['run_id']}/citations",
        json=request,
    ).status_code == 404


def test_acquisition_policy_cannot_be_replaced_by_client(
    tmp_path: Path,
) -> None:
    api = client(tmp_path)
    discovered = api.post("/knowledge/discovery/runs", json=payload()).json()
    record = discovered["records"][0]
    source = record["source_records"][0]
    request = {
        "record_id": record["record_id"],
        "url": "https://attacker.example/arbitrary.pdf",
        "access_status": "open",
        "license": "CC-BY-4.0",
        "source_provider": source["provider"],
        "source_response_hash": source["response_hash"],
    }
    response = api.post(
        f"/knowledge/discovery/runs/{discovered['run_id']}/documents",
        json=request,
    )
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Document URL does not match enumerated source metadata"
    )

    request["url"] = "https://example.test/paper.pdf"
    request["license"] = "invented-license"
    response = api.post(
        f"/knowledge/discovery/runs/{discovered['run_id']}/documents",
        json=request,
    )
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Document license does not match enumerated source metadata"
    )


def test_continuous_monitoring_api_is_readable_and_lifecycle_governed(
    tmp_path: Path,
) -> None:
    repository = RecordingRepository()
    api = client(tmp_path, repository=repository)
    discovered = api.post("/knowledge/discovery/runs", json=payload()).json()
    watch = api.post(
        f"/knowledge/discovery/runs/{discovered['run_id']}/source-watches",
        json={
            "cadence_minutes": 60,
            "created_at": "2026-07-17T00:00:00Z",
            "next_run_at": "2026-07-17T01:00:00Z",
            "maximum_runs": 10,
        },
    )
    assert watch.status_code == 201
    assert watch.json()["candidate_status"] == "discovery_only"
    assert api.get(
        "/knowledge/projects/researchos-default/source-watches"
    ).json()["items"][0]["watch_id"] == "watch-1"
    assert api.get(
        "/knowledge/source-watches/watch-1/runs"
    ).json()["items"][0]["monitoring_run_id"] == "monitoring-1"
    changes = api.get(
        "/knowledge/source-watches/watch-1/changes",
        params={"unacknowledged_only": True},
    ).json()["items"]
    assert changes[0]["candidate_status"] == "discovery_only"

    paused = api.post(
        "/knowledge/source-watches/watch-1/transitions",
        json={
            "to_status": "paused", "rationale": "Research scope review",
            "occurred_at": "2026-07-17T00:30:00Z",
        },
    )
    assert paused.status_code == 201
    assert paused.json()["actor_id"] == "researcher@example"
    assert paused.json()["to_status"] == "paused"
    assert client(tmp_path, "review", repository=repository).post(
        "/knowledge/source-watches/watch-1/transitions",
        json={
            "to_status": "paused", "rationale": "Unauthorized takeover",
            "occurred_at": "2026-07-17T00:31:00Z",
        },
    ).status_code == 403

    acknowledged = client(
        tmp_path, "review", repository=repository,
    ).post(
        "/knowledge/scientific-changes/change-1/acknowledgements",
        json={
            "rationale": "Candidate assigned for normal screening",
            "occurred_at": "2026-07-17T00:40:00Z",
        },
    )
    assert acknowledged.status_code == 201
    assert repository.change_acknowledgements[0][1]["actor_id"] == (
        "reviewer@example"
    )
    impact = client(
        tmp_path, "review", repository=repository,
    ).post(
        "/knowledge/impact-reviews/change-retracted/resolutions",
        json={
            "decision": "evidence_review_required",
            "rationale": "Retraction may invalidate admitted evidence.",
            "occurred_at": "2026-07-17T00:45:00Z",
        },
    )
    assert impact.status_code == 201
    assert impact.json()["decision"] == "evidence_review_required"
    assert impact.json()["follow_up_case"]["case_id"] == (
        "follow-up:impact-resolution-1"
    )
    assert impact.json()["follow_up_case"]["decision_automation"] is False
    assert repository.impact_resolutions[0].reviewer_id == "reviewer@example"
    target = client(
        tmp_path, "review", repository=repository,
    ).post(
        "/knowledge/evidence-follow-up-cases/impact-resolution-1/targets",
        json={
            "target_object_id": "object-1",
            "rationale": "Canonical evidence identity verified manually.",
            "occurred_at": "2026-07-17T00:50:00Z",
        },
    )
    assert target.status_code == 201
    assert target.json()["target_kind"] == "evidence"
    assert repository.follow_up_targets[0].selector_id == "reviewer@example"
    assert client(
        tmp_path, "review", repository=repository,
    ).post(
        "/knowledge/publication-follow-up-cases/impact-resolution-1/targets",
        json={
            "target_object_id": "publication-1",
            "rationale": "Attempt with wrong role must fail.",
            "occurred_at": "2026-07-17T00:51:00Z",
        },
    ).status_code == 403


def test_monitoring_transition_and_acknowledgement_fail_closed(
    tmp_path: Path,
) -> None:
    repository = RecordingRepository()
    api = client(tmp_path, repository=repository)
    discovered = api.post("/knowledge/discovery/runs", json=payload()).json()
    api.post(
        f"/knowledge/discovery/runs/{discovered['run_id']}/source-watches",
        json={
            "cadence_minutes": 60,
            "created_at": "2026-07-17T00:00:00Z",
            "next_run_at": "2026-07-17T01:00:00Z",
        },
    )
    invalid_resume = api.post(
        "/knowledge/source-watches/watch-1/transitions",
        json={
            "to_status": "active", "rationale": "Resume",
            "occurred_at": "2026-07-17T00:30:00Z",
        },
    )
    assert invalid_resume.status_code == 422
    missing = client(tmp_path, "review", repository=repository).post(
        "/knowledge/scientific-changes/missing/acknowledgements",
        json={
            "rationale": "Cannot acknowledge unknown change",
            "occurred_at": "2026-07-17T00:40:00Z",
        },
    )
    assert missing.status_code == 404


def test_acquired_document_uses_object_and_representation_ports(tmp_path: Path) -> None:
    repository = RecordingRepository()
    object_store = RecordingObjectStore()
    api = client(tmp_path, repository=repository, object_store=object_store)
    discovered = api.post("/knowledge/discovery/runs", json=payload()).json()
    record = discovered["records"][0]
    source = record["source_records"][0]
    response = api.post(
        f"/knowledge/discovery/runs/{discovered['run_id']}/documents",
        json={
            "record_id": record["record_id"],
            "url": "https://example.test/paper.pdf",
            "access_status": "open", "license": "CC-BY-4.0",
            "source_provider": source["provider"],
            "source_response_hash": source["response_hash"],
        },
    )
    assert response.status_code == 201
    assert len(object_store.results) == 1
    persisted_record, result, uri = repository.representations[0]
    assert persisted_record.record_id == record["record_id"]
    assert result.content_hash == object_store.results[0].content_hash
    assert uri.startswith("s3://researchos-documents/")
    assert result.capture_manifest_hash
    assert result.content_encoding == "binary"
    assert result.retrieval_method == "https_pdf"


def test_canonical_persistence_failure_does_not_create_local_success(
    tmp_path: Path,
) -> None:
    class FailingRepository(RecordingRepository):
        def persist_representation(self, record, result, storage_uri):
            raise RuntimeError("canonical persistence unavailable")

    api = client(
        tmp_path, repository=FailingRepository(),
        object_store=RecordingObjectStore(),
    )
    discovered = api.post("/knowledge/discovery/runs", json=payload()).json()
    record = discovered["records"][0]
    source = record["source_records"][0]
    with pytest.raises(RuntimeError, match="canonical persistence unavailable"):
        api.post(
            f"/knowledge/discovery/runs/{discovered['run_id']}/documents",
            json={
                "record_id": record["record_id"],
                "url": "https://example.test/paper.pdf",
                "access_status": "open", "license": "CC-BY-4.0",
                "source_provider": source["provider"],
                "source_response_hash": source["response_hash"],
            },
        )
    assert not (tmp_path / "documents" / "records").exists()


def test_extraction_reads_verified_object_representation(tmp_path: Path) -> None:
    repository = RecordingRepository()
    object_store = RecordingObjectStore()
    api = client(tmp_path, repository=repository, object_store=object_store)
    discovered = api.post("/knowledge/discovery/runs", json=payload()).json()
    record = discovered["records"][0]
    source = record["source_records"][0]
    acquired = api.post(
        f"/knowledge/discovery/runs/{discovered['run_id']}/documents",
        json={
            "record_id": record["record_id"], "url": "https://example.test/paper.pdf",
            "access_status": "open", "license": "CC-BY-4.0",
            "source_provider": source["provider"],
            "source_response_hash": source["response_hash"],
        },
    ).json()
    bypass = api.post(
        f"/knowledge/documents/{acquired['document_id']}/extractions"
    )
    assert bypass.status_code == 422
    assert "screening decision" in bypass.json()["detail"]
    screening = api.post(
        f"/knowledge/documents/{acquired['document_id']}/screenings"
    )
    assert screening.status_code == 201
    assert screening.json()["status"] == "eligible"
    extraction = api.post(f"/knowledge/documents/{acquired['document_id']}/extractions")
    assert extraction.status_code == 201
    assert object_store.reads[0].checksum_sha256 == acquired["content_hash"]
    assert repository.inspections[0][1].document_content_hash == acquired["content_hash"]
    assert repository.evidence_manifests[0][0].record_id == record["record_id"]
    assert repository.evidence_manifests[0][1].extraction_id == extraction.json()["extraction_id"]
    graph = api.post(f"/knowledge/extractions/{extraction.json()['extraction_id']}/graph")
    assert graph.status_code == 201
    assert repository.graphs[0][0].graph_id == graph.json()["graph_id"]
    assert repository.graphs[0][1] == repository.evidence_manifests[0][1].created_at
    lifecycle = api.get(
        f"/knowledge/graphs/{graph.json()['graph_id']}/lifecycle",
        headers={"Authorization": "Bearer review"},
    )
    assert lifecycle.status_code == 200
    assert lifecycle.json()["state"] == "current"
    assert lifecycle.json()["current"] is True
    assert lifecycle.json()[
        "verification"
    ] == "canonical_evidence_and_semantic_relation_ledgers"
    theories = api.post("/knowledge/theories", json={"graph_ids": [graph.json()["graph_id"]]})
    assert theories.status_code == 201
    gaps = api.post(f"/knowledge/theories/{theories.json()['bundle_id']}/gaps")
    assert gaps.status_code == 201
    proposal = theories.json()["proposals"][0]
    review = api.post(
        f"/knowledge/theories/{theories.json()['bundle_id']}/reviews",
        json={
            "theory_id": proposal["theory_id"], "decision": "accepted",
            "rationale": "Evidence and provenance reviewed",
            "occurred_at": "2026-07-15T23:55:00Z",
        }, headers={"Authorization": "Bearer review"},
    )
    assert review.status_code == 200
    validation = api.post(
        f"/knowledge/theories/{theories.json()['bundle_id']}/validations",
        json={
            "assessed_at": "2026-07-16T00:00:00Z",
            "search_completed_at": "2026-07-01T00:00:00Z",
            "max_age_days": 180,
            "risk_of_bias_by_theory": {proposal["theory_id"]: "low"},
        },
        headers={"Authorization": "Bearer review"},
    )
    assert validation.status_code == 201
    publication_path = (
        f"/knowledge/theories/{theories.json()['bundle_id']}/publications"
    )
    publication_request = {
        "validation_report_id": validation.json()["report_id"],
        "kind": "literature_review", "generated_at": "2026-07-16T00:05:00Z",
    }
    assert api.post(
        publication_path, json=publication_request,
        headers={"Authorization": "Bearer review"},
    ).status_code == 403
    publication = api.post(
        publication_path,
        json=publication_request,
        headers={"Authorization": "Bearer publish"},
    )
    assert publication.status_code == 201
    assert [item["artifact_type"] for item in repository.artifacts] == [
        "theory_bundle", "gap_analysis", "validation_report", "publication_package",
    ]
    assert [item["status"] for item in repository.artifacts] == [
        "draft", "draft", "validated", "published",
    ]
    assert [item["actor_id"] for item in repository.artifacts] == [
        "researcher@example", "researcher@example", "reviewer@example", "publisher@example",
    ]
    assert len(object_store.byte_objects) == 1
    publication_id, representation = repository.publication_representations[0]
    assert publication_id == publication.json()["publication_id"]
    assert representation["representation_type"] == "markdown"
    assert representation["edition_type"] == "canonical"
    retraction = api.post(
        f"/knowledge/publications/{publication.json()['publication_id']}/relationships",
        json={
            "relation_type": "retracts", "target_publication_id": None,
            "rationale": "Material validity failure confirmed after release.",
            "occurred_at": "2026-07-17T00:00:00Z",
        }, headers={"Authorization": "Bearer publish"},
    )
    assert retraction.status_code == 201
    lifecycle = api.get(
        f"/knowledge/publications/{publication.json()['publication_id']}/lifecycle",
        headers={"Authorization": "Bearer review"},
    )
    assert lifecycle.status_code == 200
    assert lifecycle.json()["state"] == "retracted"
    assert lifecycle.json()["current"] is False
    assert repository.publication_relationships[0].verify()


def test_knowledge_intake_requires_indexer_and_registers_canonical_evidence(
    tmp_path: Path,
) -> None:
    repository = RecordingRepository()
    object_store = RecordingObjectStore()
    api = client(tmp_path, repository=repository, object_store=object_store)
    discovered = api.post("/knowledge/discovery/runs", json=payload()).json()
    record = discovered["records"][0]
    source = record["source_records"][0]
    acquired = api.post(
        f"/knowledge/discovery/runs/{discovered['run_id']}/documents",
        json={
            "record_id": record["record_id"],
            "url": "https://example.test/paper.pdf",
            "access_status": "open", "license": "CC-BY-4.0",
            "source_provider": source["provider"],
            "source_response_hash": source["response_hash"],
        },
    ).json()
    assert api.post(
        f"/knowledge/documents/{acquired['document_id']}/screenings"
    ).status_code == 201
    extraction = api.post(
        f"/knowledge/documents/{acquired['document_id']}/extractions"
    ).json()
    result_id = next(
        item["object_id"] for item in extraction["objects"]
        if item["object_type"] == "result"
    )
    conclusion_id = next(
        item["object_id"] for item in extraction["objects"]
        if item["object_type"] == "conclusion"
    )
    reextracted = api.post(
        f"/knowledge/extractions/{extraction['extraction_id']}/"
        "semantic-reextractions",
        json={"evidence_object_ids": [result_id]},
    )
    assert reextracted.status_code == 201
    assert reextracted.json()["integrity_verified"] is True
    assert {
        item["object_type"] for item in reextracted.json()["objects"]
    } >= {"population", "measurement"}
    assert all(
        item["review_state"] == "provisional"
        for item in reextracted.json()["objects"]
    )
    proposed = api.post(
        f"/knowledge/extractions/{extraction['extraction_id']}/semantic-relations",
        json={
            "source_object_id": conclusion_id,
            "target_object_id": result_id,
            "edge_type": "infers_from",
            "provenance_object_id": conclusion_id,
            "rationale": "The conclusion is explicitly drawn from the result.",
            "proposed_at": "2026-07-17T00:01:00Z",
        },
    )
    assert proposed.status_code == 201
    relation_id = proposed.json()["relation_id"]
    assert proposed.json()["state"] == "proposed"
    queue = api.get(
        f"/knowledge/extractions/{extraction['extraction_id']}/"
        "semantic-relation-review-queue",
        headers={"Authorization": "Bearer review"},
    )
    assert queue.status_code == 200
    assert queue.json()["counts"]["proposed"] == 1
    assert queue.json()["proposals"][0]["relation"]["relation_id"] == relation_id
    assert queue.json()["proposals"][0]["source"]["object_id"] == conclusion_id
    assert queue.json()["proposals"][0]["target"]["object_id"] == result_id
    assert queue.json()["review_context"][0]["review_event"]["provenance_id"]
    assert queue.json()["review_context"][0]["review_event"]["assessment_hash"]
    reviewed = api.post(
        f"/knowledge/semantic-relations/{relation_id}/reviews",
        json={
            "decision": "accepted",
            "rationale": "The source passage and relation direction were checked.",
            "occurred_at": "2026-07-17T00:01:30Z",
        },
        headers={"Authorization": "Bearer review"},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["state"] == "accepted"
    endpoint = f"/knowledge/extractions/{extraction['extraction_id']}/intake"
    request = {
        "evidence_object_ids": [],
        "semantic_relation_ids": [relation_id],
        "occurred_at": "2026-07-17T00:02:00Z",
    }
    assert api.post(endpoint, json=request).status_code == 403

    response = api.post(
        endpoint, json=request, headers={"Authorization": "Bearer index"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["integrity_verified"] is True
    assert body["intake"]["actor_id"] == "indexer@example"
    assert body["intake"]["semantic_relation_ids"] == [relation_id]
    assert body["intake"]["admitted_evidence_object_ids"]
    assert all(item["admitted"] for item in body["intake"]["decisions"])
    assert any(
        item["edge_type"] == "infers_from"
        and item["provenance"]["object_id"] == conclusion_id
        for item in body["graph"]["edges"]
    )
    assert repository.graphs[-1][0].graph_id == body["graph"]["graph_id"]


def test_extraction_fails_closed_for_corrupt_object(tmp_path: Path) -> None:
    repository = RecordingRepository()
    object_store = RecordingObjectStore(corrupt=True)
    api = client(tmp_path, repository=repository, object_store=object_store)
    discovered = api.post("/knowledge/discovery/runs", json=payload()).json()
    record = discovered["records"][0]
    source = record["source_records"][0]
    acquired = api.post(
        f"/knowledge/discovery/runs/{discovered['run_id']}/documents",
        json={
            "record_id": record["record_id"], "url": "https://example.test/paper.pdf",
            "access_status": "open", "license": "CC-BY-4.0",
            "source_provider": source["provider"],
            "source_response_hash": source["response_hash"],
        },
    ).json()
    response = api.post(f"/knowledge/documents/{acquired['document_id']}/extractions")
    assert response.status_code == 422
    assert "checksum" in response.json()["detail"]


def test_evidence_review_requires_reviewer_role_and_attributes_actor(tmp_path: Path) -> None:
    repository = RecordingRepository()
    request = {
        "decision": "accepted", "rationale": "Coordinates and quotation verified.",
        "occurred_at": "2026-07-15T14:30:00Z",
        "citation_fidelity": True, "context_preserved": True,
        "relevant": True, "confidence_assessment": .9,
        "epistemic_classification": "observed_fact",
        "reviewed_statement_hash": "a" * 64,
        "extraction_manifest_hash": "b" * 64,
    }
    assert client(tmp_path, repository=repository).post(
        "/knowledge/evidence/object-1/reviews", json=request,
    ).status_code == 403
    response = client(tmp_path, token="review", repository=repository).post(
        "/knowledge/evidence/object-1/reviews", json=request,
    )
    assert response.status_code == 201
    assert response.json()["reviewer"] == "reviewer@example"
    assert response.json()["previous_state"] == "pending"


def test_artifact_transition_requires_reviewer_and_attributes_actor(tmp_path: Path) -> None:
    repository = RecordingRepository()
    request = {
        "to_status": "review", "rationale": "Ready for formal assessment.",
        "occurred_at": "2026-07-16T00:10:00Z",
    }
    assert client(tmp_path, repository=repository).post(
        "/knowledge/artifacts/bundle-1/transitions", json=request,
    ).status_code == 403
    response = client(tmp_path, token="review", repository=repository).post(
        "/knowledge/artifacts/bundle-1/transitions", json=request,
    )
    assert response.status_code == 201
    assert response.json()["actor_id"] == "reviewer@example"
    assert response.json()["from_status"] == "draft"


def test_published_transition_requires_publisher_and_attributes_release_actor(
    tmp_path: Path,
) -> None:
    repository = RecordingRepository()
    request = {
        "to_status": "published",
        "rationale": "Release gates and immutable package verified.",
        "occurred_at": "2026-07-16T00:20:00Z",
    }
    assert client(tmp_path, token="review", repository=repository).post(
        "/knowledge/artifacts/bundle-1/transitions", json=request,
    ).status_code == 403
    response = client(tmp_path, token="publish", repository=repository).post(
        "/knowledge/artifacts/bundle-1/transitions", json=request,
    )
    assert response.status_code == 201
    assert response.json()["actor_id"] == "publisher@example"


def test_semantic_index_job_requires_indexer_role_and_exact_dimensions(tmp_path: Path) -> None:
    repository = RecordingRepository()
    request = {
        "object_type": "evidence", "object_id": "object-1", "model": "health-model",
        "embedding": [0.0] * 1536, "metadata": {"purpose": "test"},
    }
    assert client(tmp_path, repository=repository).post(
        "/knowledge/semantic-index/jobs", json=request,
    ).status_code == 403
    response = client(tmp_path, token="index", repository=repository).post(
        "/knowledge/semantic-index/jobs", json=request,
    )
    assert response.status_code == 202
    assert response.json()["dimensions"] == 1536
    assert repository.semantic_jobs[0]["object_id"] == "object-1"
    request["embedding"] = [0.0] * 10
    assert client(tmp_path, token="index", repository=repository).post(
        "/knowledge/semantic-index/jobs", json=request,
    ).status_code == 422


def test_semantic_search_returns_canonical_provenance_without_vectors(tmp_path: Path) -> None:
    response = client(tmp_path, repository=RecordingRepository()).post(
        "/knowledge/semantic-search",
        json={
            "model": "health-model", "query_embedding": [0.0] * 1536,
            "limit": 5, "object_types": ["evidence"],
        },
    )
    assert response.status_code == 200
    hit = response.json()["hits"][0]
    assert hit["stable_key"] == "evidence:object-1"
    assert hit["provenance_id"] == "provenance-1"
    assert "embedding" not in hit

def test_metadata_api_is_bound_to_discovery_run_and_versioned(tmp_path: Path) -> None:
    api = client(tmp_path)
    discovered = api.post("/knowledge/discovery/runs", json=payload()).json()
    response = api.post(f"/knowledge/discovery/runs/{discovered['run_id']}/metadata")
    assert response.status_code == 201
    assert response.json()["discovery_run_id"] == discovered["run_id"]
    assert response.json()["schema_version"] == "1.0"
    assert response.json()["snapshot"].startswith("v1.0-")
    assert api.post("/knowledge/discovery/runs/missing/metadata").status_code == 404


def test_document_api_requires_matching_provenance_and_registers_pdf(tmp_path: Path) -> None:
    api = client(
        tmp_path, repository=RecordingRepository(),
        object_store=RecordingObjectStore(),
    )
    discovered = api.post("/knowledge/discovery/runs", json=payload()).json()
    record = discovered["records"][0]
    source = record["source_records"][0]
    request = {
        "record_id": record["record_id"], "url": "https://example.test/paper.pdf",
        "access_status": "open", "license": "CC-BY-4.0",
        "source_provider": source["provider"],
        "source_response_hash": source["response_hash"],
    }
    response = api.post(f"/knowledge/discovery/runs/{discovered['run_id']}/documents", json=request)
    assert response.status_code == 201
    assert response.json()["status"] == "acquired"
    assert response.json()["integrity_verified"] is True
    screening = api.post(
        f"/knowledge/documents/{response.json()['document_id']}/screenings"
    )
    assert screening.status_code == 201
    extraction = api.post(
        f"/knowledge/documents/{response.json()['document_id']}/extractions"
    )
    assert extraction.status_code == 201
    assert extraction.json()["objects"][0]["object_type"] == "result"
    assert extraction.json()["objects"][0]["review_state"] == "provisional"
    graph = api.post(
        f"/knowledge/extractions/{extraction.json()['extraction_id']}/graph"
    )
    assert graph.status_code == 201
    assert graph.json()["integrity_verified"] is True
    assert graph.json()["nodes"]
    assert all(edge["assertion"] is True for edge in graph.json()["edges"])
    theories = api.post("/knowledge/theories", json={"graph_ids": [graph.json()["graph_id"]]})
    assert theories.status_code == 201
    proposal = theories.json()["proposals"][0]
    assert api.get("/knowledge/theories").status_code == 403
    registry = api.get(
        "/knowledge/theories", headers={"Authorization": "Bearer review"}
    )
    assert registry.status_code == 200
    assert registry.json()["items"][0]["bundle_id"] == theories.json()["bundle_id"]
    assert registry.json()["items"][0]["theory_count"] == 1
    assert registry.json()["items"][0]["pending_review_count"] == 1
    assert registry.json()["items"][0]["latest_validation"] is None
    forbidden_review = api.post(
        f"/knowledge/theories/{theories.json()['bundle_id']}/reviews",
        json={"theory_id": proposal["theory_id"], "decision": "accepted", "rationale": "Reviewed source", "occurred_at": "2026-07-15T00:00:00Z"},
    )
    assert forbidden_review.status_code == 403
    review = api.post(
        f"/knowledge/theories/{theories.json()['bundle_id']}/reviews",
        json={"theory_id": proposal["theory_id"], "decision": "accepted", "rationale": "Reviewed source", "occurred_at": "2026-07-15T00:00:00Z"},
        headers={"Authorization": "Bearer review"},
    )
    assert review.status_code == 200
    assert review.json()["reviews"][0]["reviewer"] == "reviewer@example"
    reviewed_registry = api.get(
        "/knowledge/theories", headers={"Authorization": "Bearer review"}
    ).json()["items"][0]
    assert reviewed_registry["accepted_count"] == 1
    assert reviewed_registry["pending_review_count"] == 0
    alignment_request = {
        "theory_ids": [proposal["theory_id"], proposal["theory_id"]],
        "statement": "Governance improves village performance",
        "rationale": "Reviewer evaluated semantic scope",
        "occurred_at": "2026-07-15T00:01:00Z",
    }
    forbidden_alignment = api.post(
        f"/knowledge/theories/{theories.json()['bundle_id']}/alignments",
        json=alignment_request,
    )
    assert forbidden_alignment.status_code == 403
    invalid_alignment = api.post(
        f"/knowledge/theories/{theories.json()['bundle_id']}/alignments",
        json=alignment_request, headers={"Authorization": "Bearer review"},
    )
    assert invalid_alignment.status_code == 422
    assert "distinct theories" in invalid_alignment.text
    forbidden_candidates = api.get(
        f"/knowledge/theories/{theories.json()['bundle_id']}/alignment-candidates"
    )
    assert forbidden_candidates.status_code == 403
    candidates = api.get(
        f"/knowledge/theories/{theories.json()['bundle_id']}/alignment-candidates",
        headers={"Authorization": "Bearer review"},
    )
    assert candidates.status_code == 200
    assert candidates.json()["advisory"] is True
    assert candidates.json()["method"] == "explainable-lexical-v2"
    assert candidates.json()["threshold"] == 0.2
    assert candidates.json()["scoring"] == {
        "content_term_jaccard_weight": 0.85,
        "content_bigram_jaccard_weight": 0.15,
        "minimum_shared_content_terms": 2,
        "opposing_polarity_excluded": True,
    }
    assert candidates.json()["items"] == []
    translations_path = (
        f"/knowledge/theories/{theories.json()['bundle_id']}/translations"
    )
    assert api.get(translations_path).status_code == 403
    manual_translation = api.post(
        translations_path + "/manual",
        json={
            "theory_id": proposal["theory_id"],
            "translated_statement": "Tata kelola meningkatkan kinerja desa",
            "generated_at": "2026-07-16T08:00:00Z",
        },
        headers={"Authorization": "Bearer review"},
    )
    assert manual_translation.status_code == 201
    assert manual_translation.json()["source_statement"] == proposal["statement"]
    assert manual_translation.json()["status"] == "advisory"
    translations = api.get(
        translations_path, headers={"Authorization": "Bearer review"}
    )
    assert translations.status_code == 200
    assert translations.json()["source_preserved"] is True
    assert translations.json()["items"][0]["target_language"] == "id"
    translation_review = api.post(
        f"/knowledge/theory-translations/{manual_translation.json()['translation_id']}/reviews",
        json={
            "rationale": "Terminologi Bahasa Indonesia telah diperiksa",
            "reviewed_at": "2026-07-16T08:01:00Z",
            "corrected_translation": "Tata kelola meningkatkan performa desa",
        },
        headers={"Authorization": "Bearer review"},
    )
    assert translation_review.status_code == 201
    assert translation_review.json()["status"] == "reviewed"
    invalid_keep_separate = api.post(
        f"/knowledge/theories/{theories.json()['bundle_id']}/alignment-decisions",
        json={
            "theory_ids": [proposal["theory_id"], proposal["theory_id"]],
            "decision": "keep_separate", "rationale": "Scopes differ materially",
            "occurred_at": "2026-07-15T00:02:00Z",
        }, headers={"Authorization": "Bearer review"},
    )
    assert invalid_keep_separate.status_code == 422
    forbidden_history = api.get(
        f"/knowledge/theories/{theories.json()['bundle_id']}/alignment-history"
    )
    assert forbidden_history.status_code == 403
    history = api.get(
        f"/knowledge/theories/{theories.json()['bundle_id']}/alignment-history",
        headers={"Authorization": "Bearer review"},
    )
    assert history.status_code == 200
    assert history.json()["bundle_id"] == theories.json()["bundle_id"]
    assert history.json()["latest_validation"] is None
    assert history.json()["validation_state"] == {
        "active": False, "reason": "never_validated",
    }
    assert history.json()["active_theories"][0]["theory_id"] == proposal["theory_id"]
    assert history.json()["items"] == []
    quality_path = f"/knowledge/theories/{theories.json()['bundle_id']}/alignment-quality"
    assert api.get(quality_path).status_code == 403
    quality = api.get(
        quality_path + "?threshold=0.5",
        headers={"Authorization": "Bearer review"},
    )
    assert quality.status_code == 200
    assert quality.json()["simulation_only"] is True
    assert quality.json()["simulated_threshold"] == 0.5
    assert quality.json()["benchmark"]["version"] == "1.0.0"
    assert api.get(
        quality_path + "?threshold=1.1",
        headers={"Authorization": "Bearer review"},
    ).status_code == 422
    calibration_path = "/knowledge/theory-alignment/calibration"
    assert api.get(calibration_path).status_code == 403
    calibration = api.get(
        calibration_path, headers={"Authorization": "Bearer review"}
    )
    assert calibration.status_code == 200
    assert calibration.json()["minimum_reviewed_outcomes"] == 30
    assert calibration.json()["eligible_to_propose"] is False
    assert calibration.json()["queue"]["total"] == 0
    assert api.get(
        "/knowledge/theory-alignment/calibration-cases/next"
    ).status_code == 403
    next_case = api.get(
        "/knowledge/theory-alignment/calibration-cases/next",
        headers={"Authorization": "Bearer review"},
    )
    assert next_case.status_code == 200
    assert next_case.json() == {"blind": True, "item": None}
    refresh_queue = api.post(
        "/knowledge/theory-alignment/calibration-cases/refresh",
        json={"created_at": "2026-07-16T07:00:00Z"},
        headers={"Authorization": "Bearer review"},
    )
    assert refresh_queue.status_code == 201
    assert refresh_queue.json()["created"] == 0
    disputes = api.get(
        "/knowledge/theory-alignment/calibration-disputes",
        headers={"Authorization": "Bearer review"},
    )
    assert disputes.status_code == 200
    assert disputes.json() == {"blind": True, "items": []}
    calibration_response = api.post(
        "/knowledge/theory-alignment/calibrations",
        json={
            "threshold": 0.3,
            "rationale": "Observed outcomes justify a conservative calibration",
            "proposed_at": "2026-07-16T06:00:00Z",
        },
        headers={"Authorization": "Bearer review"},
    )
    assert calibration_response.status_code == 422
    assert "at least 30" in calibration_response.text
    assert api.get(
        f"/knowledge/theories/{theories.json()['bundle_id']}/validation-history"
    ).status_code == 403
    gaps = api.post(f"/knowledge/theories/{theories.json()['bundle_id']}/gaps")
    assert gaps.status_code == 201
    assert gaps.json()["gaps"][0]["gap_type"] == "limited_coverage"
    assert gaps.json()["hypotheses"][0]["advisory"] is True
    invalid_bias = api.post(
        f"/knowledge/theories/{theories.json()['bundle_id']}/validations",
        json={"assessed_at": "2026-07-15T00:00:00Z", "search_completed_at": "2026-07-01T00:00:00Z", "max_age_days": 180, "risk_of_bias_by_theory": {proposal["theory_id"]: "unclear"}},
        headers={"Authorization": "Bearer review"},
    )
    assert invalid_bias.status_code == 422
    assert "some_concerns" in invalid_bias.text
    validation = api.post(
        f"/knowledge/theories/{theories.json()['bundle_id']}/validations",
        json={"assessed_at": "2026-07-15T00:00:00Z", "search_completed_at": "2026-07-01T00:00:00Z", "max_age_days": 180, "risk_of_bias_by_theory": {proposal["theory_id"]: "low"}},
        headers={"Authorization": "Bearer review"},
    )
    assert validation.status_code == 201
    assert validation.json()["status"] == "incomplete"
    assert validation.json()["reviewer"] == "reviewer@example"
    assert validation.json()["theory_bundle_hash"] == review.json()["content_hash"]
    validation_history = api.get(
        f"/knowledge/theories/{theories.json()['bundle_id']}/validation-history",
        headers={"Authorization": "Bearer review"},
    )
    assert validation_history.status_code == 200
    assert validation_history.json()["items"][0]["active_for_current_bundle"] is True
    assert api.get(
        f"/knowledge/theories/{theories.json()['bundle_id']}/publication-readiness"
    ).status_code == 403
    readiness = api.get(
        f"/knowledge/theories/{theories.json()['bundle_id']}/publication-readiness?kind=literature_review",
        headers={"Authorization": "Bearer review"},
    )
    assert readiness.status_code == 200
    assert readiness.json()["ready"] is True
    assert all(item["passed"] for item in readiness.json()["checks"])
    systematic = api.get(
        f"/knowledge/theories/{theories.json()['bundle_id']}/publication-readiness?kind=systematic_review_support",
        headers={"Authorization": "Bearer review"},
    )
    assert systematic.status_code == 200
    assert systematic.json()["ready"] is False
    assert next(
        item for item in systematic.json()["checks"]
        if item["key"] == "validation_policy"
    )["passed"] is False
    preview = api.post(
        f"/knowledge/theories/{theories.json()['bundle_id']}/publication-preview",
        json={"kind": "evidence_brief", "validation_report_id": validation.json()["report_id"]},
        headers={"Authorization": "Bearer review"},
    )
    assert preview.status_code == 200
    assert preview.json()["ready"] is True
    assert preview.json()["citation_verification"]["verified"] is True
    assert "# Evidence Brief" in preview.json()["markdown"]
    publication = api.post(
        f"/knowledge/theories/{theories.json()['bundle_id']}/publications",
        json={"validation_report_id": validation.json()["report_id"], "kind": "literature_review", "generated_at": "2026-07-15T00:00:00Z"},
        headers={"Authorization": "Bearer publish"},
    )
    assert publication.status_code == 201
    assert publication.json()["integrity_verified"] is True
    assert publication.json()["generated_by"] == "publisher@example"
    history = api.get(
        f"/knowledge/theories/{theories.json()['bundle_id']}/publication-history",
        headers={"Authorization": "Bearer review"},
    )
    assert history.status_code == 200
    assert history.json()["items"][0]["manifest"]["publication_id"] == publication.json()["publication_id"]
    package = api.get(
        f"/knowledge/theories/{theories.json()['bundle_id']}/publications/{publication.json()['publication_id']}",
        headers={"Authorization": "Bearer review"},
    )
    assert package.status_code == 200
    assert package.json()["integrity_verified"] is True
    assert package.json()["package_content_hash"] == publication.json()["package_content_hash"]
    request["source_response_hash"] = "invented"
    assert api.post(f"/knowledge/discovery/runs/{discovered['run_id']}/documents", json=request).status_code == 422


def test_direct_service_cannot_build_canonical_graph_without_admission_authority(
    tmp_path: Path,
) -> None:
    api = client(tmp_path)
    discovered = api.post("/knowledge/discovery/runs", json=payload()).json()
    record = discovered["records"][0]
    source = record["source_records"][0]
    document = api.post(
        f"/knowledge/discovery/runs/{discovered['run_id']}/documents",
        json={
            "record_id": record["record_id"],
            "url": "https://example.test/paper.pdf",
            "access_status": "open", "license": "CC-BY-4.0",
            "source_provider": source["provider"],
            "source_response_hash": source["response_hash"],
        },
    ).json()
    screening = api.post(
        f"/knowledge/documents/{document['document_id']}/screenings"
    )
    assert screening.status_code == 201
    extraction = api.post(
        f"/knowledge/documents/{document['document_id']}/extractions"
    ).json()

    response = api.post(
        f"/knowledge/extractions/{extraction['extraction_id']}/graph"
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Canonical repository is required for evidence admission"
    )


def test_discovery_api_fails_closed_and_enforces_role(tmp_path: Path) -> None:
    missing = client(tmp_path, None).post("/knowledge/discovery/runs", json=payload())
    assert missing.status_code == 401
    forbidden = client(tmp_path, "audit").post("/knowledge/discovery/runs", json=payload())
    assert forbidden.status_code == 403


def test_discovery_api_rejects_client_paths_and_invalid_year_range(tmp_path: Path) -> None:
    data = payload()
    data["output_root"] = "C:/sensitive"
    assert client(tmp_path).post("/knowledge/discovery/runs", json=data).status_code == 422
    data = payload()
    data["search_plan"]["year_from"] = 2025
    data["search_plan"]["year_to"] = 2020
    response = client(tmp_path).post("/knowledge/discovery/runs", json=data)
    assert response.status_code == 422


def test_product_read_api_supports_any_authenticated_role_and_cursor(tmp_path: Path) -> None:
    api = client(tmp_path, "audit", repository=RecordingRepository())
    projects = api.get("/knowledge/projects")
    assert projects.status_code == 200
    assert projects.json()["items"][0]["object_count"] == 2
    objects = api.get("/knowledge/projects/researchos-default/objects?limit=1&q=governance&object_type=evidence")
    assert objects.status_code == 200
    assert objects.json()["items"][0]["stable_key"] == "evidence:object-1"
    assert objects.json()["next_cursor"] == "evidence:object-1"


def test_product_object_actions_are_permission_aware(tmp_path: Path) -> None:
    reviewer = client(tmp_path, "review", repository=RecordingRepository()).get(
        "/knowledge/projects/researchos-default/objects/object-1"
    )
    assert reviewer.status_code == 200
    body = reviewer.json()
    assert body["identity"]["deep_link"].endswith("/objects/object-1")
    assert {item["action"] for item in body["permissions"]["available_actions"]} == {
        "evidence:accept", "evidence:reject",
    }
    auditor = client(tmp_path, "audit", repository=RecordingRepository()).get(
        "/knowledge/projects/researchos-default/objects/object-1"
    ).json()
    assert auditor["permissions"]["can_read"] is True
    assert auditor["permissions"]["available_actions"] == []


def test_object_workspace_is_available_without_embedding_credentials(tmp_path: Path) -> None:
    response = client(tmp_path, None).get("/workspace")
    assert response.headers["cache-control"] == "no-store"
    assert response.status_code == 200
    assert "ResearchOS Workspace" in response.text
    assert "cookie HttpOnly" in response.text
    assert "Theory Alignment" in response.text
    assert "/workspace-assets/theory.js" in response.text
    assert "/workspace-assets/i18n.js" in response.text
    assert "/workspace-assets/i18n.css" in response.text
    assert 'id="uiLanguage"' in response.text
    assert "Bahasa Sumber / English" in response.text
    assert 'id="translateObject"' in response.text
    assert 'id="translateProjectObjects"' in response.text
    assert "/workspace-assets/object-translation-ui.js" in response.text
    assert "/workspace-assets/discovery.js?v=" in response.text
    assert "/workspace-assets/workspace.css?v=" in response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["clear-site-data"] == '"cache"'
    assert 'id="qualityThreshold"' in response.text
    assert 'id="qualityMetrics"' in response.text
    assert 'id="calibrationForm"' in response.text
    assert 'id="calibrationHistory"' in response.text
    assert 'id="calibrationQueueStats"' in response.text
    assert 'id="blindCalibrationCase"' in response.text
    assert 'id="languageIndonesian"' in response.text
    assert 'id="languageOriginal"' in response.text
    assert 'id="translationList"' in response.text
    assert 'id="separateDialog"' in response.text
    assert "Simpan sebagai terpisah" in response.text
    assert 'id="decisionHistory"' in response.text
    assert "Decision History" in response.text
    assert 'id="revalidationDialog"' in response.text
    assert 'id="validationHistory"' in response.text
    assert 'id="readinessChecks"' in response.text
    assert 'id="publicationPreview"' in response.text
    assert 'id="publicationHistory"' in response.text


def test_workspace_i18n_defaults_to_indonesian_and_covers_every_product_area() -> None:
    static = Path(__file__).resolve().parents[2] / "product" / "static"
    catalog = (static / "i18n.js").read_text(encoding="utf-8")
    workspace = (static / "workspace.js").read_text(encoding="utf-8")

    assert "researchos-ui-language')||'id'" in catalog
    assert "MutationObserver" in catalog
    assert ".candidate-claim>strong" in catalog
    assert "monitorTranslationJob" in workspace
    assert "object-translation-jobs" in workspace
    assert "dari ${total} selesai" in workspace
    for source, indonesian in {
        "SCIENTIFIC LIBRARY": "PERPUSTAKAAN ILMIAH",
        "OPERATIONAL WORKFLOW": "ALUR KERJA OPERASIONAL",
        "SCIENTIFIC RELATIONSHIPS": "HUBUNGAN ILMIAH",
        "LITERATURE PIPELINE": "ALUR LITERATUR",
        "CONTROL PLANE": "PANEL KENDALI",
        "REVIEWER-GOVERNED SYNTHESIS": "SINTESIS TERKENDALI REVIEWER",
        "SCIENTIFIC INTELLIGENCE": "KECERDASAN ILMIAH",
        "Publication Readiness": "Kesiapan Publikasi",
    }.items():
        assert f'"{source}":"{indonesian}"' in catalog


def test_discovery_workspace_submits_the_required_governed_contract() -> None:
    static = Path(__file__).resolve().parents[2] / "product" / "static"
    discovery = (static / "discovery.js").read_text(encoding="utf-8")
    workspace = (static / "workspace.js").read_text(encoding="utf-8")

    assert "discovery_contract:" in discovery
    assert "query_concepts:" in discovery
    assert "research_question_id:questionId" in discovery
    assert "search_plan_id:planId" in discovery
    assert "project_id:state.project" in discovery
    assert "/inspections" in discovery
    assert "/screenings" in discovery
    assert "screening.status!=='eligible'" in discovery
    assert "Array.isArray(body.detail)" in workspace
    assert "state.queue?.pending_reviews" in workspace
    assert "item.reviewed_statement_hash" in workspace
    assert "item.extraction_manifest_hash" in workspace
    assert "citation_fidelity:" in workspace
    assert "epistemic_classification:" in workspace


def test_composed_knowledge_routers_do_not_duplicate_paths(tmp_path: Path) -> None:
    application = client(tmp_path, None).app
    paths = [
        (route.path, tuple(sorted(route.methods or ())))
        for route in application.routes
        if getattr(route, "path", "").startswith("/knowledge")
    ]

    assert len(paths) == len(set(paths))


def test_work_queue_is_readable_and_exposes_role_capabilities(tmp_path: Path) -> None:
    reviewer = client(tmp_path, "review", repository=RecordingRepository()).get(
        "/knowledge/projects/researchos-default/work-queue"
    )
    assert reviewer.status_code == 200
    assert reviewer.json()["counts"]["pending_reviews"] == 1
    assert reviewer.json()["counts"]["impact_reviews"] == 1
    assert reviewer.json()["impact_reviews"][0]["signal"] == "retracted"
    assert reviewer.json()["counts"]["follow_up_cases"] == 2
    assert reviewer.json()["follow_up_cases"][0]["action_authorized"] is True
    assert reviewer.json()["follow_up_cases"][0]["available_action"] == {
        "action": "evidence:review", "method": "POST",
        "href": "/knowledge/evidence/object-1/reviews",
        "requires_confirmation": True,
        "audit_workflow": "evidence_review_event",
        "reviewed_statement_hash": "a" * 64,
        "extraction_manifest_hash": "b" * 64,
    }
    assert reviewer.json()["follow_up_cases"][1]["available_action"] is None
    publisher = client(
        tmp_path, "publish", repository=RecordingRepository()
    ).get("/knowledge/projects/researchos-default/work-queue").json()
    assert publisher["follow_up_cases"][0]["action_authorized"] is False
    assert publisher["follow_up_cases"][1]["available_action"] == {
        "action": "publication:retract", "method": "POST",
        "href": "/knowledge/publications/publication-1/relationships",
        "relation_type": "retracts", "requires_confirmation": True,
        "audit_workflow": "publication_relationship",
    }
    assert publisher["counts"]["completed_follow_up_cases"] == 1
    completed = publisher["completed_follow_up_cases"][0]
    assert completed["status"] == "closed"
    assert completed["action_completion"]["outcome"] == "retracts"
    assert [item["stage"] for item in completed["workflow_timeline"]] == [
        "impact_resolved", "target_selected", "action_completed", "case_closed",
    ]
    assert reviewer.json()["permissions"]["can_review"] is True
    assert reviewer.json()["permissions"]["can_index"] is False
    indexer = client(tmp_path, "index", repository=RecordingRepository()).get(
        "/knowledge/projects/researchos-default/work-queue"
    ).json()
    assert indexer["permissions"]["can_index"] is True


def test_project_graph_is_authenticated_filterable_and_provenance_bearing(tmp_path: Path) -> None:
    response = client(tmp_path, "audit", repository=RecordingRepository()).get(
        "/knowledge/projects/researchos-default/graph?relationship_type=supports&min_confidence=.8&review_status=accepted"
    )
    assert response.status_code == 200
    assert len(response.json()["nodes"]) == 2
    assert response.json()["edges"][0]["provenance_id"] == "provenance-1"
    assert "embedding" not in response.text


def test_scientific_object_translation_is_source_bound_and_reviewable(
    tmp_path: Path,
) -> None:
    repository = RecordingRepository()
    api = client(tmp_path, "review", repository=repository)
    created = api.post(
        "/knowledge/projects/researchos-default/object-translations",
        json={
            "object_id": "object-1",
            "generated_at": "2026-07-16T09:00:00Z",
            "translated_text": "Tata kelola itu penting",
        },
    )
    assert created.status_code == 201
    assert created.json()["source_text"] == "Governance matters"
    assert created.json()["source_hash"]
    assert created.json()["status"] == "advisory"
    listed = api.get(
        "/knowledge/projects/researchos-default/object-translations"
    )
    assert listed.status_code == 200
    assert listed.json()["source_preserved"] is True
    assert listed.json()["items"][0]["translated_text"] == "Tata kelola itu penting"
    reviewed = api.post(
        f"/knowledge/object-translations/{created.json()['translation_id']}/reviews",
        json={
            "corrected_text": "Tata kelola berperan penting",
            "rationale": "Makna ilmiah telah dibandingkan dengan sumber",
            "reviewed_at": "2026-07-16T09:01:00Z",
        },
    )
    assert reviewed.status_code == 201
    assert reviewed.json()["status"] == "reviewed"
    assert reviewed.json()["translated_text"] == "Tata kelola berperan penting"
    repository.object_title = "Governance may matter"
    stale = api.get("/knowledge/projects/researchos-default/object-translations")
    assert stale.status_code == 200
    assert stale.json()["items"] == []


def test_bulk_object_translation_generates_all_missing_project_titles(
    tmp_path: Path,
) -> None:
    api = client(tmp_path, "review", repository=RecordingRepository())

    class TranslationRouter:
        def execute(self, request):
            assert request.metadata["action"] == "bulk_translate_scientific_object"
            assert request.metadata["think"] is False
            assert request.metadata["generation_options"] == {"num_predict": 768}
            return RuntimeResponse(
                provider="test", model="translation-v1",
                text="Tata kelola itu penting",
            )

    api.app.state.ai_router = TranslationRouter()
    generated = api.post(
        "/knowledge/projects/researchos-default/object-translations/generate-missing",
        json={"generated_at": "2026-07-16T10:00:00Z"},
    )

    assert generated.status_code == 201
    assert generated.json()["created"] == 1
    assert generated.json()["remaining"] == 0
    assert generated.json()["failures"] == []
    listed = api.get(
        "/knowledge/projects/researchos-default/object-translations"
    ).json()
    assert listed["items"][0]["translated_text"] == "Tata kelola itu penting"


def test_object_translation_job_survives_the_start_request(
    tmp_path: Path,
) -> None:
    api = client(tmp_path, "review", repository=RecordingRepository())

    class TranslationRouter:
        def execute(self, request):
            return RuntimeResponse(
                provider="test", model="translation-v1",
                text="Tata kelola itu penting",
            )

    api.app.state.ai_router = TranslationRouter()
    started = api.post(
        "/knowledge/projects/researchos-default/object-translation-jobs",
        json={"generated_at": "2026-07-16T10:00:00Z"},
    )

    assert started.status_code == 202
    job = api.get(
        "/knowledge/projects/researchos-default/object-translation-jobs/"
        + started.json()["job_id"]
    )
    assert job.status_code == 200
    assert job.json()["status"] == "completed"
    assert job.json()["completed"] == 1
    assert job.json()["remaining"] == 0


def test_object_translation_uses_a_traceable_fallback_for_an_empty_title(
    tmp_path: Path,
) -> None:
    repository = RecordingRepository()
    repository.object_title = ""
    api = client(tmp_path, "review", repository=repository)

    created = api.post(
        "/knowledge/projects/researchos-default/object-translations",
        json={
            "object_id": "object-1",
            "generated_at": "2026-07-16T10:00:00Z",
            "translated_text": "Objek bukti ilmiah tanpa judul",
        },
    )

    assert created.status_code == 201
    assert created.json()["source_text"] == (
        "Untitled scientific document — Unknown journal — evidence:object-1"
    )


def test_long_object_translation_receives_a_larger_bounded_output_budget(
    tmp_path: Path,
) -> None:
    repository = RecordingRepository()
    repository.object_title = "x" * 9_000
    api = client(tmp_path, "review", repository=repository)

    class TranslationRouter:
        def execute(self, request):
            assert request.metadata["generation_options"] == {"num_predict": 4096}
            return RuntimeResponse(
                provider="test", model="translation-v1", text="Terjemahan panjang",
            )

    api.app.state.ai_router = TranslationRouter()
    created = api.post(
        "/knowledge/projects/researchos-default/object-translations",
        json={
            "object_id": "object-1",
            "generated_at": "2026-07-16T10:00:00Z",
            "translated_text": None,
        },
    )

    assert created.status_code == 201


def test_discovery_capabilities_drive_workspace_without_client_guesses(tmp_path: Path) -> None:
    response = client(tmp_path, "audit", repository=RecordingRepository()).get(
        "/knowledge/discovery/capabilities"
    )
    assert response.status_code == 200
    assert response.json()["providers"] == ["openalex", "crossref", "semantic_scholar"]
    assert response.json()["workflow"][-1] == "extract"


def test_human_session_cookie_login_csrf_and_logout(tmp_path: Path) -> None:
    api = client(tmp_path, None, repository=RecordingRepository())
    login = api.post("/auth/login", json={"username": "researcher", "password": "correct-password"})
    assert login.status_code == 200
    assert "HttpOnly" in login.headers["set-cookie"]
    assert login.json()["csrf_token"] == "csrf-token"
    assert api.get("/knowledge/projects").status_code == 200
    rejected = api.post("/knowledge/discovery/runs", json=payload())
    assert rejected.status_code == 401
    accepted = api.post(
        "/knowledge/discovery/runs", json=payload(), headers={"X-CSRF-Token": "csrf-token"},
    )
    assert accepted.status_code == 201
    assert api.post("/auth/logout", headers={"X-CSRF-Token": "csrf-token"}).status_code == 204
    assert api.get("/knowledge/projects").status_code == 401
