"""Shared authentication dependencies for scientific knowledge routers."""

from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.knowledge.authentication import KnowledgeRole


bearer = HTTPBearer(auto_error=False)


def authorize(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
    role: KnowledgeRole | None = KnowledgeRole.DISCOVERER,
):
    try:
        if credentials and credentials.credentials:
            authorization = f"{credentials.scheme} {credentials.credentials}"
            principal = request.app.state.knowledge_authenticator.authenticate(
                authorization
            )
        else:
            require_csrf = request.method not in {"GET", "HEAD", "OPTIONS"}
            manager = getattr(request.app.state, "workspace_sessions", None)
            if manager is None:
                raise PermissionError("A Bearer token is required")
            principal, _ = manager.authenticate(
                request.cookies.get("researchos_session"),
                request.headers.get("x-csrf-token"),
                require_csrf=require_csrf,
            )
    except PermissionError as exc:
        raise HTTPException(
            status_code=401,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    if role is not None and not principal.has_role(role):
        raise HTTPException(status_code=403, detail=f"Role required: {role.value}")
    return principal


def authorize_any(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
    *roles: KnowledgeRole,
):
    """Authorize an authenticated principal holding at least one listed role."""
    principal = authorize(request, credentials, None)
    if roles and not any(principal.has_role(role) for role in roles):
        expected = ", ".join(role.value for role in roles)
        raise HTTPException(status_code=403, detail=f"One role required: {expected}")
    return principal
