from dataclasses import replace
import json
from pathlib import Path

import pytest

from app.architecture.repository import (
    RepositoryFileRegistryBuilder,
    RepositoryHealthCategory,
    RepositoryHealthEngine,
    RepositoryHealthOutcome,
    RepositoryHealthReport,
    RepositoryLifecycle,
    RepositoryLifecyclePolicy,
    RepositoryNamingPolicy,
    RepositoryOwnershipPolicy,
    RepositoryPlacementNamingVerifier,
    RepositoryPlacementPolicy,
    RepositoryPolicyBundle,
    RepositoryPolicyRegistry,
    RepositoryScanner,
    RepositoryTraceabilityGraphBuilder,
)
from app.architecture.repository.models import RepositoryFileClassification


def _write(root: Path, path: str, content: str) -> None:
    target = root.joinpath(*path.split("/"))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _bundle() -> RepositoryPolicyBundle:
    return RepositoryPolicyBundle(
        "", "ResearchOS", "1.0", "policy-r1",
        ownership_policies=(
            RepositoryOwnershipPolicy(
                "owner.app", "1.0", ("AI-Gateway/app/**",),
                "Architecture Engine", "Architecture",
                "Architecture Engine", "Repository Management",
                "Application ownership.",
            ),
        ),
        placement_policies=(
            RepositoryPlacementPolicy(
                "place.app", "1.0", ("AI-Gateway/app/**",),
                (
                    RepositoryFileClassification.CODE,
                    RepositoryFileClassification.TEST,
                ),
                (".py",), (".pdf",), "Application placement.",
            ),
        ),
        naming_policies=(
            RepositoryNamingPolicy(
                "name.python", "1.0", ("AI-Gateway/**/*.py",),
                r"^(__init__|test_[a-z][a-z0-9_]*|[a-z][a-z0-9_]*)\.py$",
                ("module.py",), "Python naming.",
            ),
        ),
        lifecycle_policies=(
            RepositoryLifecyclePolicy(
                "life.app", "1.0", ("AI-Gateway/app/**",),
                RepositoryLifecycle.RETAIN, "Review on replacement.",
                "Application lifecycle.",
            ),
        ),
    ).finalized()


def _inputs(tmp_path: Path):
    _write(tmp_path, "AI-Gateway/app/a.py", "same = 1\n")
    _write(tmp_path, "AI-Gateway/app/b.py", "same = 1\n")
    _write(tmp_path, "AI-Gateway/app/empty_a.py", "")
    _write(tmp_path, "AI-Gateway/app/empty_b.py", "")
    _write(tmp_path, "AI-Gateway/build/leak.txt", "generated\n")
    _write(tmp_path, "Documents/ROADMAP.md", "# Roadmap\n")
    paths = (
        "AI-Gateway/app/a.py",
        "AI-Gateway/app/b.py",
        "AI-Gateway/app/empty_a.py",
        "AI-Gateway/app/empty_b.py",
        "AI-Gateway/build/leak.txt",
        "Documents/ROADMAP.md",
    )
    policies = RepositoryPolicyRegistry(_bundle())
    inventory = RepositoryScanner(tmp_path).scan(
        paths, project_name="ResearchOS", source_revision="r1",
    )
    registry = RepositoryFileRegistryBuilder().build(inventory, policies)
    verification = RepositoryPlacementNamingVerifier().verify(
        registry, policies, as_of="2026-07-17",
    )
    graph = RepositoryTraceabilityGraphBuilder(
        tmp_path / "AI-Gateway", "AI-Gateway",
    ).build(registry, policies, verification)
    return registry, verification, graph


def _check(report: RepositoryHealthReport, category: RepositoryHealthCategory):
    return next(item for item in report.checks if item.category is category)


def test_health_report_separates_findings_advisories_and_unknowns(
    tmp_path: Path,
) -> None:
    registry, verification, graph = _inputs(tmp_path)

    report = RepositoryHealthEngine().assess(
        registry, verification, graph, as_of="2026-07-17",
    )

    assert report.verify()
    assert report.status == "INCOMPLETE"
    assert report.is_compliance_decision is False
    leakage = _check(report, RepositoryHealthCategory.CANONICAL_LEAKAGE)
    assert leakage.outcome is RepositoryHealthOutcome.FINDING
    assert leakage.affected_paths == ("AI-Gateway/build/leak.txt",)
    governance = _check(report, RepositoryHealthCategory.GOVERNANCE_COVERAGE)
    assert governance.outcome is RepositoryHealthOutcome.FINDING
    assert set(governance.affected_paths) == {
        "AI-Gateway/build/leak.txt", "Documents/ROADMAP.md",
    }
    policy_coverage = _check(
        report, RepositoryHealthCategory.POLICY_COVERAGE,
    )
    assert policy_coverage.outcome is RepositoryHealthOutcome.FINDING
    assert policy_coverage.evidence_ids

    duplication = _check(
        report, RepositoryHealthCategory.NON_EMPTY_EXACT_DUPLICATION,
    )
    assert duplication.outcome is RepositoryHealthOutcome.ADVISORY
    assert set(duplication.affected_paths) == {
        "AI-Gateway/app/a.py", "AI-Gateway/app/b.py",
    }
    assert "empty_a.py" not in " ".join(duplication.affected_paths)

    tests = _check(
        report, RepositoryHealthCategory.CAPABILITY_TEST_PRESENCE,
    )
    assert tests.outcome is RepositoryHealthOutcome.ADVISORY
    assert tests.details["capabilities"] == ["Repository Management"]

    for category in (
        RepositoryHealthCategory.DEAD_FILE_ANALYSIS,
        RepositoryHealthCategory.STALENESS,
        RepositoryHealthCategory.EXECUTION_COVERAGE,
        RepositoryHealthCategory.DOCUMENTATION_COVERAGE,
    ):
        item = _check(report, category)
        assert item.outcome is RepositoryHealthOutcome.NOT_EVALUATED
        assert item.details["reason"]


def test_health_report_is_deterministic_round_trippable_and_tamper_evident(
    tmp_path: Path,
) -> None:
    registry, verification, graph = _inputs(tmp_path)
    engine = RepositoryHealthEngine()

    first = engine.assess(
        registry, verification, graph, as_of="2026-07-17",
    )
    second = engine.assess(
        registry, verification, graph, as_of="2026-07-17",
    )

    assert first == second
    assert RepositoryHealthReport.from_json(first.to_json()) == first
    tampered = replace(
        first,
        checks=(
            replace(first.checks[0], summary="tampered"),
            *first.checks[1:],
        ),
    )
    assert not tampered.verify()
    payload = json.loads(first.to_json())
    payload["status"] = "OBSERVED"
    with pytest.raises(ValueError, match="invalid"):
        RepositoryHealthReport.from_json(json.dumps(payload))
    payload = json.loads(first.to_json())
    payload["schema_version"] = "2.0"
    with pytest.raises(ValueError, match="future"):
        RepositoryHealthReport.from_json(json.dumps(payload))


def test_health_direct_invocation_rejects_stale_or_tampered_inputs(
    tmp_path: Path,
) -> None:
    registry, verification, graph = _inputs(tmp_path)
    engine = RepositoryHealthEngine()

    with pytest.raises(ValueError, match="integrity"):
        engine.assess(
            replace(registry, content_hash="0" * 64),
            verification, graph, as_of="2026-07-17",
        )
    stale_graph = replace(
        graph, source_revision="r2", graph_id="", content_hash="",
    ).finalized()
    with pytest.raises(ValueError, match="provenance"):
        engine.assess(
            registry, verification, stale_graph, as_of="2026-07-17",
        )


def test_health_has_no_runtime_scientific_storage_or_compliance_dependency() -> None:
    capability = Path(__file__).parents[1] / "repository"
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            capability / "health_models.py",
            capability / "health_engine.py",
        )
    )
    forbidden = (
        "app.runtime", "app.knowledge", "app.discovery",
        "psycopg", "boto3", "ComplianceEngine", "ArchitectureViolation",
    )
    assert not any(item in source for item in forbidden)
