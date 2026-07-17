from dataclasses import replace

import pytest

from app.architecture.models import ArchitectureGraph
from app.architecture.repository import (
    FileGovernanceState,
    RepositoryEvolutionDecision,
    RepositoryEvolutionDryRun,
    RepositoryEvolutionDryRunEngine,
    RepositoryEvolutionPlan,
    RepositoryEvolutionPlanner,
    RepositoryEvolutionPreflight,
    RepositoryEvolutionPreflightEngine,
    RepositoryFileClassification,
    RepositoryFileEntry,
    RepositoryFileRegistry,
    RepositoryLifecycle,
    RepositoryMove,
    RepositoryPreflightOutcome,
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


def _approved_plan(registry=None) -> RepositoryEvolutionPlan:
    registry = registry or _registry()
    proposed = RepositoryEvolutionPlanner().plan(
        registry, (_move(),), proposed_by="architecture",
    )
    return replace(
        proposed,
        decision=RepositoryEvolutionDecision.APPROVED,
        decided_by="project-owner",
        decision_rationale="Impact and rollback evidence reviewed.",
    ).finalized()


def _graph(revision="r1") -> ArchitectureGraph:
    return ArchitectureGraph(
        "", "ResearchOS", source_revision=revision,
    ).finalized()


def _ready_preflight(plan=None, registry=None):
    registry = registry or _registry()
    plan = plan or _approved_plan(registry)
    return RepositoryEvolutionPreflightEngine().evaluate(
        plan, registry, _graph(registry.source_revision),
    )


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


def test_preflight_ready_is_deterministic_provenance_bound_and_non_authorizing():
    registry = _registry()
    plan = _approved_plan(registry)
    engine = RepositoryEvolutionPreflightEngine()

    first = engine.evaluate(plan, registry, _graph())
    second = engine.evaluate(plan, registry, _graph())

    assert first == second
    assert first.verify()
    assert first.outcome is RepositoryPreflightOutcome.READY
    assert first.plan_id == plan.plan_id
    assert first.plan_hash == plan.content_hash
    assert first.registry_hash == registry.content_hash
    assert first.graph_hash == _graph().content_hash
    assert first.is_execution_authorization is False
    assert all(item.passed for item in first.checks)
    assert RepositoryEvolutionPreflight.from_json(first.to_json()) == first


def test_preflight_blocks_plan_without_human_approval_with_explicit_reason():
    registry = _registry()
    proposed = RepositoryEvolutionPlanner().plan(
        registry, (_move(),), proposed_by="architecture",
    )

    result = RepositoryEvolutionPreflightEngine().evaluate(
        proposed, registry, _graph(),
    )

    assert result.outcome is RepositoryPreflightOutcome.BLOCKED
    failed = [item for item in result.checks if not item.passed]
    assert [(item.check_id, item.reason) for item in failed] == [
        ("human_approval_valid", "plan_decision_is_proposed"),
    ]


@pytest.mark.parametrize(
    "registry,graph,failed_check",
    [
        (
            replace(_registry(), source_revision="r2").finalized(),
            _graph("r2"),
            "source_revision_current",
        ),
        (
            _registry(),
            _graph("r2"),
            "architecture_graph_current",
        ),
    ],
)
def test_preflight_marks_changed_canonical_state_stale(
    registry, graph, failed_check,
):
    result = RepositoryEvolutionPreflightEngine().evaluate(
        _approved_plan(), registry, graph,
    )

    assert result.outcome is RepositoryPreflightOutcome.STALE
    assert failed_check in {
        item.check_id for item in result.checks if not item.passed
    }
    assert result.is_execution_authorization is False


def test_preflight_rejects_unverified_inputs_and_tampered_artifact():
    registry = _registry()
    plan = _approved_plan(registry)
    engine = RepositoryEvolutionPreflightEngine()

    with pytest.raises(ValueError, match="verified repository evolution plan"):
        engine.evaluate(replace(plan, content_hash="0" * 64), registry, _graph())
    with pytest.raises(ValueError, match="verified current file registry"):
        engine.evaluate(plan, replace(registry, content_hash="0" * 64), _graph())
    with pytest.raises(ValueError, match="verified current Architecture Graph"):
        engine.evaluate(
            plan, registry, replace(_graph(), content_hash="0" * 64),
        )

    result = engine.evaluate(plan, registry, _graph())
    payload = result.to_json().replace(
        '"outcome": "ready"', '"outcome": "blocked"',
    )
    with pytest.raises(ValueError, match="preflight is invalid"):
        RepositoryEvolutionPreflight.from_json(payload)


def test_dry_run_is_deterministic_reversible_provenance_bound_and_non_mutating(
    tmp_path,
):
    marker = tmp_path / "repository-marker.txt"
    marker.write_text("unchanged", encoding="utf-8")
    registry = _registry()
    plan = _approved_plan(registry)
    preflight = _ready_preflight(plan, registry)
    engine = RepositoryEvolutionDryRunEngine()

    first = engine.simulate(plan, preflight)
    second = engine.simulate(plan, preflight)

    assert first == second
    assert first.verify()
    assert first.plan_id == plan.plan_id
    assert first.plan_hash == plan.content_hash
    assert first.preflight_id == preflight.preflight_id
    assert first.preflight_hash == preflight.content_hash
    assert first.forward_steps[0].source_path == "docs/a.md"
    assert first.forward_steps[0].target_path == "Documents/a.md"
    assert first.rollback_steps[0].source_path == "Documents/a.md"
    assert first.rollback_steps[0].target_path == "docs/a.md"
    assert first.mutates_repository is False
    assert first.is_execution_authorization is False
    assert marker.read_text(encoding="utf-8") == "unchanged"
    assert RepositoryEvolutionDryRun.from_json(first.to_json()) == first


@pytest.mark.parametrize(
    "outcome,error",
    [
        (RepositoryPreflightOutcome.BLOCKED, "preflight is blocked"),
        (RepositoryPreflightOutcome.STALE, "preflight is stale"),
    ],
)
def test_dry_run_rejects_non_ready_preflight(outcome, error):
    registry = _registry()
    plan = _approved_plan(registry)
    ready = _ready_preflight(plan, registry)
    failed_check = replace(ready.checks[0], passed=False, reason="not_ready")
    preflight = replace(
        ready, outcome=outcome, checks=(failed_check, *ready.checks[1:]),
    ).finalized()

    if outcome is RepositoryPreflightOutcome.STALE:
        stale_check = replace(
            ready.checks[1], passed=False, reason="revision_changed",
        )
        preflight = replace(
            ready,
            outcome=outcome,
            checks=(ready.checks[0], stale_check, *ready.checks[2:]),
        ).finalized()

    assert preflight.verify()
    with pytest.raises(ValueError, match=error):
        RepositoryEvolutionDryRunEngine().simulate(plan, preflight)


def test_dry_run_rejects_mismatched_or_tampered_provenance():
    registry = _registry()
    first_plan = _approved_plan(registry)
    preflight = _ready_preflight(first_plan, registry)
    second_plan = replace(
        first_plan,
        decision_rationale="A separate human review produced a new plan.",
    ).finalized()

    with pytest.raises(ValueError, match="provenance do not match"):
        RepositoryEvolutionDryRunEngine().simulate(second_plan, preflight)

    dry_run = RepositoryEvolutionDryRunEngine().simulate(
        first_plan, preflight,
    )
    payload = dry_run.to_json().replace(
        '"mutates_repository": false', '"mutates_repository": true',
    )
    with pytest.raises(ValueError, match="dry run is invalid"):
        RepositoryEvolutionDryRun.from_json(payload)

    incomplete = replace(dry_run, rollback_steps=()).finalized()
    assert not incomplete.verify()
