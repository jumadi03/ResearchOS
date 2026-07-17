"""Versioned advisory public-contract and deprecation registry contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from hashlib import sha256
import json

from app.architecture.schema import PUBLIC_CONTRACT_REGISTRY_SCHEMA


class PublicContractKind(StrEnum):
    CONSTRUCTOR = "constructor"
    ENUM = "enum"
    NAMESPACE = "namespace"
    HTTP_API = "http_api"
    EVENT = "event"
    SCHEMA = "schema"
    CLI = "cli"
    VERIFIER = "verifier"


class PublicContractLifecycle(StrEnum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    COMPATIBILITY_PERIOD = "compatibility_period"
    REMOVAL_CANDIDATE = "removal_candidate"
    REMOVED = "removed"


@dataclass(frozen=True, slots=True)
class PublicContractEntry:
    contract_id: str
    kind: PublicContractKind
    public_surface: str
    owner: str
    subsystem: str
    engine: str
    capability: str
    lifecycle: PublicContractLifecycle
    callers: tuple[str, ...]
    regression_tests: tuple[str, ...]
    rationale: str
    replacement: str | None = None
    milestone: str | None = None
    migration_guide: str | None = None

    def verify(self) -> bool:
        values = (
            self.contract_id,
            self.public_surface,
            self.owner,
            self.subsystem,
            self.engine,
            self.capability,
            self.rationale,
        )
        deprecation_fields = (
            self.replacement,
            self.milestone,
            self.migration_guide,
        )
        is_active = self.lifecycle is PublicContractLifecycle.ACTIVE
        return (
            self.contract_id.startswith("contract:")
            and all(value.strip() for value in values)
            and bool(self.callers)
            and len(set(self.callers)) == len(self.callers)
            and all(value.strip() for value in self.callers)
            and bool(self.regression_tests)
            and len(set(self.regression_tests)) == len(self.regression_tests)
            and all(value.strip() for value in self.regression_tests)
            and (
                all(value is None for value in deprecation_fields)
                if is_active
                else all(value is not None and value.strip() for value in deprecation_fields)
            )
        )


@dataclass(frozen=True, slots=True)
class PublicContractRegistryManifest:
    registry_id: str
    project_name: str
    source_revision: str
    entries: tuple[PublicContractEntry, ...]
    advisory_only: bool = True
    schema_version: str = "1.0"
    content_hash: str = ""

    def canonical_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "project_name": self.project_name,
            "source_revision": self.source_revision,
            "advisory_only": self.advisory_only,
            "entries": [
                asdict(item)
                for item in sorted(self.entries, key=lambda item: item.contract_id)
            ],
        }

    def calculate_content_hash(self) -> str:
        return sha256(json.dumps(
            self.canonical_payload(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")).hexdigest()

    def finalized(self) -> "PublicContractRegistryManifest":
        content_hash = self.calculate_content_hash()
        return replace(
            self,
            registry_id=f"public-contract-registry:1.0:{content_hash[:16]}",
            entries=tuple(sorted(self.entries, key=lambda item: item.contract_id)),
            content_hash=content_hash,
        )

    def verify(self) -> bool:
        try:
            PUBLIC_CONTRACT_REGISTRY_SCHEMA.require_readable(self.schema_version)
        except ValueError:
            return False
        identities = [item.contract_id for item in self.entries]
        surfaces = [item.public_surface for item in self.entries]
        return (
            self.advisory_only
            and bool(self.project_name.strip() and self.source_revision.strip())
            and bool(self.entries)
            and len(set(identities)) == len(identities)
            and len(set(surfaces)) == len(surfaces)
            and all(item.verify() for item in self.entries)
            and self == self.finalized()
        )

    def to_json(self) -> str:
        return json.dumps(
            {
                "registry_id": self.registry_id,
                "content_hash": self.content_hash,
                **self.canonical_payload(),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

    @classmethod
    def from_json(cls, raw: str) -> "PublicContractRegistryManifest":
        payload = json.loads(raw)
        PUBLIC_CONTRACT_REGISTRY_SCHEMA.require_readable(
            payload.get("schema_version", "")
        )
        manifest = cls(
            registry_id=payload.get("registry_id", ""),
            project_name=payload.get("project_name", ""),
            source_revision=payload.get("source_revision", ""),
            advisory_only=payload.get("advisory_only", False),
            schema_version=payload.get("schema_version", ""),
            content_hash=payload.get("content_hash", ""),
            entries=tuple(
                PublicContractEntry(
                    contract_id=item["contract_id"],
                    kind=PublicContractKind(item["kind"]),
                    public_surface=item["public_surface"],
                    owner=item["owner"],
                    subsystem=item["subsystem"],
                    engine=item["engine"],
                    capability=item["capability"],
                    lifecycle=PublicContractLifecycle(item["lifecycle"]),
                    callers=tuple(item["callers"]),
                    regression_tests=tuple(item["regression_tests"]),
                    rationale=item["rationale"],
                    replacement=item.get("replacement"),
                    milestone=item.get("milestone"),
                    migration_guide=item.get("migration_guide"),
                )
                for item in payload.get("entries", ())
            ),
        )
        if not manifest.verify():
            raise ValueError("Public contract registry integrity verification failed")
        return manifest
