"""Authenticated HTTP boundary for SK-001A."""

from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials

from app.knowledge.authentication import KnowledgeRole
from app.knowledge.models import ScientificQuestion, SearchPlan
from app.models.knowledge import (
    DocumentAcquisitionRequest, LiteratureDiscoveryRequest,
    ArtifactTransitionRequest, EvidenceReviewRequest, PublicationRequest,
    SemanticIndexRequest, SemanticSearchRequest, TheoryBuildRequest,
    TheoryReviewRequest,
    TheoryValidationRequest,
)
from app.knowledge.ingestion.models import AccessStatus, DocumentCandidate
from app.router.knowledge_dependencies import authorize, bearer
from app.router.knowledge_workspace import router as workspace_router


router = APIRouter(prefix="/knowledge", tags=["scientific-knowledge"])
router.include_router(workspace_router)
DISCOVERY_PROVIDERS = ("openalex", "crossref", "semantic_scholar")

@router.get("/discovery/capabilities")
def discovery_capabilities(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
):
    authorize(request, credentials, None)
    return {
        "providers": list(DISCOVERY_PROVIDERS),
        "limit_per_provider": {"default": 25, "minimum": 1, "maximum": 1000},
        "acquisition_access_statuses": ["open", "restricted", "unavailable"],
        "workflow": ["discover", "collect_metadata", "acquire", "extract"],
    }


@router.post("/discovery/runs", status_code=201)
def discover(
    req: LiteratureDiscoveryRequest,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
):
    authorize(request, credentials)
    try:
        question = ScientificQuestion(**req.question.model_dump())
        plan_data = req.search_plan.model_dump()
        plan_data["providers"] = tuple(plan_data["providers"])
        plan = SearchPlan(**plan_data)
        run, snapshot = request.app.state.knowledge_service.discover(question, plan)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    result = asdict(run)
    for record in result["records"]:
        for source in record["source_records"]:
            source.pop("raw", None)
    result["snapshot"] = snapshot.name
    return result


@router.post("/discovery/runs/{run_id}/metadata", status_code=201)
def collect_metadata(
    run_id: str,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
):
    authorize(request, credentials)
    try:
        run, snapshot = request.app.state.knowledge_service.collect_metadata(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    result = asdict(run)
    result["snapshot"] = snapshot.name
    return result


@router.post("/discovery/runs/{run_id}/documents", status_code=201)
def acquire_document(
    run_id: str,
    req: DocumentAcquisitionRequest,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
):
    authorize(request, credentials)
    try:
        candidate = DocumentCandidate(
            req.record_id, req.url, AccessStatus(req.access_status), req.license,
            req.source_provider, req.source_response_hash,
        )
        document, manifest = request.app.state.knowledge_service.acquire_document(
            run_id, candidate
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    result = asdict(document)
    result["manifest"] = manifest.name
    result["integrity_verified"] = request.app.state.knowledge_service.document_registry.verify(document)
    return result


@router.post("/documents/{document_id}/extractions", status_code=201)
def extract_document(
    document_id: str,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
):
    authorize(request, credentials)
    try:
        manifest, snapshot = request.app.state.knowledge_service.extract_document(document_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    result = asdict(manifest)
    result["snapshot"] = snapshot.name
    return result


@router.post("/extractions/{extraction_id}/graph", status_code=201)
def build_knowledge_graph(
    extraction_id: str,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
):
    authorize(request, credentials)
    try:
        graph, snapshot = request.app.state.knowledge_service.build_knowledge_graph(
            extraction_id
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    result = asdict(graph)
    result["snapshot"] = snapshot.name
    result["integrity_verified"] = graph.verify()
    return result


@router.post("/evidence/{evidence_object_id}/reviews", status_code=201)
def review_evidence(
    evidence_object_id: str,
    req: EvidenceReviewRequest,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
):
    principal = authorize(request, credentials, KnowledgeRole.REVIEWER)
    try:
        event = request.app.state.knowledge_service.review_evidence(
            evidence_object_id, decision=req.decision, reviewer=principal.actor_id,
            rationale=req.rationale, occurred_at=req.occurred_at,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return asdict(event)


@router.post("/theories", status_code=201)
def build_theories(req: TheoryBuildRequest, request: Request, credentials: HTTPAuthorizationCredentials | None = Security(bearer)):
    principal = authorize(request, credentials)
    try:
        bundle, snapshot = request.app.state.knowledge_service.build_theories(
            tuple(req.graph_ids), generated_by=principal.actor_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    result = asdict(bundle); result["snapshot"] = snapshot.name
    return result


@router.post("/theories/{bundle_id}/reviews")
def review_theory(bundle_id: str, req: TheoryReviewRequest, request: Request, credentials: HTTPAuthorizationCredentials | None = Security(bearer)):
    principal = authorize(request, credentials, KnowledgeRole.REVIEWER)
    try:
        bundle, snapshot = request.app.state.knowledge_service.review_theory(
            bundle_id, theory_id=req.theory_id, decision=req.decision,
            reviewer=principal.actor_id, rationale=req.rationale, occurred_at=req.occurred_at,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    result = asdict(bundle); result["snapshot"] = snapshot.name
    return result


@router.post("/theories/{bundle_id}/gaps", status_code=201)
def detect_research_gaps(bundle_id: str, request: Request, credentials: HTTPAuthorizationCredentials | None = Security(bearer)):
    principal = authorize(request, credentials)
    try:
        analysis, snapshot = request.app.state.knowledge_service.detect_research_gaps(
            bundle_id, generated_by=principal.actor_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    result = asdict(analysis); result["snapshot"] = snapshot.name
    return result


@router.post("/artifacts/{artifact_id}/transitions", status_code=201)
def transition_artifact(
    artifact_id: str, req: ArtifactTransitionRequest, request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
):
    principal = authorize(request, credentials, KnowledgeRole.REVIEWER)
    try:
        event = request.app.state.knowledge_service.transition_artifact(
            artifact_id, to_status=req.to_status, actor_id=principal.actor_id,
            rationale=req.rationale, occurred_at=req.occurred_at,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return asdict(event)


@router.post("/semantic-index/jobs", status_code=202)
def enqueue_semantic_index(
    req: SemanticIndexRequest, request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
):
    authorize(request, credentials, KnowledgeRole.INDEXER)
    try:
        job = request.app.state.knowledge_service.enqueue_semantic_index(
            object_type=req.object_type, object_id=req.object_id, model=req.model,
            embedding=tuple(req.embedding), metadata=req.metadata,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return asdict(job)


@router.post("/semantic-search")
def semantic_search(
    req: SemanticSearchRequest, request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
):
    authorize(request, credentials)
    try:
        hits = request.app.state.knowledge_service.semantic_search(
            model=req.model, query_embedding=tuple(req.query_embedding),
            limit=req.limit, object_types=tuple(req.object_types),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"hits": [asdict(hit) for hit in hits], "count": len(hits)}


@router.post("/theories/{bundle_id}/validations", status_code=201)
def validate_theories(bundle_id: str, req: TheoryValidationRequest, request: Request, credentials: HTTPAuthorizationCredentials | None = Security(bearer)):
    principal = authorize(request, credentials, KnowledgeRole.REVIEWER)
    try:
        report, snapshot = request.app.state.knowledge_service.validate_theories(
            bundle_id, assessed_at=req.assessed_at,
            search_completed_at=req.search_completed_at,
            max_age_days=req.max_age_days,
            risk_of_bias_by_theory=req.risk_of_bias_by_theory,
            reviewer=principal.actor_id,
        )
    except KeyError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=422, detail=str(exc)) from exc
    result = asdict(report); result["snapshot"] = snapshot.name
    return result


@router.post("/theories/{bundle_id}/publications", status_code=201)
def publish(bundle_id: str, req: PublicationRequest, request: Request, credentials: HTTPAuthorizationCredentials | None = Security(bearer)):
    principal = authorize(request, credentials, KnowledgeRole.REVIEWER)
    try:
        package, location = request.app.state.knowledge_service.publish(
            bundle_id, validation_report_id=req.validation_report_id,
            kind=req.kind, generated_at=req.generated_at,
            generated_by=principal.actor_id,
        )
    except KeyError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=422, detail=str(exc)) from exc
    result = asdict(package.manifest)
    result["package_content_hash"] = package.content_hash
    result["location"] = location.name
    result["integrity_verified"] = package.verify()
    return result
