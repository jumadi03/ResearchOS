"""Typed, immutable Repository Policy Registry contracts for FMA-002."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import date
from enum import StrEnum
from hashlib import sha256
import json
from pathlib import PurePosixPath
import re

from app.architecture.schema import REPOSITORY_POLICY_BUNDLE_SCHEMA

from .models import RepositoryFileClassification


def _valid_patterns(patterns: tuple[str, ...]) -> bool:
    return bool(patterns) and all(
        bool(pattern)
        and "\\" not in pattern
        and not PurePosixPath(pattern).is_absolute()
        and ".." not in PurePosixPath(pattern).parts
        for pattern in patterns
    )


def _valid_policy_identity(
    policy_id: str, version: str, patterns: tuple[str, ...], rationale: str,
) -> bool:
    return bool(
        policy_id.strip()
        and version.strip()
        and rationale.strip()
        and _valid_patterns(patterns)
    )


class RepositoryLifecycle(StrEnum):
    RETAIN = "retain"
    DEPRECATE = "deprecate"
    ARCHIVE = "archive"
    REGENERATE = "regenerate"
    EXPIRE = "expire"
    DELETE = "delete"
    LOCAL_ONLY = "local_only"


@dataclass(frozen=True, slots=True)
class RepositoryOwnershipPolicy:
    policy_id: str
    version: str
    path_patterns: tuple[str, ...]
    owner: str
    subsystem: str
    engine: str
    capability: str
    rationale: str

    def verify(self) -> bool:
        return (
            _valid_policy_identity(
                self.policy_id, self.version, self.path_patterns, self.rationale,
            )
            and all(
                value.strip()
                for value in (
                    self.owner, self.subsystem, self.engine, self.capability,
                )
            )
        )


@dataclass(frozen=True, slots=True)
class RepositoryPlacementPolicy:
    policy_id: str
    version: str
    path_patterns: tuple[str, ...]
    allowed_classifications: tuple[RepositoryFileClassification, ...]
    allowed_extensions: tuple[str, ...]
    forbidden_extensions: tuple[str, ...]
    rationale: str

    def verify(self) -> bool:
        extensions = (*self.allowed_extensions, *self.forbidden_extensions)
        return (
            _valid_policy_identity(
                self.policy_id, self.version, self.path_patterns, self.rationale,
            )
            and bool(self.allowed_classifications)
            and len(set(self.allowed_classifications)) == len(
                self.allowed_classifications
            )
            and all(
                item == item.lower() and (not item or item.startswith("."))
                for item in extensions
            )
            and not set(self.allowed_extensions).intersection(
                self.forbidden_extensions
            )
        )


@dataclass(frozen=True, slots=True)
class RepositoryNamingPolicy:
    policy_id: str
    version: str
    path_patterns: tuple[str, ...]
    name_pattern: str
    examples: tuple[str, ...]
    rationale: str

    def verify(self) -> bool:
        try:
            re.compile(self.name_pattern)
        except re.error:
            return False
        return (
            _valid_policy_identity(
                self.policy_id, self.version, self.path_patterns, self.rationale,
            )
            and bool(self.name_pattern and self.examples)
        )


@dataclass(frozen=True, slots=True)
class RepositoryLifecyclePolicy:
    policy_id: str
    version: str
    path_patterns: tuple[str, ...]
    lifecycle: RepositoryLifecycle
    review_condition: str
    rationale: str

    def verify(self) -> bool:
        return (
            _valid_policy_identity(
                self.policy_id, self.version, self.path_patterns, self.rationale,
            )
            and bool(self.review_condition.strip())
        )


@dataclass(frozen=True, slots=True)
class RepositoryPolicyException:
    exception_id: str
    policy_ids: tuple[str, ...]
    path_patterns: tuple[str, ...]
    rationale: str
    approved_by: str
    approved_at: str
    expires_at: str | None = None
    review_condition: str | None = None

    def verify(self) -> bool:
        try:
            approved = date.fromisoformat(self.approved_at)
            expires = date.fromisoformat(self.expires_at) if self.expires_at else None
        except ValueError:
            return False
        return (
            bool(
                self.exception_id.strip()
                and self.policy_ids
                and len(set(self.policy_ids)) == len(self.policy_ids)
                and self.rationale.strip()
                and self.approved_by.strip()
            )
            and _valid_patterns(self.path_patterns)
            and bool(self.expires_at or (self.review_condition or "").strip())
            and (expires is None or expires >= approved)
        )


Policy = (
    RepositoryOwnershipPolicy
    | RepositoryPlacementPolicy
    | RepositoryNamingPolicy
    | RepositoryLifecyclePolicy
)


@dataclass(frozen=True, slots=True)
class RepositoryPolicyBundle:
    bundle_id: str
    project_name: str
    version: str
    source_revision: str
    ownership_policies: tuple[RepositoryOwnershipPolicy, ...] = ()
    placement_policies: tuple[RepositoryPlacementPolicy, ...] = ()
    naming_policies: tuple[RepositoryNamingPolicy, ...] = ()
    lifecycle_policies: tuple[RepositoryLifecyclePolicy, ...] = ()
    exceptions: tuple[RepositoryPolicyException, ...] = ()
    schema_version: str = "1.0"
    content_hash: str = ""

    @property
    def policies(self) -> tuple[Policy, ...]:
        return (
            *self.ownership_policies,
            *self.placement_policies,
            *self.naming_policies,
            *self.lifecycle_policies,
        )

    def canonical_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "project_name": self.project_name,
            "version": self.version,
            "source_revision": self.source_revision,
            "ownership_policies": [
                asdict(item)
                for item in sorted(
                    self.ownership_policies, key=lambda item: item.policy_id,
                )
            ],
            "placement_policies": [
                asdict(item)
                for item in sorted(
                    self.placement_policies, key=lambda item: item.policy_id,
                )
            ],
            "naming_policies": [
                asdict(item)
                for item in sorted(
                    self.naming_policies, key=lambda item: item.policy_id,
                )
            ],
            "lifecycle_policies": [
                asdict(item)
                for item in sorted(
                    self.lifecycle_policies, key=lambda item: item.policy_id,
                )
            ],
            "exceptions": [
                asdict(item)
                for item in sorted(
                    self.exceptions, key=lambda item: item.exception_id,
                )
            ],
        }

    def calculate_content_hash(self) -> str:
        encoded = json.dumps(
            self.canonical_payload(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return sha256(encoded).hexdigest()

    def finalized(self) -> "RepositoryPolicyBundle":
        content_hash = self.calculate_content_hash()
        return replace(
            self,
            bundle_id=f"repository-policy:{self.version}:{content_hash[:16]}",
            ownership_policies=tuple(sorted(
                self.ownership_policies, key=lambda item: item.policy_id,
            )),
            placement_policies=tuple(sorted(
                self.placement_policies, key=lambda item: item.policy_id,
            )),
            naming_policies=tuple(sorted(
                self.naming_policies, key=lambda item: item.policy_id,
            )),
            lifecycle_policies=tuple(sorted(
                self.lifecycle_policies, key=lambda item: item.policy_id,
            )),
            exceptions=tuple(sorted(
                self.exceptions, key=lambda item: item.exception_id,
            )),
            content_hash=content_hash,
        )

    def verify(self) -> bool:
        policy_ids = [item.policy_id for item in self.policies]
        exception_ids = [item.exception_id for item in self.exceptions]
        known = set(policy_ids)
        return (
            bool(
                self.project_name.strip()
                and self.version.strip()
                and self.source_revision.strip()
                and self.policies
            )
            and len(policy_ids) == len(known)
            and len(exception_ids) == len(set(exception_ids))
            and all(item.verify() for item in self.policies)
            and all(
                item.verify() and set(item.policy_ids).issubset(known)
                for item in self.exceptions
            )
            and self == self.finalized()
        )

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(
            {
                "bundle_id": self.bundle_id,
                "content_hash": self.content_hash,
                **self.canonical_payload(),
            },
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    @classmethod
    def from_json(cls, value: str) -> "RepositoryPolicyBundle":
        payload = json.loads(value)
        REPOSITORY_POLICY_BUNDLE_SCHEMA.require_readable(
            payload.get("schema_version", "")
        )
        bundle = cls(
            bundle_id=payload.get("bundle_id", ""),
            project_name=payload["project_name"],
            version=payload["version"],
            source_revision=payload["source_revision"],
            ownership_policies=tuple(
                RepositoryOwnershipPolicy(
                    **{
                        **item,
                        "path_patterns": tuple(item["path_patterns"]),
                    }
                )
                for item in payload.get("ownership_policies", ())
            ),
            placement_policies=tuple(
                RepositoryPlacementPolicy(
                    **{
                        **item,
                        "path_patterns": tuple(item["path_patterns"]),
                        "allowed_classifications": tuple(
                            RepositoryFileClassification(value)
                            for value in item["allowed_classifications"]
                        ),
                        "allowed_extensions": tuple(item["allowed_extensions"]),
                        "forbidden_extensions": tuple(item["forbidden_extensions"]),
                    }
                )
                for item in payload.get("placement_policies", ())
            ),
            naming_policies=tuple(
                RepositoryNamingPolicy(
                    **{
                        **item,
                        "path_patterns": tuple(item["path_patterns"]),
                        "examples": tuple(item["examples"]),
                    }
                )
                for item in payload.get("naming_policies", ())
            ),
            lifecycle_policies=tuple(
                RepositoryLifecyclePolicy(
                    **{
                        **item,
                        "path_patterns": tuple(item["path_patterns"]),
                        "lifecycle": RepositoryLifecycle(item["lifecycle"]),
                    }
                )
                for item in payload.get("lifecycle_policies", ())
            ),
            exceptions=tuple(
                RepositoryPolicyException(
                    **{
                        **item,
                        "policy_ids": tuple(item["policy_ids"]),
                        "path_patterns": tuple(item["path_patterns"]),
                    }
                )
                for item in payload.get("exceptions", ())
            ),
            schema_version=payload.get("schema_version", ""),
            content_hash=payload.get("content_hash", ""),
        )
        expected = bundle.finalized()
        if (
            not bundle.content_hash
            or not bundle.bundle_id
            or bundle.content_hash != expected.content_hash
            or bundle.bundle_id != expected.bundle_id
            or not expected.verify()
        ):
            raise ValueError("Repository policy bundle identity or content is invalid")
        return expected
