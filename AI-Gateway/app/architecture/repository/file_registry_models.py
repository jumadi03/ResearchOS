"""Content-addressed file identity and continuity contracts for FMA-003."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
import json
from pathlib import PurePosixPath

from app.architecture.schema import FILE_REGISTRY_SCHEMA

from .models import RepositoryFileClassification
from .policy_models import RepositoryLifecycle


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


class FileGovernanceState(StrEnum):
    ASSIGNED = "assigned"
    PARTIAL = "partial"
    UNASSIGNED = "unassigned"


@dataclass(frozen=True, slots=True)
class FileContinuityEvent:
    event_id: str
    file_id: str
    from_path: str
    to_path: str
    from_hash: str
    to_hash: str
    from_revision: str
    to_revision: str
    actor: str
    rationale: str
    occurred_at: str
    event_hash: str = ""

    def canonical_payload(self) -> dict[str, str]:
        return {
            key: value for key, value in asdict(
                replace(self, event_id="", event_hash="")
            ).items()
            if key not in {"event_id", "event_hash"}
        }

    def calculate_event_hash(self) -> str:
        return sha256(json.dumps(
            self.canonical_payload(),
            ensure_ascii=False, separators=(",", ":"), sort_keys=True,
        ).encode("utf-8")).hexdigest()

    def finalized(self) -> "FileContinuityEvent":
        event_hash = self.calculate_event_hash()
        return replace(
            self,
            event_id=f"file-continuity:{event_hash[:24]}",
            event_hash=event_hash,
        )

    def verify(self) -> bool:
        try:
            datetime.fromisoformat(self.occurred_at.replace("Z", "+00:00"))
        except ValueError:
            return False
        return (
            self.from_path != self.to_path
            and _valid_path(self.from_path)
            and _valid_path(self.to_path)
            and _valid_hash(self.from_hash)
            and _valid_hash(self.to_hash)
            and bool(
                self.file_id.strip()
                and self.from_revision.strip()
                and self.to_revision.strip()
                and self.from_revision != self.to_revision
                and self.actor.strip()
                and self.rationale.strip()
            )
            and self == self.finalized()
        )


@dataclass(frozen=True, slots=True)
class RepositoryFileEntry:
    file_id: str
    current_path: str
    content_hash: str
    classification: RepositoryFileClassification
    size: int
    extension: str
    first_seen_revision: str
    previous_paths: tuple[str, ...]
    owner: str | None
    subsystem: str | None
    engine: str | None
    capability: str | None
    lifecycle: RepositoryLifecycle | None
    policy_ids: tuple[str, ...]
    exception_ids: tuple[str, ...]
    governance_state: FileGovernanceState

    def verify(self) -> bool:
        ownership = (self.owner, self.subsystem, self.engine, self.capability)
        has_owner = all(value and value.strip() for value in ownership)
        has_no_owner = all(value is None for value in ownership)
        expected_state = (
            FileGovernanceState.ASSIGNED
            if has_owner and self.lifecycle is not None
            else FileGovernanceState.PARTIAL
            if has_owner or self.lifecycle is not None
            else FileGovernanceState.UNASSIGNED
        )
        return (
            self.file_id.startswith("file:")
            and _valid_path(self.current_path)
            and _valid_hash(self.content_hash)
            and self.size >= 0
            and self.extension == self.extension.lower()
            and bool(self.first_seen_revision.strip())
            and all(_valid_path(path) for path in self.previous_paths)
            and self.current_path not in self.previous_paths
            and len(set(self.previous_paths)) == len(self.previous_paths)
            and (has_owner or has_no_owner)
            and len(set(self.policy_ids)) == len(self.policy_ids)
            and len(set(self.exception_ids)) == len(self.exception_ids)
            and self.governance_state is expected_state
        )


@dataclass(frozen=True, slots=True)
class RepositoryFileRegistry:
    registry_id: str
    project_name: str
    source_revision: str
    inventory_id: str
    inventory_hash: str
    policy_bundle_id: str
    policy_bundle_hash: str
    entries: tuple[RepositoryFileEntry, ...]
    continuity_events: tuple[FileContinuityEvent, ...] = ()
    governance_counts: tuple[tuple[str, int], ...] = ()
    schema_version: str = "1.0"
    content_hash: str = ""

    def canonical_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "project_name": self.project_name,
            "source_revision": self.source_revision,
            "inventory_id": self.inventory_id,
            "inventory_hash": self.inventory_hash,
            "policy_bundle_id": self.policy_bundle_id,
            "policy_bundle_hash": self.policy_bundle_hash,
            "entries": [
                asdict(item)
                for item in sorted(self.entries, key=lambda item: item.file_id)
            ],
            "continuity_events": [
                asdict(item) for item in sorted(
                    self.continuity_events, key=lambda item: item.event_id,
                )
            ],
            "governance_counts": [
                list(item) for item in sorted(self.governance_counts)
            ],
        }

    def calculate_content_hash(self) -> str:
        return sha256(json.dumps(
            self.canonical_payload(),
            ensure_ascii=False, separators=(",", ":"), sort_keys=True,
        ).encode("utf-8")).hexdigest()

    def finalized(self) -> "RepositoryFileRegistry":
        entries = tuple(sorted(self.entries, key=lambda item: item.file_id))
        events = tuple(sorted(
            self.continuity_events, key=lambda item: item.event_id,
        ))
        counts = tuple(sorted(Counter(
            item.governance_state.value for item in entries
        ).items()))
        candidate = replace(
            self, registry_id="", entries=entries,
            continuity_events=events, governance_counts=counts,
            content_hash="",
        )
        content_hash = candidate.calculate_content_hash()
        return replace(
            candidate,
            registry_id=(
                f"file-registry:{self.project_name}:{content_hash[:16]}"
            ),
            content_hash=content_hash,
        )

    def verify(self) -> bool:
        paths = [item.current_path for item in self.entries]
        file_ids = [item.file_id for item in self.entries]
        event_ids = [item.event_id for item in self.continuity_events]
        entries_by_id = {item.file_id: item for item in self.entries}
        continuity_is_consistent = all(
            event.file_id in entries_by_id
            and event.from_path in entries_by_id[event.file_id].previous_paths
            and (
                event.to_path == entries_by_id[event.file_id].current_path
                or event.to_path
                in entries_by_id[event.file_id].previous_paths
            )
            for event in self.continuity_events
        )
        return (
            bool(
                self.project_name.strip()
                and self.source_revision.strip()
                and self.inventory_id.strip()
                and _valid_hash(self.inventory_hash)
                and self.policy_bundle_id.strip()
                and _valid_hash(self.policy_bundle_hash)
                and self.entries
            )
            and len(paths) == len(set(paths))
            and len(file_ids) == len(set(file_ids))
            and len(event_ids) == len(set(event_ids))
            and all(item.verify() for item in self.entries)
            and all(item.verify() for item in self.continuity_events)
            and continuity_is_consistent
            and self == self.finalized()
        )

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(
            {
                "registry_id": self.registry_id,
                "content_hash": self.content_hash,
                **self.canonical_payload(),
            },
            ensure_ascii=False, indent=indent, sort_keys=True,
        )

    @classmethod
    def from_json(cls, value: str) -> "RepositoryFileRegistry":
        payload = json.loads(value)
        FILE_REGISTRY_SCHEMA.require_readable(payload.get("schema_version", ""))
        registry = cls(
            registry_id=payload.get("registry_id", ""),
            project_name=payload["project_name"],
            source_revision=payload["source_revision"],
            inventory_id=payload["inventory_id"],
            inventory_hash=payload["inventory_hash"],
            policy_bundle_id=payload["policy_bundle_id"],
            policy_bundle_hash=payload["policy_bundle_hash"],
            entries=tuple(
                RepositoryFileEntry(
                    **{
                        **item,
                        "classification": RepositoryFileClassification(
                            item["classification"]
                        ),
                        "previous_paths": tuple(item["previous_paths"]),
                        "lifecycle": (
                            RepositoryLifecycle(item["lifecycle"])
                            if item.get("lifecycle") else None
                        ),
                        "policy_ids": tuple(item["policy_ids"]),
                        "exception_ids": tuple(item["exception_ids"]),
                        "governance_state": FileGovernanceState(
                            item["governance_state"]
                        ),
                    }
                )
                for item in payload.get("entries", ())
            ),
            continuity_events=tuple(
                FileContinuityEvent(**item)
                for item in payload.get("continuity_events", ())
            ),
            governance_counts=tuple(
                (str(item[0]), int(item[1]))
                for item in payload.get("governance_counts", ())
            ),
            schema_version=payload.get("schema_version", ""),
            content_hash=payload.get("content_hash", ""),
        )
        if not registry.verify():
            raise ValueError("Repository file registry identity or content is invalid")
        return registry
