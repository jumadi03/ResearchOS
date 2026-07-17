from dataclasses import replace
import json
from pathlib import Path

import pytest

from app.architecture.repository import (
    PublicContractEntry,
    PublicContractKind,
    PublicContractLifecycle,
    PublicContractRegistry,
    PublicContractRegistryManifest,
)
from app.architecture.schema import SchemaVersionError


def entry(
    *,
    contract_id: str = "contract:kernel-capability",
    lifecycle: PublicContractLifecycle = PublicContractLifecycle.ACTIVE,
) -> PublicContractEntry:
    deprecated = lifecycle is not PublicContractLifecycle.ACTIVE
    return PublicContractEntry(
        contract_id=contract_id,
        kind=PublicContractKind.NAMESPACE,
        public_surface="app.kernel.contracts",
        owner="Architecture",
        subsystem="Architecture Governance",
        engine="Repository Governance",
        capability="Public Contract and Deprecation Registry",
        lifecycle=lifecycle,
        callers=("app.kernel",),
        regression_tests=("app/kernel/tests/test_kernel_contracts_public_api.py",),
        rationale="Stable Kernel contract namespace.",
        replacement="app.kernel.contracts" if deprecated else None,
        milestone="Phase 3 compatibility review" if deprecated else None,
        migration_guide="Import through app.kernel.contracts." if deprecated else None,
    )


def manifest(*entries: PublicContractEntry) -> PublicContractRegistryManifest:
    return PublicContractRegistryManifest(
        "",
        "ResearchOS",
        "revision-1",
        entries or (entry(),),
    ).finalized()


def test_manifest_is_deterministic_content_addressed_and_round_trips() -> None:
    first = manifest(
        entry(contract_id="contract:z"),
        replace(
            entry(contract_id="contract:a"),
            public_surface="app.kernel.execution",
        ),
    )
    reordered = manifest(*reversed(first.entries))
    assert first == reordered
    assert first.verify()
    assert PublicContractRegistryManifest.from_json(first.to_json()) == first


def test_lifecycle_requires_complete_deprecation_record() -> None:
    assert entry().verify()
    deprecated = entry(lifecycle=PublicContractLifecycle.DEPRECATED)
    assert deprecated.verify()
    assert not replace(deprecated, replacement=None).verify()
    assert not replace(deprecated, milestone=None).verify()
    assert not replace(deprecated, migration_guide=None).verify()
    assert not replace(entry(), replacement="unexpected").verify()


def test_manifest_rejects_duplicate_identity_surface_and_tampering() -> None:
    duplicate_id = replace(entry(), public_surface="app.kernel.execution")
    assert not manifest(entry(), duplicate_id).verify()
    duplicate_surface = replace(entry(), contract_id="contract:other")
    assert not manifest(entry(), duplicate_surface).verify()
    assert not replace(manifest(), content_hash="0" * 64).verify()


def test_registry_is_read_only_advisory_resolution() -> None:
    deprecated = replace(
        entry(
            contract_id="contract:legacy",
            lifecycle=PublicContractLifecycle.COMPATIBILITY_PERIOD,
        ),
        public_surface="app.legacy",
    )
    registry = PublicContractRegistry(manifest(entry(), deprecated))
    assert registry.get("contract:kernel-capability") == entry()
    assert registry.resolve_surface("app.legacy") == deprecated
    assert registry.by_lifecycle(
        PublicContractLifecycle.COMPATIBILITY_PERIOD
    ) == (deprecated,)
    assert registry.manifest.advisory_only
    assert not hasattr(registry, "remove")
    assert not hasattr(registry, "enforce")


def test_unknown_schema_fails_before_registry_content_is_used() -> None:
    payload = json.loads(manifest().to_json())
    payload["schema_version"] = "2.0"
    with pytest.raises(SchemaVersionError, match="future"):
        PublicContractRegistryManifest.from_json(json.dumps(payload))


def test_canonical_repository_manifest_is_valid_and_advisory() -> None:
    root = Path(__file__).resolve().parents[4]
    path = root / ".github/researchos/public-contract-registry-v1.json"
    restored = PublicContractRegistryManifest.from_json(
        path.read_text(encoding="utf-8")
    )
    registry = PublicContractRegistry(restored)
    assert restored.verify()
    assert restored.advisory_only
    assert len(restored.entries) == 5
    gateway_root = root / "AI-Gateway"
    assert all(
        (gateway_root / test_path).is_file()
        for item in restored.entries
        for test_path in item.regression_tests
    )
    assert tuple(
        item.contract_id for item in registry.by_lifecycle(
            PublicContractLifecycle.COMPATIBILITY_PERIOD
        )
    ) == ("contract:recovery-ready-alias",)
