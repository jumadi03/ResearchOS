"""Versioned, content-addressed collection of architecture laws."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from hashlib import sha256
import json

from .architecture_law import ArchitectureLaw
from ..schema import LAW_BUNDLE_SCHEMA


@dataclass(frozen=True, slots=True)
class ArchitectureLawBundle:
    """Immutable set of ratified architecture laws for one execution cycle."""

    bundle_id: str
    version: str
    laws: tuple[ArchitectureLaw, ...] = ()
    schema_version: str = "1.0"
    content_hash: str = ""

    def __post_init__(self) -> None:
        law_ids = [law.law_id for law in self.laws]
        if len(law_ids) != len(set(law_ids)):
            raise ValueError("A law bundle cannot contain duplicate law identifiers")

    def canonical_payload(self) -> dict[str, object]:
        """Return stable bundle content, excluding self-referential identity."""
        return {
            "schema_version": self.schema_version,
            "version": self.version,
            "laws": [
                asdict(law)
                for law in sorted(self.laws, key=lambda item: item.law_id)
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

    def finalized(self) -> ArchitectureLawBundle:
        content_hash = self.calculate_content_hash()
        return replace(
            self,
            bundle_id=f"law-bundle:{self.version}:{content_hash[:16]}",
            laws=tuple(sorted(self.laws, key=lambda item: item.law_id)),
            content_hash=content_hash,
        )

    def to_json(self, *, indent: int | None = 2) -> str:
        payload = {
            "bundle_id": self.bundle_id,
            "content_hash": self.content_hash,
            **self.canonical_payload(),
        }
        return json.dumps(payload, ensure_ascii=False, indent=indent, sort_keys=True)

    @classmethod
    def from_json(cls, value: str) -> ArchitectureLawBundle:
        """Load and verify a bundle from its canonical JSON representation."""
        payload = json.loads(value)
        LAW_BUNDLE_SCHEMA.require_readable(payload.get("schema_version", ""))
        laws = tuple(
            ArchitectureLaw.from_dict(item) for item in payload.get("laws", [])
        )
        bundle = cls(
            bundle_id=payload.get("bundle_id", ""),
            version=payload["version"],
            laws=laws,
            schema_version=payload.get("schema_version", "1.0"),
            content_hash=payload.get("content_hash", ""),
        )
        expected = bundle.calculate_content_hash()
        if bundle.content_hash and bundle.content_hash != expected:
            raise ValueError("Law bundle content hash does not match its content")
        finalized = bundle.finalized()
        if bundle.bundle_id and bundle.bundle_id != finalized.bundle_id:
            raise ValueError("Law bundle identifier does not match its content")
        return finalized
