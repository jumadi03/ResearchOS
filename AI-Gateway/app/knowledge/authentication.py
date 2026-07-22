"""Fail-closed authentication for Scientific Knowledge APIs."""

from dataclasses import dataclass
from enum import StrEnum
from hmac import compare_digest
from typing import Any


class KnowledgeRole(StrEnum):
    ADMIN = "admin"
    DISCOVERER = "discoverer"
    AUDITOR = "auditor"
    REVIEWER = "reviewer"
    INDEXER = "indexer"
    PUBLISHER = "publisher"


@dataclass(frozen=True, slots=True)
class KnowledgePrincipal:
    actor_id: str
    roles: frozenset[KnowledgeRole]

    def has_role(self, role: KnowledgeRole) -> bool:
        return role in self.roles


@dataclass(frozen=True, slots=True)
class KnowledgeAuthenticator:
    principals_by_token: dict[str, Any]

    def __post_init__(self) -> None:
        normalized = {}
        if not isinstance(self.principals_by_token, dict):
            raise ValueError("Knowledge API principal configuration must be an object")
        for token, value in self.principals_by_token.items():
            if not isinstance(token, str) or not token or not isinstance(value, dict):
                raise ValueError("Invalid Knowledge API principal")
            actor_id = value.get("actor_id")
            roles = value.get("roles")
            if not isinstance(actor_id, str) or not actor_id.strip():
                raise ValueError("Knowledge principal actor_id is required")
            if not isinstance(roles, list) or not roles:
                raise ValueError("Knowledge principal roles must be a non-empty list")
            normalized[token] = KnowledgePrincipal(
                actor_id.strip(), frozenset(KnowledgeRole(role) for role in roles)
            )
        object.__setattr__(self, "principals_by_token", normalized)

    def authenticate(self, authorization: str | None) -> KnowledgePrincipal:
        if not authorization or not authorization.startswith("Bearer "):
            raise PermissionError("A Bearer token is required")
        supplied = authorization[7:]
        principal = None
        for token, configured in self.principals_by_token.items():
            if compare_digest(supplied, token):
                principal = configured
        if principal is None:
            raise PermissionError("Invalid Knowledge API credentials")
        return principal
