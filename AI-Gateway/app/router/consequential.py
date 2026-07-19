"""Authenticated SGF-020C consequential-research control plane."""

from fastapi import APIRouter, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials

from app.knowledge.authentication import KnowledgeRole
from app.models.consequential import (
    AppealEventRequest, AuthorityQualificationRequest, ConflictDeclarationRequest,
    ConsequentialProfileRequest, DecisionAppealRequest, DecisionVoteRequest,
    EthicsApprovalRequest, HumanAuthorityRequest, ProfileActivationRequest,
    QuorumEvaluationRequest, ScientificDecisionRequest,
)
from app.router.knowledge_dependencies import authorize_any, bearer


router = APIRouter(
    prefix="/knowledge/governance/consequential",
    tags=["consequential-research-governance"],
)


def controls(request: Request):
    service = getattr(request.app.state, "consequential_controls", None)
    if service is None:
        raise HTTPException(
            status_code=503, detail="Consequential research controls unavailable"
        )
    return service


@router.get("/profiles")
def list_profiles(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
):
    authorize_any(
        request, credentials, KnowledgeRole.ADMIN, KnowledgeRole.AUDITOR,
        KnowledgeRole.REVIEWER, KnowledgeRole.PUBLISHER,
    )
    return {"profiles": controls(request).list_profiles()}


@router.post("/profiles", status_code=201)
def create_profile(
    req: ConsequentialProfileRequest,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
):
    principal = authorize_any(request, credentials, KnowledgeRole.ADMIN)
    try:
        result = controls(request).create_profile(
            req.model_dump(mode="json"), principal.actor_id
        )
        controls(request).record_audit_event(
            actor_id=principal.actor_id,
            event_type="consequential_profile_created",
            payload={"profile_id": result["profile_id"]},
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/authorities", status_code=201)
def register_authority(
    req: HumanAuthorityRequest,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
):
    principal = authorize_any(request, credentials, KnowledgeRole.ADMIN)
    try:
        result = controls(request).register_authority(
            req.model_dump(mode="json"), principal.actor_id
        )
        controls(request).record_audit_event(
            actor_id=principal.actor_id,
            event_type="human_authority_registered",
            payload={"authority_id": result["authority_id"]},
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/projects/{project_id}/activate", status_code=201)
def activate_profile(
    project_id: str,
    req: ProfileActivationRequest,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
):
    principal = authorize_any(request, credentials, KnowledgeRole.ADMIN)
    try:
        result = controls(request).activate_profile(
            project_id, str(req.profile_id), req.rationale,
            req.activated_at.isoformat(), principal.actor_id,
        )
        controls(request).record_audit_event(
            actor_id=principal.actor_id,
            event_type="consequential_profile_activated",
            payload={
                "project_id": project_id,
                "profile_id": str(req.profile_id),
                "assignment_id": result["assignment_id"],
            },
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/decisions/{decision_id}/readiness")
def decision_readiness(
    decision_id: str,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
):
    authorize_any(
        request, credentials, KnowledgeRole.ADMIN, KnowledgeRole.AUDITOR,
        KnowledgeRole.REVIEWER, KnowledgeRole.PUBLISHER,
    )
    result = controls(request).readiness(decision_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    return result


@router.post("/authorities/{authority_id}/qualifications", status_code=201)
def add_qualification(
    authority_id: str,
    req: AuthorityQualificationRequest,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
):
    principal = authorize_any(request, credentials, KnowledgeRole.ADMIN)
    try:
        return controls(request).add_qualification(
            authority_id, req.model_dump(mode="json"), principal.actor_id
        )
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/ethics", status_code=201)
def record_ethics(
    req: EthicsApprovalRequest,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
):
    principal = authorize_any(request, credentials, KnowledgeRole.ADMIN)
    try:
        return controls(request).record_ethics(
            req.model_dump(mode="json"), principal.actor_id
        )
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/decisions", status_code=201)
def open_decision(
    req: ScientificDecisionRequest,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
):
    principal = authorize_any(
        request, credentials, KnowledgeRole.ADMIN, KnowledgeRole.REVIEWER,
        KnowledgeRole.PUBLISHER,
    )
    try:
        return controls(request).open_decision(
            req.model_dump(mode="json"), principal.actor_id
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/decisions/{decision_id}/conflicts", status_code=201)
def declare_conflict(
    decision_id: str,
    req: ConflictDeclarationRequest,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
):
    principal = authorize_any(request, credentials, KnowledgeRole.REVIEWER)
    try:
        return controls(request).declare_conflict(
            decision_id, req.model_dump(mode="json"), principal.actor_id
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/decisions/{decision_id}/votes", status_code=201)
def vote(
    decision_id: str,
    req: DecisionVoteRequest,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
):
    principal = authorize_any(request, credentials, KnowledgeRole.REVIEWER)
    try:
        return controls(request).vote(
            decision_id, req.model_dump(mode="json"), principal.actor_id
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/decisions/{decision_id}/evaluate", status_code=201)
def evaluate_quorum(
    decision_id: str,
    req: QuorumEvaluationRequest,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
):
    principal = authorize_any(
        request, credentials, KnowledgeRole.ADMIN, KnowledgeRole.AUDITOR,
    )
    try:
        return controls(request).evaluate_quorum(
            decision_id, req.evaluated_at.isoformat(), principal.actor_id
        )
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/decisions/{decision_id}/appeals", status_code=201)
def file_appeal(
    decision_id: str,
    req: DecisionAppealRequest,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
):
    principal = authorize_any(
        request, credentials, KnowledgeRole.ADMIN, KnowledgeRole.REVIEWER,
        KnowledgeRole.PUBLISHER,
    )
    try:
        return controls(request).file_appeal(
            decision_id, req.model_dump(mode="json"), principal.actor_id
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/appeals/{appeal_id}/events", status_code=201)
def record_appeal_event(
    appeal_id: str,
    req: AppealEventRequest,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
):
    principal = authorize_any(
        request, credentials, KnowledgeRole.ADMIN, KnowledgeRole.REVIEWER,
    )
    try:
        return controls(request).record_appeal_event(
            appeal_id, req.model_dump(mode="json"), principal.actor_id
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/revalidation")
def revalidation_queue(
    request: Request,
    project_id: str | None = None,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
):
    authorize_any(
        request, credentials, KnowledgeRole.ADMIN, KnowledgeRole.AUDITOR,
        KnowledgeRole.REVIEWER,
    )
    return {
        "items": controls(request).revalidation_queue(project_id),
        "fail_closed": True,
    }
