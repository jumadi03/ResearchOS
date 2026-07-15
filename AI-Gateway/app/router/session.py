"""Human login/session boundary for the ResearchOS workspace."""

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field


router = APIRouter(prefix="/auth", tags=["workspace-session"])
COOKIE_NAME = "researchos_session"


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=3, max_length=128)
    password: str = Field(min_length=12, max_length=1024)


@router.post("/login")
def login(req: LoginRequest, request: Request, response: Response):
    try:
        token, csrf, expires_at, user = request.app.state.workspace_sessions.login(
            req.username, req.password, request.headers.get("user-agent"),
        )
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    response.set_cookie(
        COOKIE_NAME, token, httponly=True, secure=False, samesite="strict",
        max_age=request.app.state.workspace_sessions.session_hours * 3600,
        path="/",
    )
    return {"user": user, "csrf_token": csrf, "expires_at": expires_at.isoformat()}


@router.get("/session")
def current_session(request: Request):
    try:
        principal, expires_at, csrf = request.app.state.workspace_sessions.refresh_csrf(
            request.cookies.get(COOKIE_NAME)
        )
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return {
        "user": {"username": principal.actor_id, "display_name": principal.actor_id,
                 "roles": sorted(role.value for role in principal.roles)},
        "expires_at": expires_at.isoformat(),
        "csrf_token": csrf,
    }


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response):
    try:
        request.app.state.workspace_sessions.authenticate(
            request.cookies.get(COOKIE_NAME), request.headers.get("x-csrf-token"),
            require_csrf=True,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    request.app.state.workspace_sessions.logout(request.cookies.get(COOKIE_NAME))
    response.delete_cookie(COOKIE_NAME, path="/")
