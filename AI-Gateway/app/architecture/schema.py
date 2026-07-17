"""Central schema compatibility and explicit migration contracts."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import re
from typing import Callable


class SchemaVersionError(ValueError):
    """Raised when persisted data uses an unsupported schema version."""


@dataclass(frozen=True, order=True, slots=True)
class SchemaVersion:
    major: int
    minor: int

    @classmethod
    def parse(cls, value: str) -> "SchemaVersion":
        match = re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)", value)
        if not match:
            raise SchemaVersionError(f"Invalid schema version: {value!r}")
        return cls(int(match.group(1)), int(match.group(2)))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}"


@dataclass(frozen=True, slots=True)
class SchemaPolicy:
    artifact: str
    current: str
    readable: frozenset[str]

    def require_readable(self, value: str) -> None:
        version = SchemaVersion.parse(value)
        current = SchemaVersion.parse(self.current)
        if str(version) not in self.readable:
            direction = "future" if version > current else "unsupported"
            raise SchemaVersionError(
                f"{self.artifact} schema {value} is {direction}; "
                f"current schema is {self.current}"
            )


Migration = Callable[[dict[str, object]], dict[str, object]]


@dataclass(frozen=True, slots=True)
class SchemaMigrationRegistry:
    policy: SchemaPolicy
    migrations: dict[str, tuple[str, Migration]]

    def migrate(
        self,
        payload: dict[str, object],
        *,
        source_version: str,
    ) -> dict[str, object]:
        self.policy.require_readable(source_version)
        migrated = deepcopy(payload)
        version = source_version
        visited: set[str] = set()
        while version != self.policy.current:
            if version in visited or version not in self.migrations:
                raise SchemaVersionError(
                    f"No migration path for {self.policy.artifact} "
                    f"from {source_version} to {self.policy.current}"
                )
            visited.add(version)
            next_version, transform = self.migrations[version]
            migrated = transform(migrated)
            migrated["schema_version"] = next_version
            version = next_version
        return migrated


GRAPH_SCHEMA = SchemaPolicy(
    "Architecture Graph", "1.1", frozenset({"1.0", "1.1"})
)
LAW_BUNDLE_SCHEMA = SchemaPolicy("Law Bundle", "1.0", frozenset({"1.0"}))
REPOSITORY_POLICY_BUNDLE_SCHEMA = SchemaPolicy(
    "Repository Policy Bundle", "1.0", frozenset({"1.0"})
)
FILE_REGISTRY_SCHEMA = SchemaPolicy(
    "Repository File Registry", "1.0", frozenset({"1.0"})
)
REPOSITORY_VERIFICATION_SCHEMA = SchemaPolicy(
    "Repository Verification Report", "1.0", frozenset({"1.0"})
)
REPOSITORY_HEALTH_SCHEMA = SchemaPolicy(
    "Repository Health Report", "1.0", frozenset({"1.0"})
)
REPOSITORY_DASHBOARD_SCHEMA = SchemaPolicy(
    "Repository Dashboard Snapshot", "1.0", frozenset({"1.0"})
)
REPOSITORY_EVOLUTION_SCHEMA = SchemaPolicy(
    "Repository Evolution Plan", "1.0", frozenset({"1.0"})
)
REPOSITORY_EVOLUTION_PREFLIGHT_SCHEMA = SchemaPolicy(
    "Repository Evolution Preflight", "1.0", frozenset({"1.0"})
)
REPOSITORY_EVOLUTION_DRY_RUN_SCHEMA = SchemaPolicy(
    "Repository Evolution Dry Run", "1.0", frozenset({"1.0"})
)
COMPLIANCE_SCHEMA = SchemaPolicy(
    "Compliance Report", "1.0", frozenset({"0.9", "1.0"})
)
REVIEW_SCHEMA = SchemaPolicy("Review Session", "1.0", frozenset({"0.9", "1.0"}))
ARC_SCHEMA = SchemaPolicy("ARC Manifest", "1.1", frozenset({"1.0", "1.1"}))


def _identity(payload: dict[str, object]) -> dict[str, object]:
    return payload


COMPLIANCE_MIGRATIONS = SchemaMigrationRegistry(
    COMPLIANCE_SCHEMA,
    {"0.9": ("1.0", _identity)},
)
REVIEW_MIGRATIONS = SchemaMigrationRegistry(
    REVIEW_SCHEMA,
    {"0.9": ("1.0", _identity)},
)


def _arc_1_0_to_1_1(payload: dict[str, object]) -> dict[str, object]:
    payload.setdefault("generated_by", "legacy:unknown")
    return payload


ARC_MIGRATIONS = SchemaMigrationRegistry(
    ARC_SCHEMA,
    {"1.0": ("1.1", _arc_1_0_to_1_1)},
)
