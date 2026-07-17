from dataclasses import replace
import json
from pathlib import Path

import pytest

from app.architecture import ArchitectureGraphBuilder
from app.architecture.models import (
    ArchitectureEdge,
    ArchitectureGraph,
    ArchitectureNode,
)
from app.architecture.repository import (
    RepositoryFileRegistryBuilder,
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
    RepositoryVerificationReport,
)
from app.architecture.repository.models import RepositoryFileClassification


def _write(root: Path, path: str, content: str = "value = 1\n") -> None:
    target = root.joinpath(*path.split("/"))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _bundle(
    ownership: tuple[RepositoryOwnershipPolicy, ...] | None = None,
    *,
    version: str = "1.0",
) -> RepositoryPolicyBundle:
    return RepositoryPolicyBundle(
        "", "ResearchOS", version, "policy-r1",
        ownership_policies=ownership or (
            RepositoryOwnershipPolicy(
                "owner.app", "1.0", ("AI-Gateway/app/**",),
                "Architecture Engine", "Architecture",
                "Architecture Engine", "Repository Management",
                "Application architecture ownership.",
            ),
            RepositoryOwnershipPolicy(
                "owner.docs", "1.0", ("Documents/**",),
                "Governance Capability", "Architecture",
                "Architecture Engine", "Governance Documentation",
                "Documentation ownership.",
            ),
        ),
        placement_policies=(
            RepositoryPlacementPolicy(
                "place.app", "1.0", ("AI-Gateway/app/**",),
                (
                    RepositoryFileClassification.CODE,
                    RepositoryFileClassification.TEST,
                ),
                (".py",), (".pdf",), "Python source placement.",
            ),
        ),
        naming_policies=(
            RepositoryNamingPolicy(
                "name.python", "1.0", ("AI-Gateway/**/*.py",),
                r"^(__init__|test_[a-z][a-z0-9_]*|[a-z][a-z0-9_]*)\.py$",
                ("module.py",), "Python source naming.",
            ),
        ),
        lifecycle_policies=(
            RepositoryLifecyclePolicy(
                "life.app", "1.0", ("AI-Gateway/app/**",),
                RepositoryLifecycle.RETAIN, "Review on replacement.",
                "Application source lifecycle.",
            ),
            RepositoryLifecyclePolicy(
                "life.docs", "1.0", ("Documents/**",),
                RepositoryLifecycle.ARCHIVE, "Review on supersession.",
                "Document lifecycle.",
            ),
        ),
    ).finalized()


def _inputs(
    root: Path,
    *,
    bundle: RepositoryPolicyBundle | None = None,
    paths: tuple[str, ...] = (
        "AI-Gateway/app/__init__.py",
        "AI-Gateway/app/service.py",
        "Documents/ROADMAP.md",
    ),
):
    selected_bundle = bundle or _bundle()
    policies = RepositoryPolicyRegistry(selected_bundle)
    inventory = RepositoryScanner(root).scan(
        paths, project_name="ResearchOS", source_revision="r1",
    )
    registry = RepositoryFileRegistryBuilder().build(inventory, policies)
    report = RepositoryPlacementNamingVerifier().verify(
        registry, policies, as_of="2026-07-17",
    )
    return registry, policies, report


def test_selected_source_graph_excludes_generated_and_temporary_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write(tmp_path, "AI-Gateway/app/service.py")
    _write(tmp_path, "AI-Gateway/build/lib/copied.py")
    _write(tmp_path, "AI-Gateway/tmp/test/leaked.py")
    monkeypatch.chdir(tmp_path)

    graph = ArchitectureGraphBuilder(
        Path("AI-Gateway"), "ResearchOS", "r1", ("app/service.py",),
    ).build()

    internal = {
        node.source_path for node in graph.nodes
        if node.node_type == "Module" and not node.metadata.get("external")
    }
    assert internal == {"app/service.py"}
    assert graph.schema_version == "1.1"


def test_traceability_extends_one_canonical_graph_with_exact_provenance(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "AI-Gateway/app/__init__.py", "")
    _write(
        tmp_path, "AI-Gateway/app/service.py",
        "from app import value\n\nclass Service:\n    pass\n",
    )
    _write(tmp_path, "Documents/ROADMAP.md", "# Roadmap\n")
    _write(tmp_path, "AI-Gateway/tmp/leak.py")
    registry, policies, report = _inputs(tmp_path)

    graph = RepositoryTraceabilityGraphBuilder(
        tmp_path / "AI-Gateway", "AI-Gateway",
    ).build(registry, policies, report)

    assert graph.verify()
    assert graph.schema_version == "1.1"
    assert graph.project_name == "ResearchOS"
    nodes = {item.node_id: item for item in graph.nodes}
    relations = {(item.source_id, item.target_id, item.relation_type)
                 for item in graph.edges}
    service = next(
        item for item in registry.entries
        if item.current_path == "AI-Gateway/app/service.py"
    )
    module_id = "module:app.service"
    assert service.file_id in nodes
    assert nodes[service.file_id].node_type == "File"
    assert (module_id, service.file_id, "REPRESENTED_BY") in relations
    assert not any(
        node.source_path == "tmp/leak.py" for node in graph.nodes
    )
    provenance = nodes["project:ResearchOS"].metadata[
        "repository_traceability"
    ]
    assert provenance["registry_hash"] == registry.content_hash
    assert provenance["policy_bundle_hash"] == policies.bundle.content_hash
    assert provenance["verification_report_hash"] == report.content_hash
    assert {node.node_type for node in graph.nodes}.issuperset({
        "Project", "Module", "Class", "File", "RepositoryPolicy",
        "RepositoryEvaluation", "Subsystem", "Engine", "Capability",
    })
    assert any(
        edge.relation_type == "OWNS" and edge.target_id == service.file_id
        for edge in graph.edges
    )


def test_graph_1_0_remains_readable_while_new_graph_is_1_1() -> None:
    legacy = ArchitectureGraph(
        "", "ResearchOS",
        nodes=(ArchitectureNode("project:ResearchOS", "Project", "ResearchOS"),),
        schema_version="1.0",
    ).finalized()

    restored = ArchitectureGraph.from_json(legacy.to_json())

    assert restored == legacy
    assert restored.schema_version == "1.0"


def test_graph_integrity_rejects_duplicate_nodes_edges_and_orphans() -> None:
    node = ArchitectureNode("project:ResearchOS", "Project", "ResearchOS")
    duplicate_nodes = ArchitectureGraph(
        "", "ResearchOS", nodes=(node, node),
    ).finalized()
    assert not duplicate_nodes.verify()

    orphan = ArchitectureGraph(
        "", "ResearchOS", nodes=(node,),
        edges=(ArchitectureEdge(
            "edge:orphan", node.node_id, "file:missing", "CONTAINS",
        ),),
    ).finalized()
    assert not orphan.verify()

    edge = ArchitectureEdge(
        "edge:self", node.node_id, node.node_id, "CONTAINS",
    )
    duplicate_edges = ArchitectureGraph(
        "", "ResearchOS", nodes=(node,), edges=(edge, edge),
    ).finalized()
    assert not duplicate_edges.verify()


def test_traceability_rejects_stale_tampered_and_missing_sources(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "AI-Gateway/app/__init__.py", "")
    _write(tmp_path, "AI-Gateway/app/service.py")
    _write(tmp_path, "Documents/ROADMAP.md", "# Roadmap\n")
    registry, policies, report = _inputs(tmp_path)
    builder = RepositoryTraceabilityGraphBuilder(
        tmp_path / "AI-Gateway", "AI-Gateway",
    )

    with pytest.raises(ValueError, match="provenance"):
        builder.build(
            registry, RepositoryPolicyRegistry(_bundle(version="1.1")), report,
        )
    with pytest.raises(ValueError, match="integrity"):
        builder.build(
            replace(registry, content_hash="0" * 64), policies, report,
        )
    unrelated_evaluation = replace(
        report.evaluations[0],
        file_id="file:unknown",
        evaluation_id="",
        evidence_hash="",
    ).finalized()
    unrelated_report = replace(
        report,
        report_id="",
        evaluations=(unrelated_evaluation, *report.evaluations[1:]),
        outcome_counts=(),
        content_hash="",
    ).finalized()
    assert isinstance(unrelated_report, RepositoryVerificationReport)
    with pytest.raises(ValueError, match="unknown file identity"):
        builder.build(registry, policies, unrelated_report)

    (tmp_path / "AI-Gateway/app/service.py").unlink()
    with pytest.raises(FileNotFoundError):
        builder.build(registry, policies, report)


def test_ambiguous_capability_hierarchy_fails_closed(tmp_path: Path) -> None:
    _write(tmp_path, "AI-Gateway/app/a.py")
    _write(tmp_path, "AI-Gateway/app/b.py")
    ownership = (
        RepositoryOwnershipPolicy(
            "owner.a", "1.0", ("AI-Gateway/app/a.py",), "A",
            "Architecture", "Engine A", "Shared Capability", "A ownership.",
        ),
        RepositoryOwnershipPolicy(
            "owner.b", "1.0", ("AI-Gateway/app/b.py",), "B",
            "Architecture", "Engine B", "Shared Capability", "B ownership.",
        ),
    )
    bundle = _bundle(ownership)
    registry, policies, report = _inputs(
        tmp_path, bundle=bundle,
        paths=("AI-Gateway/app/a.py", "AI-Gateway/app/b.py"),
    )

    with pytest.raises(ValueError, match="ambiguous engine"):
        RepositoryTraceabilityGraphBuilder(
            tmp_path / "AI-Gateway", "AI-Gateway",
        ).build(registry, policies, report)


def test_traceability_has_no_runtime_scientific_storage_or_compliance_import() -> None:
    source = (
        Path(__file__).parents[1]
        / "repository"
        / "traceability_graph_builder.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        "app.runtime", "app.knowledge", "app.discovery",
        "psycopg", "boto3", "ComplianceEngine", "ArchitectureViolation",
    )
    assert not any(item in source for item in forbidden)
