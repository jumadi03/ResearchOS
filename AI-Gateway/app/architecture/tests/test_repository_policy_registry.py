from dataclasses import replace
import json
from pathlib import Path

import pytest

from app.architecture.repository import (
    RepositoryFileClassification as Classification,
    RepositoryLifecycle,
    RepositoryLifecyclePolicy,
    RepositoryNamingPolicy,
    RepositoryOwnershipPolicy,
    RepositoryPlacementPolicy,
    RepositoryPolicyBundle,
    RepositoryPolicyConflict,
    RepositoryPolicyException,
    RepositoryPolicyRegistry,
)
from app.architecture.schema import SchemaVersionError


def policies():
    ownership = RepositoryOwnershipPolicy(
        "OWNER-1", "1.0", ("app/**",), "Runtime Engine",
        "Runtime", "Runtime Engine", "Execution",
        "Runtime source has explicit architectural ownership.",
    )
    placement = RepositoryPlacementPolicy(
        "PLACEMENT-1", "1.0", ("app/**",),
        (Classification.CODE, Classification.TEST),
        (".py",), (".pdf",), "Application source placement.",
    )
    naming = RepositoryNamingPolicy(
        "NAMING-1", "1.0", ("app/**/*.py",),
        r"^(__init__|test_[a-z][a-z0-9_]*|[a-z][a-z0-9_]*)\.py$",
        ("service.py", "test_service.py"), "Python naming convention.",
    )
    lifecycle = RepositoryLifecyclePolicy(
        "LIFECYCLE-1", "1.0", ("app/**",),
        RepositoryLifecycle.DEPRECATE,
        "Compatibility review is required.", "Runtime source lifecycle.",
    )
    return ownership, placement, naming, lifecycle


def bundle(*, exceptions=()) -> RepositoryPolicyBundle:
    ownership, placement, naming, lifecycle = policies()
    return RepositoryPolicyBundle(
        "", "ResearchOS", "1.0", "revision-1",
        (ownership,), (placement,), (naming,), (lifecycle,), exceptions,
    ).finalized()


def test_policy_bundle_is_deterministic_and_round_trips() -> None:
    first = bundle()
    ownership, placement, naming, lifecycle = policies()
    reordered = RepositoryPolicyBundle(
        "", "ResearchOS", "1.0", "revision-1",
        tuple(reversed((ownership,))),
        tuple(reversed((placement,))),
        tuple(reversed((naming,))),
        tuple(reversed((lifecycle,))),
    ).finalized()
    assert first == reordered
    assert first.verify()
    assert RepositoryPolicyBundle.from_json(first.to_json()) == first


def test_policy_contracts_reject_invalid_scope_regex_and_placement() -> None:
    ownership, placement, naming, lifecycle = policies()
    assert not replace(ownership, path_patterns=("../app/**",)).verify()
    assert not replace(naming, name_pattern="[").verify()
    assert not replace(
        placement, forbidden_extensions=(".py",),
    ).verify()
    assert not replace(lifecycle, review_condition="").verify()


def test_exception_requires_provenance_expiry_and_known_policy() -> None:
    valid = RepositoryPolicyException(
        "EXCEPTION-1", ("PLACEMENT-1",), ("app/legacy.py",),
        "Temporary compatibility bridge.", "owner@example",
        "2026-07-17", expires_at="2026-08-17",
    )
    assert valid.verify()
    assert bundle(exceptions=(valid,)).verify()
    assert not replace(valid, expires_at=None).verify()
    assert not replace(valid, expires_at="2026-01-01").verify()
    assert not bundle(
        exceptions=(replace(valid, policy_ids=("UNKNOWN",)),),
    ).verify()


def test_registry_resolves_all_applicable_policies_without_claiming_compliance() -> None:
    registry = RepositoryPolicyRegistry(bundle())
    resolved = registry.resolve("app/services/example.py")
    assert {item.policy_id for item in resolved} == {
        "OWNER-1", "PLACEMENT-1", "NAMING-1", "LIFECYCLE-1",
    }
    assert registry.resolve_ownership("app/services/example.py").owner == (
        "Runtime Engine"
    )
    assert registry.resolve_lifecycle(
        "app/services/example.py"
    ).lifecycle is RepositoryLifecycle.DEPRECATE
    assert registry.resolve("uncovered/file.bin") == ()
    assert not hasattr(registry, "compliance_status")


def test_registry_reports_conflicts_and_unsafe_paths() -> None:
    existing, placement, naming, lifecycle = policies()
    conflicting_owner = replace(
        existing, policy_id="OWNER-2", owner="Other Engine",
    )
    conflicting_lifecycle = replace(
        lifecycle, policy_id="LIFECYCLE-2",
        lifecycle=RepositoryLifecycle.DELETE,
    )
    conflicted = RepositoryPolicyBundle(
        "", "ResearchOS", "1.0", "revision-1",
        (existing, conflicting_owner), (placement,), (naming,),
        (lifecycle, conflicting_lifecycle),
    ).finalized()
    registry = RepositoryPolicyRegistry(conflicted)
    with pytest.raises(RepositoryPolicyConflict, match="ownership"):
        registry.resolve_ownership("app/service.py")
    with pytest.raises(RepositoryPolicyConflict, match="lifecycle"):
        registry.resolve_lifecycle("app/service.py")
    with pytest.raises(ValueError, match="Unsafe"):
        registry.resolve("../outside.py")


def test_policy_bundle_rejects_duplicate_ids_tampering_and_future_schema() -> None:
    ownership, placement, naming, lifecycle = policies()
    duplicate = RepositoryPolicyBundle(
        "", "ResearchOS", "1.0", "revision-1",
        (ownership,), (replace(
            placement, policy_id=ownership.policy_id,
        ),), (naming,), (lifecycle,),
    ).finalized()
    assert not duplicate.verify()

    payload = json.loads(bundle().to_json())
    payload["ownership_policies"][0]["owner"] = "Tampered"
    with pytest.raises(ValueError, match="invalid"):
        RepositoryPolicyBundle.from_json(json.dumps(payload))
    payload = json.loads(bundle().to_json())
    payload["schema_version"] = "2.0"
    with pytest.raises(SchemaVersionError, match="future"):
        RepositoryPolicyBundle.from_json(json.dumps(payload))


def test_canonical_researchos_policy_bundle_loads_and_resolves() -> None:
    root = Path(__file__).resolve().parents[4]
    source = (
        root / ".github" / "researchos" / "repository-policy-v1.json"
    ).read_text(encoding="utf-8")
    canonical = RepositoryPolicyBundle.from_json(source)
    registry = RepositoryPolicyRegistry(canonical)

    assert canonical.bundle_id == "repository-policy:1.0:a778690b312ac90b"
    assert len(canonical.policies) == 14
    architecture = registry.resolve_ownership(
        "AI-Gateway/app/architecture/repository/policy_models.py"
    )
    assert architecture is not None
    assert architecture.capability == "Repository Management"
    assert registry.resolve_lifecycle(
        "Documents/FILE_MANAGEMENT_ARCHITECTURE.md"
    ).lifecycle is RepositoryLifecycle.ARCHIVE


def test_policy_capability_has_no_runtime_scientific_or_storage_dependencies() -> None:
    capability = Path(__file__).parents[1] / "repository"
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in capability.glob("policy_*.py")
    )
    forbidden = (
        "app.runtime", "app.knowledge", "app.discovery",
        "psycopg", "boto3",
    )
    assert not any(item in source for item in forbidden)
