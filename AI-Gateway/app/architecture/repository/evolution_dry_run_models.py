"""Immutable, non-mutating execution simulation contracts for FMA-008."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from hashlib import sha256
import json
from pathlib import PurePosixPath

from app.architecture.schema import REPOSITORY_EVOLUTION_DRY_RUN_SCHEMA


def _valid_path(path: str) -> bool:
    item = PurePosixPath(path)
    return bool(
        path
        and "\\" not in path
        and not item.is_absolute()
        and all(part not in {"", ".", ".."} for part in item.parts)
    )


def _valid_hash(value: str) -> bool:
    return len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


class RepositoryDryRunDirection(StrEnum):
    FORWARD = "forward"
    ROLLBACK = "rollback"


@dataclass(frozen=True, slots=True)
class RepositoryDryRunStep:
    sequence: int
    direction: RepositoryDryRunDirection
    file_id: str
    source_path: str
    target_path: str
    content_hash: str

    def verify(self) -> bool:
        return (
            self.sequence >= 1
            and self.file_id.startswith("file:")
            and _valid_path(self.source_path)
            and _valid_path(self.target_path)
            and self.source_path != self.target_path
            and _valid_hash(self.content_hash)
        )


@dataclass(frozen=True, slots=True)
class RepositoryEvolutionDryRun:
    dry_run_id: str
    project_name: str
    plan_id: str
    plan_hash: str
    preflight_id: str
    preflight_hash: str
    source_revision: str
    forward_steps: tuple[RepositoryDryRunStep, ...]
    rollback_steps: tuple[RepositoryDryRunStep, ...]
    schema_version: str = "1.0"
    content_hash: str = ""

    @property
    def mutates_repository(self) -> bool:
        return False

    @property
    def is_execution_authorization(self) -> bool:
        return False

    def canonical_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "project_name": self.project_name,
            "plan_id": self.plan_id,
            "plan_hash": self.plan_hash,
            "preflight_id": self.preflight_id,
            "preflight_hash": self.preflight_hash,
            "source_revision": self.source_revision,
            "forward_steps": [asdict(item) for item in self.forward_steps],
            "rollback_steps": [asdict(item) for item in self.rollback_steps],
        }

    def calculate_content_hash(self) -> str:
        return sha256(json.dumps(
            self.canonical_payload(),
            ensure_ascii=False, separators=(",", ":"), sort_keys=True,
        ).encode("utf-8")).hexdigest()

    def finalized(self) -> "RepositoryEvolutionDryRun":
        candidate = replace(self, dry_run_id="", content_hash="")
        content_hash = candidate.calculate_content_hash()
        return replace(
            candidate,
            dry_run_id=(
                f"repository-dry-run:{self.project_name}:{content_hash[:16]}"
            ),
            content_hash=content_hash,
        )

    def verify(self) -> bool:
        expected_forward = list(range(1, len(self.forward_steps) + 1))
        expected_rollback = list(range(1, len(self.rollback_steps) + 1))
        inverse = tuple(
            (
                step.file_id,
                step.target_path,
                step.source_path,
                step.content_hash,
            )
            for step in reversed(self.forward_steps)
        )
        rollback = tuple(
            (
                step.file_id,
                step.source_path,
                step.target_path,
                step.content_hash,
            )
            for step in self.rollback_steps
        )
        return (
            bool(
                self.project_name.strip()
                and self.plan_id.strip()
                and _valid_hash(self.plan_hash)
                and self.preflight_id.strip()
                and _valid_hash(self.preflight_hash)
                and self.source_revision.strip()
                and self.forward_steps
            )
            and all(item.verify() for item in self.forward_steps)
            and all(item.verify() for item in self.rollback_steps)
            and all(
                item.direction is RepositoryDryRunDirection.FORWARD
                for item in self.forward_steps
            )
            and all(
                item.direction is RepositoryDryRunDirection.ROLLBACK
                for item in self.rollback_steps
            )
            and [item.sequence for item in self.forward_steps] == expected_forward
            and [item.sequence for item in self.rollback_steps] == expected_rollback
            and inverse == rollback
            and not self.mutates_repository
            and not self.is_execution_authorization
            and self == self.finalized()
        )

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(
            {
                "dry_run_id": self.dry_run_id,
                "content_hash": self.content_hash,
                "mutates_repository": self.mutates_repository,
                "is_execution_authorization": self.is_execution_authorization,
                **self.canonical_payload(),
            },
            ensure_ascii=False, indent=indent, sort_keys=True,
        )

    @classmethod
    def from_json(cls, value: str) -> "RepositoryEvolutionDryRun":
        payload = json.loads(value)
        REPOSITORY_EVOLUTION_DRY_RUN_SCHEMA.require_readable(
            payload.get("schema_version", "")
        )

        def steps(key: str) -> tuple[RepositoryDryRunStep, ...]:
            return tuple(
                RepositoryDryRunStep(
                    **{
                        **item,
                        "direction": RepositoryDryRunDirection(
                            item["direction"]
                        ),
                    }
                )
                for item in payload[key]
            )

        dry_run = cls(
            dry_run_id=payload.get("dry_run_id", ""),
            project_name=payload["project_name"],
            plan_id=payload["plan_id"],
            plan_hash=payload["plan_hash"],
            preflight_id=payload["preflight_id"],
            preflight_hash=payload["preflight_hash"],
            source_revision=payload["source_revision"],
            forward_steps=steps("forward_steps"),
            rollback_steps=steps("rollback_steps"),
            schema_version=payload.get("schema_version", ""),
            content_hash=payload.get("content_hash", ""),
        )
        if (
            payload.get("mutates_repository") is not False
            or payload.get("is_execution_authorization") is not False
            or not dry_run.verify()
        ):
            raise ValueError("Repository evolution dry run is invalid")
        return dry_run
