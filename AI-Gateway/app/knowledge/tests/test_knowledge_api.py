from pathlib import Path
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.knowledge.authentication import KnowledgeAuthenticator, KnowledgePrincipal, KnowledgeRole
from app.knowledge.discovery.providers import ProviderPage
from app.knowledge.service import KnowledgeDiscoveryService
from app.knowledge.ingestion.acquisition import DocumentAcquirer
from app.knowledge.repositories.models import StoredRepresentation
from app.knowledge.extraction.models import EvidenceReviewEvent, ExtractionReviewState
from app.knowledge.repositories.artifacts import ArtifactLifecycleEvent
from app.knowledge.repositories.semantic import SemanticIndexJob, SemanticSearchHit
from app.knowledge.repositories.read_models import ObjectPage, ObjectSummary, ProjectSummary
from app.router.knowledge import router
from app.router.workspace import router as workspace_router
from app.router.session import router as session_router


class Provider:
    name = "openalex"

    def search(self, plan):
        return (ProviderPage(({"id": "W1", "title": "Result"},), "https://example.test"),)


class RecordingRepository:
    def __init__(self):
        self.discovery_runs = []
        self.metadata_runs = []
        self.representations = []
        self.evidence_manifests = []
        self.evidence_reviews = []
        self.graphs = []
        self.artifacts = []
        self.artifact_transitions = []
        self.publication_representations = []
        self.semantic_jobs = []

    def persist_discovery(self, run): self.discovery_runs.append(run)
    def persist_metadata(self, run): self.metadata_runs.append(run)
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
    def persist_evidence(self, record, manifest):
        self.evidence_manifests.append((record, manifest))
        return tuple(f"evidence-{index}" for index, _ in enumerate(manifest.objects, 1))
    def review_evidence(self, evidence_object_id, **values):
        self.evidence_reviews.append((evidence_object_id, values))
        return EvidenceReviewEvent(
            "review-1", evidence_object_id,
            ExtractionReviewState(values["decision"]), values["reviewer"],
            values["rationale"], values["occurred_at"], "provenance-1", "pending",
        )
    def persist_graph(self, graph, *, occurred_at):
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
            ObjectSummary("object-1", "evidence:object-1", "evidence", "active", 1, "Governance matters", "2026-07-16T00:00:00+00:00"),
        )
        return ObjectPage(items, "evidence:object-1" if values["limit"] == 1 else None)
    def get_object_read_model(self, object_ref, project_id):
        return {
            "identity": {"object_id": "object-1", "stable_key": "evidence:object-1", "object_type": "evidence", "deep_link": f"/knowledge/projects/{project_id}/objects/object-1"},
            "summary": {"title": "Governance matters"},
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
            "counts": {"pending_reviews": 1, "pending_transitions": 0, "index_jobs": 0, "failed_jobs": 0},
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
        return f"s3://researchos-documents/{result.content_hash}.pdf"
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
    assert "raw" not in body["records"][0]["source_records"][0]
    assert tuple((tmp_path / "runs" / body["run_id"]).glob("discovery-*.json"))
    assert tuple((tmp_path / "runs" / body["run_id"] / "raw").rglob("*.json"))


def test_discovery_and_metadata_use_repository_port(tmp_path: Path) -> None:
    repository = RecordingRepository()
    api = client(tmp_path, repository=repository)
    discovered = api.post("/knowledge/discovery/runs", json=payload()).json()
    metadata = api.post(f"/knowledge/discovery/runs/{discovered['run_id']}/metadata")
    assert metadata.status_code == 201
    assert repository.discovery_runs[0].run_id == discovered["run_id"]
    assert repository.metadata_runs[0].discovery_run_id == discovered["run_id"]


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
    extraction = api.post(f"/knowledge/documents/{acquired['document_id']}/extractions")
    assert extraction.status_code == 201
    assert object_store.reads[0].checksum_sha256 == acquired["content_hash"]
    assert repository.evidence_manifests[0][0].record_id == record["record_id"]
    assert repository.evidence_manifests[0][1].extraction_id == extraction.json()["extraction_id"]
    graph = api.post(f"/knowledge/extractions/{extraction.json()['extraction_id']}/graph")
    assert graph.status_code == 201
    assert repository.graphs[0][0].graph_id == graph.json()["graph_id"]
    assert repository.graphs[0][1] == repository.evidence_manifests[0][1].created_at
    theories = api.post("/knowledge/theories", json={"graph_ids": [graph.json()["graph_id"]]})
    assert theories.status_code == 201
    gaps = api.post(f"/knowledge/theories/{theories.json()['bundle_id']}/gaps")
    assert gaps.status_code == 201
    proposal = theories.json()["proposals"][0]
    validation = api.post(
        f"/knowledge/theories/{theories.json()['bundle_id']}/validations",
        json={
            "assessed_at": "2026-07-16T00:00:00Z",
            "search_completed_at": "2026-07-01T00:00:00Z",
            "max_age_days": 180,
            "risk_of_bias_by_theory": {proposal["theory_id"]: "low"},
        },
    )
    assert validation.status_code == 201
    publication = api.post(
        f"/knowledge/theories/{theories.json()['bundle_id']}/publications",
        json={
            "validation_report_id": validation.json()["report_id"],
            "kind": "literature_review", "generated_at": "2026-07-16T00:05:00Z",
        },
    )
    assert publication.status_code == 201
    assert [item["artifact_type"] for item in repository.artifacts] == [
        "theory_bundle", "gap_analysis", "validation_report", "publication_package",
    ]
    assert [item["status"] for item in repository.artifacts] == [
        "draft", "draft", "validated", "published",
    ]
    assert all(item["actor_id"] == "researcher@example" for item in repository.artifacts)
    assert len(object_store.byte_objects) == 1
    publication_id, representation = repository.publication_representations[0]
    assert publication_id == publication.json()["publication_id"]
    assert representation["representation_type"] == "markdown"
    assert representation["edition_type"] == "canonical"


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
    api = client(tmp_path)
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
    review = api.post(
        f"/knowledge/theories/{theories.json()['bundle_id']}/reviews",
        json={"theory_id": proposal["theory_id"], "decision": "accepted", "rationale": "Reviewed source", "occurred_at": "2026-07-15T00:00:00Z"},
    )
    assert review.status_code == 200
    assert review.json()["reviews"][0]["reviewer"] == "researcher@example"
    gaps = api.post(f"/knowledge/theories/{theories.json()['bundle_id']}/gaps")
    assert gaps.status_code == 201
    assert gaps.json()["gaps"][0]["gap_type"] == "limited_coverage"
    assert gaps.json()["hypotheses"][0]["advisory"] is True
    validation = api.post(
        f"/knowledge/theories/{theories.json()['bundle_id']}/validations",
        json={"assessed_at": "2026-07-15T00:00:00Z", "search_completed_at": "2026-07-01T00:00:00Z", "max_age_days": 180, "risk_of_bias_by_theory": {proposal["theory_id"]: "low"}},
    )
    assert validation.status_code == 201
    assert validation.json()["status"] == "incomplete"
    assert validation.json()["reviewer"] == "researcher@example"
    publication = api.post(
        f"/knowledge/theories/{theories.json()['bundle_id']}/publications",
        json={"validation_report_id": validation.json()["report_id"], "kind": "literature_review", "generated_at": "2026-07-15T00:00:00Z"},
    )
    assert publication.status_code == 201
    assert publication.json()["integrity_verified"] is True
    assert publication.json()["generated_by"] == "researcher@example"
    request["source_response_hash"] = "invented"
    assert api.post(f"/knowledge/discovery/runs/{discovered['run_id']}/documents", json=request).status_code == 422


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


def test_work_queue_is_readable_and_exposes_role_capabilities(tmp_path: Path) -> None:
    reviewer = client(tmp_path, "review", repository=RecordingRepository()).get(
        "/knowledge/projects/researchos-default/work-queue"
    )
    assert reviewer.status_code == 200
    assert reviewer.json()["counts"]["pending_reviews"] == 1
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
