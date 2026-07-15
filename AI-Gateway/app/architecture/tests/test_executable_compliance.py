from pathlib import Path

from app.architecture import ArchitectureGraphBuilder
from app.architecture.governance import (
    ComplianceEngine,
    DependencyValidator,
    LawRegistry,
    LawResolution,
    PublicAPIValidator,
    ValidatorRegistry,
)
from app.architecture.models import (
    ArchitectureLaw,
    ArchitectureLawBundle,
    LawScope,
    ValidationStatus,
)


def _graph(tmp_path: Path, *, include_api_init: bool = True):
    kernel = tmp_path / "app" / "kernel"
    infrastructure = tmp_path / "app" / "infrastructure"
    contracts = kernel / "contracts"
    contracts.mkdir(parents=True)
    infrastructure.mkdir(parents=True)
    (tmp_path / "app" / "__init__.py").write_text("", encoding="utf-8")
    (kernel / "__init__.py").write_text("", encoding="utf-8")
    (infrastructure / "__init__.py").write_text("", encoding="utf-8")
    if include_api_init:
        (contracts / "__init__.py").write_text("", encoding="utf-8")
    (contracts / "api.py").write_text("class Contract: pass\n", encoding="utf-8")
    (kernel / "service.py").write_text(
        "from app.infrastructure import database\n",
        encoding="utf-8",
    )
    return ArchitectureGraphBuilder(tmp_path, "sample", "revision-1").build()


def _resolution(*laws: ArchitectureLaw) -> LawResolution:
    bundle = ArchitectureLawBundle("", "1.0.0", laws).finalized()
    return LawResolution(LawRegistry.from_bundle(bundle))


def test_dependency_validator_finds_forbidden_import_with_evidence(
    tmp_path: Path,
) -> None:
    graph = _graph(tmp_path)
    law = ArchitectureLaw(
        "ALA-DEP-001",
        "Kernel isolation",
        "Kernel cannot import infrastructure",
        "1.0.0",
        category="Dependency",
        scope=LawScope(node_types=("Module",), path_patterns=("app/kernel/**",)),
        condition={"relation": "IMPORTS", "forbidden_target": "app.infrastructure*"},
        remediation="Move the dependency behind a kernel contract.",
    )

    result = DependencyValidator(_resolution(law), graph).validate()

    assert result.status is ValidationStatus.FAIL
    assert len(result.violations) == 1
    violation = result.violations[0]
    assert violation.law is law
    assert violation.fact.fact_name == "IMPORTS"
    assert violation.fact.fact_value == "app.infrastructure"
    assert violation.metadata["source_path"] == "app/kernel/service.py"
    assert violation.metadata["lines"] == [1]


def test_dependency_validator_passes_when_target_is_allowed(tmp_path: Path) -> None:
    graph = _graph(tmp_path)
    law = ArchitectureLaw(
        "ALA-DEP-002",
        "No legacy imports",
        "Legacy package is forbidden",
        "1.0.0",
        category="Dependency",
        scope=LawScope(node_types=("Module",), path_patterns=("app/kernel/**",)),
        condition={"relation": "IMPORTS", "forbidden_target": "legacy*"},
    )
    result = DependencyValidator(_resolution(law), graph).validate()
    assert result.status is ValidationStatus.PASS
    assert result.violations == ()


def test_public_api_validator_requires_package_init(tmp_path: Path) -> None:
    graph = _graph(tmp_path, include_api_init=False)
    law = ArchitectureLaw(
        "ALA-API-001",
        "Public package namespace",
        "Contract packages expose a package namespace",
        "1.0.0",
        category="PublicAPI",
        scope=LawScope(
            node_types=("Module",),
            path_patterns=("app/kernel/contracts/*.py",),
        ),
        condition={"type": "REQUIRE_PACKAGE_INIT"},
    )
    result = PublicAPIValidator(_resolution(law), graph).validate()
    assert result.status is ValidationStatus.FAIL
    assert len(result.violations) == 1
    assert result.violations[0].metadata["required_module"] == (
        "app.kernel.contracts.__init__"
    )


def test_compliance_engine_runs_validators_against_graph(tmp_path: Path) -> None:
    graph = _graph(tmp_path)
    law = ArchitectureLaw(
        "ALA-DEP-001",
        "Kernel isolation",
        "Kernel cannot import infrastructure",
        "1.0.0",
        category="Dependency",
        scope=LawScope(node_types=("Module",), path_patterns=("app/kernel/**",)),
        condition={"relation": "IMPORTS", "forbidden_target": "app.infrastructure*"},
    )
    resolution = _resolution(law)
    engine = ComplianceEngine(
        ValidatorRegistry(
            validators=(
                DependencyValidator(resolution),
                PublicAPIValidator(resolution),
            )
        )
    )
    report = engine.validate(graph, as_of="2026-07-15")
    assert report.status == "FAIL"
    assert report.is_compliant is False
    assert report.metadata["graph_hash"] == graph.content_hash
    assert report.validation_results[0].status is ValidationStatus.FAIL
    assert report.validation_results[1].status is ValidationStatus.NOT_APPLICABLE
