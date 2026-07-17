from dataclasses import replace
import json
from pathlib import Path

import pytest

from app.architecture.repository import (
    RepositoryFileRegistryBuilder,
    RepositoryLifecycle,
    RepositoryLifecyclePolicy,
    RepositoryNamingPolicy,
    RepositoryOwnershipPolicy,
    RepositoryPlacementNamingVerifier,
    RepositoryPlacementPolicy,
    RepositoryPolicyBundle,
    RepositoryPolicyDomain,
    RepositoryPolicyException,
    RepositoryPolicyRegistry,
    RepositoryScanner,
    RepositoryVerificationMode,
    RepositoryVerificationOutcome,
    RepositoryVerificationReport,
)
from app.architecture.repository.models import RepositoryFileClassification


def _write(root: Path, path: str, content: str = "content\n") -> None:
    target = root.joinpath(*path.split("/"))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _bundle(
    *,
    exceptions: tuple[RepositoryPolicyException, ...] = (),
    second_naming: bool = False,
    version: str = "1.0",
) -> RepositoryPolicyBundle:
    naming = [
        RepositoryNamingPolicy(
            "name.python", "1.0", ("app/**",),
            r"^[a-z][a-z0-9_]*\.py$", ("module.py",),
            "Python modules use snake_case names.",
        )
    ]
    if second_naming:
        naming.append(RepositoryNamingPolicy(
            "name.no_private", "1.0", ("app/**",),
            r"^[a-z][a-z0-9_]*\.py$", ("public.py",),
            "Application modules use public names.",
        ))
    return RepositoryPolicyBundle(
        "", "ResearchOS", version, "policy-r1",
        ownership_policies=(
            RepositoryOwnershipPolicy(
                "owner.app", "1.0", ("app/**",), "architecture",
                "Architecture", "Architecture Engine",
                "Repository Management", "Explicit fixture ownership.",
            ),
        ),
        placement_policies=(
            RepositoryPlacementPolicy(
                "place.python", "1.0", ("app/**",),
                (
                    RepositoryFileClassification.CODE,
                    RepositoryFileClassification.TEST,
                ),
                (".py",), (".pdf",), "Application placement fixture.",
            ),
        ),
        naming_policies=tuple(naming),
        lifecycle_policies=(
            RepositoryLifecyclePolicy(
                "life.app", "1.0", ("app/**",),
                RepositoryLifecycle.RETAIN, "Review on replacement.",
                "Application files are retained.",
            ),
        ),
        exceptions=exceptions,
    ).finalized()


def _registry(
    root: Path,
    paths: tuple[str, ...],
    bundle: RepositoryPolicyBundle,
):
    inventory = RepositoryScanner(root).scan(
        paths, project_name="ResearchOS", source_revision="r1",
    )
    policies = RepositoryPolicyRegistry(bundle)
    registry = RepositoryFileRegistryBuilder().build(inventory, policies)
    return registry, policies


def _by_path_domain(report, path: str, domain: RepositoryPolicyDomain):
    return tuple(
        item for item in report.evaluations
        if item.path == path and item.domain is domain
    )


def test_verifier_reports_conformance_findings_and_uncovered_scope(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "app/good.py")
    _write(tmp_path, "app/Bad.py")
    _write(tmp_path, "app/paper.pdf")
    _write(tmp_path, "misc/readme.md")
    registry, policies = _registry(
        tmp_path,
        ("app/good.py", "app/Bad.py", "app/paper.pdf", "misc/readme.md"),
        _bundle(),
    )

    report = RepositoryPlacementNamingVerifier().verify(
        registry, policies, as_of="2026-07-17",
    )

    assert report.verify()
    assert report.mode is RepositoryVerificationMode.REPORT_ONLY
    assert report.is_compliance_decision is False
    assert report.finding_count == 3
    assert report.excepted_count == 0
    assert _by_path_domain(
        report, "app/good.py", RepositoryPolicyDomain.PLACEMENT,
    )[0].outcome is RepositoryVerificationOutcome.CONFORMS
    bad_name = _by_path_domain(
        report, "app/Bad.py", RepositoryPolicyDomain.NAMING,
    )[0]
    assert bad_name.outcome is RepositoryVerificationOutcome.FINDING
    assert bad_name.reasons == ("name_pattern_mismatch",)
    bad_placement = _by_path_domain(
        report, "app/paper.pdf", RepositoryPolicyDomain.PLACEMENT,
    )[0]
    assert bad_placement.reasons == (
        "classification_not_allowed",
        "extension_forbidden",
        "extension_not_allowed",
    )
    uncovered = _by_path_domain(
        report, "misc/readme.md", RepositoryPolicyDomain.PLACEMENT,
    )[0]
    assert uncovered.outcome is RepositoryVerificationOutcome.NOT_EVALUATED
    assert uncovered.policy_id is None


def test_every_matching_policy_is_evaluated(tmp_path: Path) -> None:
    _write(tmp_path, "app/good.py")
    registry, policies = _registry(
        tmp_path, ("app/good.py",), _bundle(second_naming=True),
    )

    report = RepositoryPlacementNamingVerifier().verify(
        registry, policies, as_of="2026-07-17",
    )

    naming = _by_path_domain(
        report, "app/good.py", RepositoryPolicyDomain.NAMING,
    )
    assert {item.policy_id for item in naming} == {
        "name.python", "name.no_private",
    }
    assert all(
        item.outcome is RepositoryVerificationOutcome.CONFORMS
        for item in naming
    )


def test_exception_is_temporal_attributable_and_never_a_compliance_pass(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "app/Bad.py")
    exception = RepositoryPolicyException(
        "exception.bad-name", ("name.python",), ("app/Bad.py",),
        "Temporary compatibility exception.", "architecture",
        "2026-01-01", expires_at="2026-12-31",
    )
    registry, policies = _registry(
        tmp_path, ("app/Bad.py",), _bundle(exceptions=(exception,)),
    )
    verifier = RepositoryPlacementNamingVerifier()

    active = verifier.verify(registry, policies, as_of="2026-07-17")
    expired = verifier.verify(registry, policies, as_of="2027-01-01")

    active_name = _by_path_domain(
        active, "app/Bad.py", RepositoryPolicyDomain.NAMING,
    )[0]
    expired_name = _by_path_domain(
        expired, "app/Bad.py", RepositoryPolicyDomain.NAMING,
    )[0]
    assert active_name.outcome is RepositoryVerificationOutcome.EXCEPTED
    assert active_name.exception_ids == ("exception.bad-name",)
    assert active.excepted_count == 1
    assert active.is_compliance_decision is False
    assert expired_name.outcome is RepositoryVerificationOutcome.FINDING
    assert expired_name.exception_ids == ()


def test_report_is_deterministic_round_trippable_and_tamper_evident(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "app/good.py")
    registry, policies = _registry(
        tmp_path, ("app/good.py",), _bundle(),
    )
    verifier = RepositoryPlacementNamingVerifier()

    first = verifier.verify(registry, policies, as_of="2026-07-17")
    second = verifier.verify(registry, policies, as_of="2026-07-17")

    assert first == second
    assert RepositoryVerificationReport.from_json(first.to_json()) == first
    assert not replace(
        first,
        evaluations=(
            replace(first.evaluations[0], path="app/tampered.py"),
            *first.evaluations[1:],
        ),
    ).verify()
    payload = json.loads(first.to_json())
    payload["finding_count"] = 99
    with pytest.raises(ValueError, match="invalid"):
        RepositoryVerificationReport.from_json(json.dumps(payload))
    payload = json.loads(first.to_json())
    payload["schema_version"] = "2.0"
    with pytest.raises(ValueError, match="future"):
        RepositoryVerificationReport.from_json(json.dumps(payload))


def test_direct_invocation_rejects_stale_policy_invalid_inputs_and_bad_date(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "app/good.py")
    registry, policies = _registry(
        tmp_path, ("app/good.py",), _bundle(),
    )
    stale = RepositoryPolicyRegistry(_bundle(version="1.1"))
    verifier = RepositoryPlacementNamingVerifier()

    with pytest.raises(ValueError, match="provenance"):
        verifier.verify(registry, stale, as_of="2026-07-17")
    with pytest.raises(ValueError, match="ISO date"):
        verifier.verify(registry, policies, as_of="17-07-2026")
    with pytest.raises(ValueError, match="integrity"):
        verifier.verify(
            replace(registry, content_hash="0" * 64),
            policies, as_of="2026-07-17",
        )


def test_verifier_has_no_runtime_scientific_storage_or_compliance_dependency() -> None:
    capability = Path(__file__).parents[1] / "repository"
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            capability / "verification_models.py",
            capability / "placement_naming_verifier.py",
        )
    )
    forbidden = (
        "app.runtime", "app.knowledge", "app.discovery",
        "psycopg", "boto3", "ComplianceEngine", "ArchitectureViolation",
    )
    assert not any(item in source for item in forbidden)
