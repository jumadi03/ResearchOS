"""Read-only path resolution for a finalized Repository Policy Bundle."""

from fnmatch import fnmatchcase
from pathlib import PurePosixPath

from .policy_models import (
    Policy,
    RepositoryLifecyclePolicy,
    RepositoryOwnershipPolicy,
    RepositoryPolicyBundle,
    RepositoryPolicyException,
)


class RepositoryPolicyConflict(ValueError):
    """Raised when exclusive policies disagree for the same path."""


class RepositoryPolicyRegistry:
    def __init__(self, bundle: RepositoryPolicyBundle) -> None:
        if not bundle.verify():
            raise ValueError("Repository policy bundle integrity verification failed")
        self.bundle = bundle
        self._by_id = {item.policy_id: item for item in bundle.policies}

    @staticmethod
    def _normalize(path: str) -> str:
        normalized = path.replace("\\", "/")
        item = PurePosixPath(normalized)
        if (
            not normalized
            or item.is_absolute()
            or any(part in {"", ".", ".."} for part in item.parts)
        ):
            raise ValueError(f"Unsafe repository-relative path: {path}")
        return item.as_posix()

    @staticmethod
    def _matches(path: str, patterns: tuple[str, ...]) -> bool:
        return any(fnmatchcase(path, pattern) for pattern in patterns)

    def get(self, policy_id: str) -> Policy | None:
        return self._by_id.get(policy_id)

    def resolve(self, path: str) -> tuple[Policy, ...]:
        normalized = self._normalize(path)
        return tuple(
            item for item in self.bundle.policies
            if self._matches(normalized, item.path_patterns)
        )

    def resolve_ownership(self, path: str) -> RepositoryOwnershipPolicy | None:
        matches = tuple(
            item for item in self.resolve(path)
            if isinstance(item, RepositoryOwnershipPolicy)
        )
        identities = {
            (item.owner, item.subsystem, item.engine, item.capability)
            for item in matches
        }
        if len(identities) > 1:
            raise RepositoryPolicyConflict(
                f"Conflicting repository ownership policies for {path}"
            )
        return matches[0] if matches else None

    def resolve_lifecycle(self, path: str) -> RepositoryLifecyclePolicy | None:
        matches = tuple(
            item for item in self.resolve(path)
            if isinstance(item, RepositoryLifecyclePolicy)
        )
        if len({item.lifecycle for item in matches}) > 1:
            raise RepositoryPolicyConflict(
                f"Conflicting repository lifecycle policies for {path}"
            )
        return matches[0] if matches else None

    def resolve_exceptions(
        self, path: str, policy_ids: tuple[str, ...],
    ) -> tuple[RepositoryPolicyException, ...]:
        normalized = self._normalize(path)
        applicable = set(policy_ids)
        return tuple(
            item for item in self.bundle.exceptions
            if applicable.intersection(item.policy_ids)
            and self._matches(normalized, item.path_patterns)
        )
