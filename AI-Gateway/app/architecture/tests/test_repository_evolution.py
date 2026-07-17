from dataclasses import replace

import pytest

from app.architecture.repository import (
    FileGovernanceState,
    RepositoryEvolutionDecision,
    RepositoryEvolutionPlan,
    RepositoryEvolutionPlanner,
    RepositoryFileClassification,
    RepositoryFileEntry,
    RepositoryFileRegistry,
    RepositoryLifecycle,
    RepositoryMove,
)


HASH_A = "a" * 64
HASH_B = "b" * 64


def _registry() -> RepositoryFileRegistry:
    entries = (
        RepositoryFileEntry(
            "file:a", "docs/a.md", HASH_A,
            RepositoryFileClassification.DOCUMENT, 10, ".md", "r1", (),
            "architecture", "Architecture", "Architecture Engine",
            "Repository Management", RepositoryLifecycle.RETAIN,
            ("owner.docs",), (), FileGovernanceState.ASSIGNED,
        ),
        RepositoryFileEntry(
            "file:b", "docs/b.md", HASH_B,
            RepositoryFileClassification.DOCUMENT, 10, ".md", "r1", (),
            "architecture", "Architecture", "Architecture Engine",
            "Repository Management", RepositoryLifecycle.RETAIN,
            ("owner.docs",), (), FileGovernanceState.ASSIGNED,
        ),
    )
    return RepositoryFileRegistry(
        "", "ResearchOS", "r1", "inventory:1", "c" * 64,
        "policy:1", "d" * 64, entries,
    ).finalized()


def _move(**changes) -> RepositoryMove:
    values = {
        "file_id": "file:a",
        "source_path": "docs/a.md",
        "target_path": "Documents/a.md",
        "content_hash": HASH_A,
        "rationale": "Align the document with canonical placement policy.",
    }
    values.update(changes)
    return RepositoryMove(**values)


def test_plan_is_deterministic_provenance_bound_reversible_and_non_executable():
    registry = _registry()
    planner = RepositoryEvolutionPlanner()

    first = planner.plan(
        registry, (_move(),), proposed_by="project-owner",
    )
    second = planner.plan(
        registry, (_move(),), proposed_by="project-owner",
    )

    assert first == second
    assert first.verify()
    assert first.registry_id == registry.registry_id
    assert first.registry_hash == registry.content_hash
    assert first.rollback_moves[0].source_path == "Documents/a.md"
    assert first.rollback_moves[0].target_path == "docs/a.md"
    assert first.decision is RepositoryEvolutionDecision.PROPOSED
    assert first.is_executable is False
    assert RepositoryEvolutionPlan.from_json(first.to_json()) == first


@pytest.mark.parametrize(
    "move,error",
    [
        (_move(file_id="file:missing"), "Unknown source"),
        (_move(source_path="docs/old.md"), "Stale source"),
        (_move(content_hash="e" * 64), "Stale source"),
        (_move(target_path="docs/b.md"), "already occupied"),
    ],
)
def test_planner_rejects_unknown_stale_or_occupied_moves(move, error):
    with pytest.raises(ValueError, match=error):
        RepositoryEvolutionPlanner().plan(
            _registry(), (move,), proposed_by="project-owner",
        )


def test_plan_rejects_duplicate_targets_and_incomplete_rollback():
    registry = _registry()
    plan = RepositoryEvolutionPlanner().plan(
        registry, (_move(),), proposed_by="project-owner",
    )
    duplicate = replace(
        plan,
        moves=(
            _move(),
            _move(
                file_id="file:b", source_path="docs/b.md",
                content_hash=HASH_B,
            ),
        ),
    ).finalized()
    incomplete = replace(plan, rollback_moves=()).finalized()

    assert not duplicate.verify()
    assert not incomplete.verify()
    with pytest.raises(ValueError):
        RepositoryEvolutionPlan.from_json(incomplete.to_json())


def test_human_decision_requires_attribution_and_rationale():
    plan = RepositoryEvolutionPlanner().plan(
        _registry(), (_move(),), proposed_by="architecture",
    )
    invalid = replace(
        plan, decision=RepositoryEvolutionDecision.APPROVED,
    ).finalized()
    approved = replace(
        plan,
        decision=RepositoryEvolutionDecision.APPROVED,
        decided_by="project-owner",
        decision_rationale="Reviewed impact and rollback evidence.",
    ).finalized()

    assert not invalid.verify()
    assert approved.verify()
    assert approved.is_executable is False
