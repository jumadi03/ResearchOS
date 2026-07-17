from dataclasses import replace
from hashlib import sha256
import os

import pytest

from app.architecture.models import ArchitectureGraph
from app.architecture.repository import (
    FileGovernanceState,
    RepositoryEvolutionDecision,
    RepositoryEvolutionDryRun,
    RepositoryEvolutionDryRunEngine,
    RepositoryEvolutionExecution,
    RepositoryEvolutionExecutor,
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
    RepositoryExecutionStatus,
    NoOverwriteFileMover,
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


def _execution_contract(root, *, two_moves=False):
    contents = {"file:a": b"alpha\n", "file:b": b"bravo\n"}
    for file_id, path in (("file:a", "docs/a.md"), ("file:b", "docs/b.md")):
        target = root.joinpath(*path.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(contents[file_id])
    hashes = {
        file_id: sha256(content).hexdigest()
        for file_id, content in contents.items()
    }
    base = _registry()
    registry = replace(
        base,
        entries=tuple(
            replace(
                entry,
                content_hash=hashes[entry.file_id],
                size=len(contents[entry.file_id]),
            )
            for entry in base.entries
        ),
    ).finalized()
    moves = (
        RepositoryMove(
            "file:a", "docs/a.md", "Documents/a.md", hashes["file:a"],
            "Apply canonical document placement.",
        ),
    )
    if two_moves:
        moves += (
            RepositoryMove(
                "file:b", "docs/b.md", "Documents/b.md", hashes["file:b"],
                "Apply canonical document placement.",
            ),
        )
    proposed = RepositoryEvolutionPlanner().plan(
        registry, moves, proposed_by="architecture",
    )
    plan = replace(
        proposed,
        decision=RepositoryEvolutionDecision.APPROVED,
        decided_by="project-owner",
        decision_rationale="Isolated execution approved.",
    ).finalized()
    preflight = RepositoryEvolutionPreflightEngine().evaluate(
        plan, registry, _graph(),
    )
    dry_run = RepositoryEvolutionDryRunEngine().simulate(plan, preflight)
    return plan, preflight, dry_run


class _FailingMover:
    def __init__(self, fail_calls):
        self.calls = 0
        self.fail_calls = set(fail_calls)
        self.delegate = NoOverwriteFileMover()

    def move(self, source, target):
        self.calls += 1
        if self.calls in self.fail_calls:
            raise OSError("injected_move_failure")
        self.delegate.move(source, target)


def test_isolated_executor_completes_without_overwrite_and_preserves_hash(
    tmp_path,
):
    plan, preflight, dry_run = _execution_contract(tmp_path, two_moves=True)

    result = RepositoryEvolutionExecutor(tmp_path).execute(
        plan, preflight, dry_run,
    )

    assert result.status is RepositoryExecutionStatus.COMPLETED
    assert result.verify()
    assert not result.requires_recovery
    assert not (tmp_path / "docs/a.md").exists()
    assert not (tmp_path / "docs/b.md").exists()
    assert (tmp_path / "Documents/a.md").read_bytes() == b"alpha\n"
    assert (tmp_path / "Documents/b.md").read_bytes() == b"bravo\n"
    assert RepositoryEvolutionExecution.from_json(result.to_json()) == result


def test_executor_rolls_back_all_completed_moves_after_mid_transaction_failure(
    tmp_path,
):
    plan, preflight, dry_run = _execution_contract(tmp_path, two_moves=True)

    result = RepositoryEvolutionExecutor(
        tmp_path, mover=_FailingMover({2}),
    ).execute(plan, preflight, dry_run)

    assert result.status is RepositoryExecutionStatus.ROLLED_BACK
    assert not result.requires_recovery
    assert (tmp_path / "docs/a.md").read_bytes() == b"alpha\n"
    assert (tmp_path / "docs/b.md").read_bytes() == b"bravo\n"
    assert not (tmp_path / "Documents/a.md").exists()
    assert not (tmp_path / "Documents/b.md").exists()
    assert not (tmp_path / "Documents").exists()


def test_executor_reports_recovery_required_if_rollback_itself_fails(tmp_path):
    plan, preflight, dry_run = _execution_contract(tmp_path, two_moves=True)

    result = RepositoryEvolutionExecutor(
        tmp_path, mover=_FailingMover({2, 3}),
    ).execute(plan, preflight, dry_run)

    assert result.status is RepositoryExecutionStatus.RECOVERY_REQUIRED
    assert result.requires_recovery
    assert not (tmp_path / "docs/a.md").exists()
    assert (tmp_path / "Documents/a.md").read_bytes() == b"alpha\n"
    assert result.verify()


def test_executor_rejects_existing_target_and_stale_source_without_mutation(
    tmp_path,
):
    plan, preflight, dry_run = _execution_contract(tmp_path)
    target = tmp_path / "Documents/a.md"
    target.parent.mkdir(parents=True)
    target.write_text("existing", encoding="utf-8")

    with pytest.raises(ValueError, match="Target already exists"):
        RepositoryEvolutionExecutor(tmp_path).execute(plan, preflight, dry_run)
    assert (tmp_path / "docs/a.md").read_bytes() == b"alpha\n"
    assert target.read_text(encoding="utf-8") == "existing"

    target.unlink()
    (tmp_path / "docs/a.md").write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="Source hash is stale"):
        RepositoryEvolutionExecutor(tmp_path).execute(plan, preflight, dry_run)
    assert not target.exists()


def test_executor_rejects_symlink_escape(tmp_path):
    plan, preflight, dry_run = _execution_contract(tmp_path)
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    link = tmp_path / "Documents"
    try:
        os.symlink(outside, link, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation is not available on this platform")

    with pytest.raises(ValueError, match="Symlink path is not allowed"):
        RepositoryEvolutionExecutor(tmp_path).execute(plan, preflight, dry_run)
    assert not (outside / "a.md").exists()
    assert (tmp_path / "docs/a.md").exists()


def test_executor_rejects_cross_contract_provenance_before_mutation(tmp_path):
    plan, preflight, dry_run = _execution_contract(tmp_path)
    other_plan = replace(
        plan, decision_rationale="A different approved execution.",
    ).finalized()

    with pytest.raises(ValueError, match="provenance does not match"):
        RepositoryEvolutionExecutor(tmp_path).execute(
            other_plan, preflight, dry_run,
        )
    assert (tmp_path / "docs/a.md").read_bytes() == b"alpha\n"
