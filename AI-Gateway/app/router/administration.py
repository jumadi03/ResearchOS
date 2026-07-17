"""Administrator-only operational control plane."""

import json

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from app.knowledge.authentication import KnowledgeRole
from app.router.session import COOKIE_NAME

router = APIRouter(prefix="/admin", tags=["administration"])


class UserStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str


def _admin(request: Request, *, mutation: bool = False):
    authorization = request.headers.get("authorization")
    try:
        if authorization:
            principal = request.app.state.knowledge_authenticator.authenticate(authorization)
        else:
            sessions = request.app.state.workspace_sessions
            if sessions is None:
                raise PermissionError("A Bearer token is required")
            principal, _ = sessions.authenticate(
                request.cookies.get(COOKIE_NAME), request.headers.get("x-csrf-token"),
                require_csrf=mutation,
            )
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    if not principal.has_role(KnowledgeRole.ADMIN):
        raise HTTPException(status_code=403, detail="Administrator role is required")
    return principal


@router.get("/overview")
def overview(request: Request):
    _admin(request)
    return request.app.state.workspace_sessions.administration_overview()


@router.get("/users")
def users(request: Request):
    _admin(request)
    return {"items": request.app.state.workspace_sessions.administration_users()}


@router.post("/users/{user_id}/status")
def user_status(user_id: str, body: UserStatusRequest, request: Request):
    principal = _admin(request, mutation=True)
    try:
        return request.app.state.workspace_sessions.set_user_status(user_id, body.status, principal.actor_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/users/{user_id}/sessions/revoke")
def revoke_sessions(user_id: str, request: Request):
    principal = _admin(request, mutation=True)
    try:
        return request.app.state.workspace_sessions.revoke_user_sessions(user_id, principal.actor_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/audit")
def audit(request: Request, limit: int = 50):
    _admin(request)
    return {"items": request.app.state.workspace_sessions.administration_audit(max(1, min(limit, 200)))}


@router.get("/recovery")
def recovery(request: Request):
    _admin(request)
    return request.app.state.workspace_sessions.recovery_status()


@router.get("/repository-dashboard")
def repository_dashboard(request: Request):
    _admin(request)
    try:
        snapshot = request.app.state.repository_dashboard_service.snapshot()
    except ValueError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Repository dashboard unavailable: {exc}",
        ) from exc
    return json.loads(snapshot.to_json())
