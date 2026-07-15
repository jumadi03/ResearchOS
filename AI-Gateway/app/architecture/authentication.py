"""Fail-closed authentication for internal architecture governance APIs."""

from dataclasses import dataclass
from enum import StrEnum
from hmac import compare_digest
from typing import Any


class ArchitectureRole(StrEnum):
    SCANNER = "scanner"
    LAW_ADMIN = "law_admin"
    REVIEWER = "reviewer"
    APPROVER = "approver"
    PUBLISHER = "publisher"
    AUDITOR = "auditor"


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    actor_id: str
    roles: frozenset[ArchitectureRole]

    def has_role(self, role: ArchitectureRole) -> bool:
        return role in self.roles


@dataclass(frozen=True, slots=True)
class BearerTokenAuthenticator:
    """Resolve opaque bearer tokens to server-configured actor identities."""

    principals_by_token: dict[str, Any]

    def __post_init__(self) -> None:
        normalized: dict[str, AuthenticatedPrincipal] = {}
        if not isinstance(self.principals_by_token, dict):
            raise ValueError("Architecture API principal configuration must be an object")
        for token, value in self.principals_by_token.items():
            if not isinstance(token, str) or not token:
                raise ValueError("Architecture API tokens must be non-empty strings")
            if not isinstance(value, dict):
                raise ValueError("Each architecture principal must be an object")
            actor_id = value.get("actor_id")
            roles = value.get("roles")
            if not isinstance(actor_id, str) or not actor_id.strip():
                raise ValueError("Architecture principal actor_id is required")
            if not isinstance(roles, list) or not roles:
                raise ValueError("Architecture principal roles must be a non-empty list")
            normalized[token] = AuthenticatedPrincipal(
                actor_id=actor_id,
                roles=frozenset(ArchitectureRole(role) for role in roles),
            )
        object.__setattr__(self, "principals_by_token", normalized)

    def authenticate(self, authorization: str | None) -> AuthenticatedPrincipal:
        if not authorization or not authorization.startswith("Bearer "):
            raise PermissionError("A Bearer token is required")
        supplied = authorization[7:]
        if not supplied:
            raise PermissionError("A Bearer token is required")
        principal: AuthenticatedPrincipal | None = None
        for configured_token, configured_principal in self.principals_by_token.items():
            if compare_digest(supplied, configured_token):
                principal = configured_principal
        if principal is None:
            raise PermissionError("Invalid architecture API credentials")
        return principal
