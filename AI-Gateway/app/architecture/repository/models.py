"""Immutable, revision-bound repository inventory contracts for FMA-001."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from hashlib import sha256
import json


class RepositoryFileClassification(StrEnum):
    """Primary classification of one repository file."""

    CODE = "code"
    TEST = "test"
    DOCUMENT = "document"
    CONFIGURATION = "configuration"
    SCRIPT = "script"
    DATASET = "dataset"
    ARTIFACT = "artifact"
    GENERATED = "generated"
    TEMPORARY = "temporary"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class RepositoryFileRecord:
    """Content-addressed observation of one tracked repository file."""

    path: str
    classification: RepositoryFileClassification
    size: int
    sha256: str
    extension: str
    tracked: bool
    classification_reason: str

    def verify(self) -> bool:
        parts = self.path.split("/")
        return (
            bool(self.path and self.classification_reason.strip())
            and "\\" not in self.path
            and not self.path.startswith("/")
            and all(part not in {"", ".", ".."} for part in parts)
            and self.size >= 0
            and len(self.sha256) == 64
            and all(character in "0123456789abcdef" for character in self.sha256)
            and self.extension == self.extension.lower()
        )


@dataclass(frozen=True, slots=True)
class RepositoryInventory:
    """Deterministic snapshot of a revision's tracked-file classification."""

    inventory_id: str
    project_name: str
    source_revision: str
    files: tuple[RepositoryFileRecord, ...]
    classification_counts: tuple[tuple[str, int], ...] = ()
    schema_version: str = "1.0"
    content_hash: str = ""

    def canonical_payload(self) -> dict[str, object]:
        ordered = sorted(self.files, key=lambda item: item.path)
        return {
            "schema_version": self.schema_version,
            "project_name": self.project_name,
            "source_revision": self.source_revision,
            "files": [asdict(item) for item in ordered],
            "classification_counts": [
                list(item) for item in sorted(self.classification_counts)
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

    def finalized(self) -> "RepositoryInventory":
        ordered = tuple(sorted(self.files, key=lambda item: item.path))
        counts = tuple(sorted(Counter(
            item.classification.value for item in ordered
        ).items()))
        candidate = replace(
            self, inventory_id="", files=ordered,
            classification_counts=counts, content_hash="",
        )
        content_hash = candidate.calculate_content_hash()
        return replace(
            candidate,
            inventory_id=(
                f"repository-inventory:{self.project_name}:{content_hash[:16]}"
            ),
            content_hash=content_hash,
        )

    def verify(self) -> bool:
        expected = self.finalized()
        return (
            bool(self.project_name.strip() and self.source_revision.strip())
            and bool(self.files)
            and len({item.path for item in self.files}) == len(self.files)
            and all(item.verify() and item.tracked for item in self.files)
            and self == expected
        )

    def to_json(self, *, indent: int | None = 2) -> str:
        payload = {
            "inventory_id": self.inventory_id,
            "content_hash": self.content_hash,
            **self.canonical_payload(),
        }
        return json.dumps(
            payload, ensure_ascii=False, indent=indent, sort_keys=True,
        )

    @classmethod
    def from_json(cls, value: str) -> "RepositoryInventory":
        payload = json.loads(value)
        if payload.get("schema_version") != "1.0":
            raise ValueError("Unsupported repository inventory schema version")
        inventory = cls(
            inventory_id=payload.get("inventory_id", ""),
            project_name=payload["project_name"],
            source_revision=payload["source_revision"],
            files=tuple(
                RepositoryFileRecord(
                    **{
                        **item,
                        "classification": RepositoryFileClassification(
                            item["classification"]
                        ),
                    }
                )
                for item in payload.get("files", [])
            ),
            classification_counts=tuple(
                (str(item[0]), int(item[1]))
                for item in payload.get("classification_counts", [])
            ),
            schema_version=payload.get("schema_version", ""),
            content_hash=payload.get("content_hash", ""),
        )
        if not inventory.verify():
            raise ValueError("Repository inventory identity or content is invalid")
        return inventory
