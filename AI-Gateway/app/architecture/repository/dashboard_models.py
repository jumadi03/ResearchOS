"""Immutable, provenance-bearing repository dashboard projection contracts."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, replace
from hashlib import sha256
import json
from pathlib import PurePosixPath

from app.architecture.schema import REPOSITORY_DASHBOARD_SCHEMA

from .file_registry_models import FileGovernanceState
from .health_models import RepositoryHealthCategory, RepositoryHealthOutcome
from .models import RepositoryFileClassification


def _valid_hash(value: str) -> bool:
    return len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _valid_path(value: str) -> bool:
    path = PurePosixPath(value)
    return bool(
        value
        and "\\" not in value
        and not path.is_absolute()
        and all(part not in {"", ".", ".."} for part in path.parts)
    )


@dataclass(frozen=True, slots=True)
class RepositoryDashboardFile:
    file_id: str
    path: str
    content_hash: str
    classification: RepositoryFileClassification
    size: int
    owner: str | None
    subsystem: str | None
    engine: str | None
    capability: str | None
    lifecycle: str | None
    governance_state: FileGovernanceState
    policy_ids: tuple[str, ...]
    exception_ids: tuple[str, ...]

    def verify(self) -> bool:
        ownership = (self.owner, self.subsystem, self.engine, self.capability)
        assigned = all(value and value.strip() for value in ownership)
        absent = all(value is None for value in ownership)
        return (
            self.file_id.startswith("file:")
            and _valid_path(self.path)
            and _valid_hash(self.content_hash)
            and self.size >= 0
            and (assigned or absent)
            and len(self.policy_ids) == len(set(self.policy_ids))
            and len(self.exception_ids) == len(set(self.exception_ids))
        )


@dataclass(frozen=True, slots=True)
class RepositoryDashboardHealth:
    check_id: str
    category: RepositoryHealthCategory
    outcome: RepositoryHealthOutcome
    summary: str
    affected_count: int
    evidence_hash: str

    def verify(self) -> bool:
        return (
            self.check_id.startswith("repository-health-check:")
            and bool(self.summary.strip())
            and self.affected_count >= 0
            and _valid_hash(self.evidence_hash)
            and (
                self.affected_count == 0
                if self.outcome in {
                    RepositoryHealthOutcome.OBSERVED,
                    RepositoryHealthOutcome.NOT_EVALUATED,
                }
                else self.affected_count > 0
            )
        )


@dataclass(frozen=True, slots=True)
class RepositoryDashboardSnapshot:
    snapshot_id: str
    project_name: str
    source_revision: str
    registry_id: str
    registry_hash: str
    verification_report_id: str
    verification_report_hash: str
    graph_id: str
    graph_hash: str
    health_report_id: str
    health_report_hash: str
    health_as_of: str
    files: tuple[RepositoryDashboardFile, ...]
    health: tuple[RepositoryDashboardHealth, ...]
    inventory_counts: tuple[tuple[str, int], ...]
    governance_counts: tuple[tuple[str, int], ...]
    verification_counts: tuple[tuple[str, int], ...]
    health_counts: tuple[tuple[str, int], ...]
    architecture_node_counts: tuple[tuple[str, int], ...]
    architecture_edge_counts: tuple[tuple[str, int], ...]
    mode: str = "read_only_projection"
    schema_version: str = "1.0"
    content_hash: str = ""

    @property
    def is_compliance_decision(self) -> bool:
        return False

    @property
    def status(self) -> str:
        outcomes = {item.outcome for item in self.health}
        if RepositoryHealthOutcome.NOT_EVALUATED in outcomes:
            return "INCOMPLETE"
        if RepositoryHealthOutcome.FINDING in outcomes:
            return "FINDINGS"
        if RepositoryHealthOutcome.ADVISORY in outcomes:
            return "ADVISORIES"
        return "OBSERVED"

    def canonical_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "mode": self.mode,
            "project_name": self.project_name,
            "source_revision": self.source_revision,
            "registry_id": self.registry_id,
            "registry_hash": self.registry_hash,
            "verification_report_id": self.verification_report_id,
            "verification_report_hash": self.verification_report_hash,
            "graph_id": self.graph_id,
            "graph_hash": self.graph_hash,
            "health_report_id": self.health_report_id,
            "health_report_hash": self.health_report_hash,
            "health_as_of": self.health_as_of,
            "files": [
                asdict(item) for item in sorted(self.files, key=lambda item: item.file_id)
            ],
            "health": [
                asdict(item)
                for item in sorted(self.health, key=lambda item: item.check_id)
            ],
            "inventory_counts": [list(item) for item in sorted(self.inventory_counts)],
            "governance_counts": [list(item) for item in sorted(self.governance_counts)],
            "verification_counts": [
                list(item) for item in sorted(self.verification_counts)
            ],
            "health_counts": [list(item) for item in sorted(self.health_counts)],
            "architecture_node_counts": [
                list(item) for item in sorted(self.architecture_node_counts)
            ],
            "architecture_edge_counts": [
                list(item) for item in sorted(self.architecture_edge_counts)
            ],
        }

    def calculate_content_hash(self) -> str:
        return sha256(json.dumps(
            self.canonical_payload(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")).hexdigest()

    def finalized(self) -> "RepositoryDashboardSnapshot":
        candidate = replace(
            self,
            snapshot_id="",
            files=tuple(sorted(self.files, key=lambda item: item.file_id)),
            health=tuple(sorted(self.health, key=lambda item: item.check_id)),
            inventory_counts=tuple(sorted(self.inventory_counts)),
            governance_counts=tuple(sorted(self.governance_counts)),
            verification_counts=tuple(sorted(self.verification_counts)),
            health_counts=tuple(sorted(self.health_counts)),
            architecture_node_counts=tuple(sorted(self.architecture_node_counts)),
            architecture_edge_counts=tuple(sorted(self.architecture_edge_counts)),
            content_hash="",
        )
        content_hash = candidate.calculate_content_hash()
        return replace(
            candidate,
            snapshot_id=(
                f"repository-dashboard:{self.project_name}:{content_hash[:16]}"
            ),
            content_hash=content_hash,
        )

    def verify(self) -> bool:
        file_ids = [item.file_id for item in self.files]
        paths = [item.path for item in self.files]
        health_ids = [item.check_id for item in self.health]
        return (
            bool(
                self.project_name.strip()
                and self.source_revision.strip()
                and self.registry_id.strip()
                and _valid_hash(self.registry_hash)
                and self.verification_report_id.strip()
                and _valid_hash(self.verification_report_hash)
                and self.graph_id.strip()
                and _valid_hash(self.graph_hash)
                and self.health_report_id.strip()
                and _valid_hash(self.health_report_hash)
                and self.health_as_of.strip()
                and self.files
                and self.health
            )
            and self.mode == "read_only_projection"
            and len(file_ids) == len(set(file_ids))
            and len(paths) == len(set(paths))
            and len(health_ids) == len(set(health_ids))
            and {item.category for item in self.health}
            == set(RepositoryHealthCategory)
            and all(item.verify() for item in self.files)
            and all(item.verify() for item in self.health)
            and self.inventory_counts == tuple(sorted(Counter(
                item.classification.value for item in self.files
            ).items()))
            and self.governance_counts == tuple(sorted(Counter(
                item.governance_state.value for item in self.files
            ).items()))
            and self.health_counts == tuple(sorted(Counter(
                item.outcome.value for item in self.health
            ).items()))
            and self == self.finalized()
        )

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(
            {
                "snapshot_id": self.snapshot_id,
                "content_hash": self.content_hash,
                "status": self.status,
                "is_compliance_decision": self.is_compliance_decision,
                **self.canonical_payload(),
            },
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    @classmethod
    def from_json(cls, value: str) -> "RepositoryDashboardSnapshot":
        payload = json.loads(value)
        REPOSITORY_DASHBOARD_SCHEMA.require_readable(
            payload.get("schema_version", "")
        )
        snapshot = cls(
            snapshot_id=payload.get("snapshot_id", ""),
            project_name=payload["project_name"],
            source_revision=payload["source_revision"],
            registry_id=payload["registry_id"],
            registry_hash=payload["registry_hash"],
            verification_report_id=payload["verification_report_id"],
            verification_report_hash=payload["verification_report_hash"],
            graph_id=payload["graph_id"],
            graph_hash=payload["graph_hash"],
            health_report_id=payload["health_report_id"],
            health_report_hash=payload["health_report_hash"],
            health_as_of=payload["health_as_of"],
            files=tuple(
                RepositoryDashboardFile(
                    **{
                        **item,
                        "classification": RepositoryFileClassification(
                            item["classification"]
                        ),
                        "governance_state": FileGovernanceState(
                            item["governance_state"]
                        ),
                        "policy_ids": tuple(item.get("policy_ids", ())),
                        "exception_ids": tuple(item.get("exception_ids", ())),
                    }
                )
                for item in payload.get("files", ())
            ),
            health=tuple(
                RepositoryDashboardHealth(
                    **{
                        **item,
                        "category": RepositoryHealthCategory(item["category"]),
                        "outcome": RepositoryHealthOutcome(item["outcome"]),
                    }
                )
                for item in payload.get("health", ())
            ),
            inventory_counts=tuple(
                (str(item[0]), int(item[1]))
                for item in payload.get("inventory_counts", ())
            ),
            governance_counts=tuple(
                (str(item[0]), int(item[1]))
                for item in payload.get("governance_counts", ())
            ),
            verification_counts=tuple(
                (str(item[0]), int(item[1]))
                for item in payload.get("verification_counts", ())
            ),
            health_counts=tuple(
                (str(item[0]), int(item[1]))
                for item in payload.get("health_counts", ())
            ),
            architecture_node_counts=tuple(
                (str(item[0]), int(item[1]))
                for item in payload.get("architecture_node_counts", ())
            ),
            architecture_edge_counts=tuple(
                (str(item[0]), int(item[1]))
                for item in payload.get("architecture_edge_counts", ())
            ),
            mode=payload.get("mode", ""),
            schema_version=payload.get("schema_version", ""),
            content_hash=payload.get("content_hash", ""),
        )
        if (
            payload.get("status") != snapshot.status
            or payload.get("is_compliance_decision")
            is not snapshot.is_compliance_decision
            or not snapshot.verify()
        ):
            raise ValueError(
                "Repository dashboard snapshot identity or content is invalid"
            )
        return snapshot
