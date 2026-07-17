from dataclasses import replace
from pathlib import Path

import pytest

from app.architecture.repository import (
    FileContinuityEvent,
    FileGovernanceState,
    RepositoryFileRegistry,
    RepositoryFileRegistryBuilder,
    RepositoryLifecycle,
    RepositoryLifecyclePolicy,
    RepositoryOwnershipPolicy,
    RepositoryPolicyBundle,
    RepositoryPolicyException,
    RepositoryPolicyRegistry,
    RepositoryScanner,
)


def _write(root: Path, path: str, content: str) -> None:
    target = root.joinpath(*path.split("/"))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _inventory(root: Path, revision: str, paths: tuple[str, ...]):
    return RepositoryScanner(root).scan(
        paths, project_name="ResearchOS", source_revision=revision,
    )


def _policies(*, conflicting: bool = False) -> RepositoryPolicyRegistry:
    ownership = [
        RepositoryOwnershipPolicy(
            "owner.app", "1.0", ("app/**",), "architecture",
            "Architecture", "Architecture Engine", "Repository Management",
            "Architecture files have an explicit owner.",
        ),
        RepositoryOwnershipPolicy(
            "owner.docs", "1.0", ("docs/**",), "documentation",
            "Documentation", "Documentation Engine", "Documentation",
            "Documents have an explicit owner.",
        ),
    ]
    if conflicting:
        ownership.append(RepositoryOwnershipPolicy(
            "owner.conflict", "1.0", ("app/**",), "other",
            "Other", "Other Engine", "Other Capability", "Conflict fixture.",
        ))
    lifecycle = (
        RepositoryLifecyclePolicy(
            "life.app", "1.0", ("app/**",), RepositoryLifecycle.RETAIN,
            "Review on architecture change.", "Application code is retained.",
        ),
        RepositoryLifecyclePolicy(
            "life.data", "1.0", ("data/**",), RepositoryLifecycle.ARCHIVE,
            "Review on data replacement.", "Data has lifecycle only.",
        ),
    )
    exceptions = (
        RepositoryPolicyException(
            "exception.app", ("owner.app",), ("app/a.py",),
            "Test exception remains visible.", "architecture", "2026-07-17",
            expires_at="2026-08-17",
        ),
    )
    bundle = RepositoryPolicyBundle(
        "", "ResearchOS", "1.0", "policy-r1",
        ownership_policies=tuple(ownership),
        lifecycle_policies=lifecycle,
        exceptions=exceptions,
    ).finalized()
    return RepositoryPolicyRegistry(bundle)


def _claim(old, current, from_revision: str, to_revision: str):
    return FileContinuityEvent(
        "", old.file_id, old.current_path, current.path,
        old.content_hash, current.sha256, from_revision, to_revision,
        "architecture", "Explicitly approved repository rename.",
        "2026-07-17T08:00:00+08:00",
    ).finalized()


def test_registry_is_deterministic_revision_bound_and_round_trips(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "app/a.py", "a = 1\n")
    _write(tmp_path, "docs/readme.md", "# Readme\n")
    inventory = _inventory(tmp_path, "r1", ("docs/readme.md", "app/a.py"))
    builder = RepositoryFileRegistryBuilder()

    first = builder.build(inventory, _policies())
    second = builder.build(inventory, _policies())

    assert first == second
    assert first.verify()
    assert RepositoryFileRegistry.from_json(first.to_json()) == first
    assert first.inventory_id == inventory.inventory_id
    assert first.policy_bundle_id == _policies().bundle.bundle_id
    app = next(item for item in first.entries if item.current_path == "app/a.py")
    docs = next(
        item for item in first.entries if item.current_path == "docs/readme.md"
    )
    assert app.governance_state is FileGovernanceState.ASSIGNED
    assert app.exception_ids == ("exception.app",)
    assert docs.governance_state is FileGovernanceState.PARTIAL


def test_same_path_preserves_identity_across_content_revision(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "app/a.py", "a = 1\n")
    builder = RepositoryFileRegistryBuilder()
    first = builder.build(_inventory(tmp_path, "r1", ("app/a.py",)), _policies())
    _write(tmp_path, "app/a.py", "a = 2\n")

    second = builder.build(
        _inventory(tmp_path, "r2", ("app/a.py",)),
        _policies(), previous=first,
    )

    assert second.entries[0].file_id == first.entries[0].file_id
    assert second.entries[0].content_hash != first.entries[0].content_hash
    assert second.entries[0].first_seen_revision == "r1"


def test_explicit_continuity_claim_preserves_renamed_file_identity(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "app/a.py", "a = 1\n")
    builder = RepositoryFileRegistryBuilder()
    first = builder.build(_inventory(tmp_path, "r1", ("app/a.py",)), _policies())
    (tmp_path / "app/a.py").rename(tmp_path / "app/b.py")
    inventory = _inventory(tmp_path, "r2", ("app/b.py",))
    claim = _claim(first.entries[0], inventory.files[0], "r1", "r2")

    second = builder.build(
        inventory, _policies(), previous=first, continuity_claims=(claim,),
    )

    assert second.entries[0].file_id == first.entries[0].file_id
    assert second.entries[0].previous_paths == ("app/a.py",)
    assert second.continuity_events == (claim,)


def test_rename_is_never_inferred_from_identical_content(tmp_path: Path) -> None:
    _write(tmp_path, "app/a.py", "same\n")
    builder = RepositoryFileRegistryBuilder()
    first = builder.build(_inventory(tmp_path, "r1", ("app/a.py",)), _policies())
    (tmp_path / "app/a.py").rename(tmp_path / "app/b.py")

    second = builder.build(
        _inventory(tmp_path, "r2", ("app/b.py",)),
        _policies(), previous=first,
    )

    assert second.entries[0].file_id != first.entries[0].file_id
    assert second.continuity_events == ()


@pytest.mark.parametrize(
    "mutation, message",
    [
        (lambda claim: replace(claim, file_id="file:unknown").finalized(),
         "unknown file"),
        (lambda claim: replace(claim, from_revision="wrong").finalized(),
         "provenance"),
        (lambda claim: replace(claim, from_hash="0" * 64).finalized(),
         "provenance"),
    ],
)
def test_invalid_continuity_provenance_is_rejected(
    tmp_path: Path, mutation, message: str,
) -> None:
    _write(tmp_path, "app/a.py", "a\n")
    builder = RepositoryFileRegistryBuilder()
    first = builder.build(_inventory(tmp_path, "r1", ("app/a.py",)), _policies())
    (tmp_path / "app/a.py").rename(tmp_path / "app/b.py")
    inventory = _inventory(tmp_path, "r2", ("app/b.py",))
    claim = mutation(_claim(first.entries[0], inventory.files[0], "r1", "r2"))

    with pytest.raises(ValueError, match=message):
        builder.build(
            inventory, _policies(), previous=first, continuity_claims=(claim,),
        )


def test_continuity_cannot_reuse_identity_or_existing_path(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "app/a.py", "a\n")
    _write(tmp_path, "app/c.py", "c\n")
    builder = RepositoryFileRegistryBuilder()
    first = builder.build(
        _inventory(tmp_path, "r1", ("app/a.py", "app/c.py")), _policies(),
    )
    old_a = next(item for item in first.entries if item.current_path == "app/a.py")
    _write(tmp_path, "app/b.py", "b\n")
    inventory = _inventory(
        tmp_path, "r2", ("app/a.py", "app/b.py", "app/c.py"),
    )
    current_b = next(item for item in inventory.files if item.path == "app/b.py")
    claim = _claim(old_a, current_b, "r1", "r2")

    with pytest.raises(ValueError, match="source path still exists"):
        builder.build(
            inventory, _policies(), previous=first, continuity_claims=(claim,),
        )

    (tmp_path / "app/a.py").unlink()
    inventory_existing_target = _inventory(
        tmp_path, "r2", ("app/b.py", "app/c.py"),
    )
    current_c = next(
        item for item in inventory_existing_target.files
        if item.path == "app/c.py"
    )
    existing_target = _claim(old_a, current_c, "r1", "r2")
    with pytest.raises(ValueError, match="established identity"):
        builder.build(
            inventory_existing_target, _policies(), previous=first,
            continuity_claims=(existing_target,),
        )


def test_missing_governance_is_explicit_and_policy_conflicts_fail(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "data/raw.csv", "x\n1\n")
    _write(tmp_path, "misc/unknown.bin", "x")
    inventory = _inventory(
        tmp_path, "r1", ("data/raw.csv", "misc/unknown.bin"),
    )
    registry = RepositoryFileRegistryBuilder().build(inventory, _policies())
    states = {item.current_path: item.governance_state for item in registry.entries}

    assert states["data/raw.csv"] is FileGovernanceState.PARTIAL
    assert states["misc/unknown.bin"] is FileGovernanceState.UNASSIGNED
    assert dict(registry.governance_counts) == {"partial": 1, "unassigned": 1}

    _write(tmp_path, "app/a.py", "a\n")
    with pytest.raises(ValueError, match="Conflicting repository ownership"):
        RepositoryFileRegistryBuilder().build(
            _inventory(tmp_path, "r2", ("app/a.py",)),
            _policies(conflicting=True),
        )


def test_registry_rejects_tampering_future_schema_and_claim_without_history(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "app/a.py", "a\n")
    inventory = _inventory(tmp_path, "r1", ("app/a.py",))
    registry = RepositoryFileRegistryBuilder().build(inventory, _policies())
    tampered = replace(
        registry,
        entries=(replace(registry.entries[0], content_hash="0" * 64),),
    )
    assert not tampered.verify()
    unrelated_event = FileContinuityEvent(
        "", "file:unrelated", "app/old.py", "app/new.py",
        registry.entries[0].content_hash, registry.entries[0].content_hash,
        "r0", "r1", "architecture", "Unrelated rename",
        "2026-07-17T08:00:00+08:00",
    ).finalized()
    assert not replace(
        registry, continuity_events=(unrelated_event,),
    ).finalized().verify()

    payload = registry.to_json().replace(
        '"schema_version": "1.0"', '"schema_version": "2.0"',
    )
    with pytest.raises(ValueError, match="future"):
        RepositoryFileRegistry.from_json(payload)

    claim = FileContinuityEvent(
        "", registry.entries[0].file_id, "app/a.py", "app/b.py",
        registry.entries[0].content_hash, registry.entries[0].content_hash,
        "r1", "r2", "architecture", "Rename", "2026-07-17T08:00:00+08:00",
    ).finalized()
    with pytest.raises(ValueError, match="previous registry"):
        RepositoryFileRegistryBuilder().build(
            inventory, _policies(), continuity_claims=(claim,),
        )


def test_file_registry_has_no_runtime_scientific_or_storage_dependencies() -> None:
    capability = Path(__file__).parents[1] / "repository"
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in capability.glob("file_registry_*.py")
    )
    forbidden = (
        "app.runtime", "app.knowledge", "app.discovery",
        "psycopg", "boto3",
    )
    assert not any(item in source for item in forbidden)
