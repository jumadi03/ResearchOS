from pathlib import Path

from app.architecture import ArchitectureGraphBuilder


def _write_project(root: Path) -> None:
    package = root / "sample"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "models.py").write_text(
        "from dataclasses import dataclass\n\n@dataclass\nclass Item:\n    name: str\n",
        encoding="utf-8",
    )
    (package / "service.py").write_text(
        "import json\nfrom sample.models import Item\n\nclass Service:\n    pass\n",
        encoding="utf-8",
    )


def test_builder_creates_modules_classes_and_import_edges(tmp_path: Path) -> None:
    _write_project(tmp_path)
    graph = ArchitectureGraphBuilder(
        root=tmp_path,
        project_name="sample-project",
        source_revision="test-revision",
    ).build()

    nodes = {node.node_id: node for node in graph.nodes}
    edges = {edge.edge_id: edge for edge in graph.edges}

    assert "project:sample-project" in nodes
    assert "module:sample.models" in nodes
    assert "module:sample.service" in nodes
    assert "class:sample.models:Item" in nodes
    assert "class:sample.service:Service" in nodes
    assert "imports:module:sample.service:module:json" in edges
    assert "imports:module:sample.service:module:sample.models" in edges
    assert nodes["module:sample.models"].metadata["external"] is False
    assert nodes["module:json"].metadata["external"] is True
    assert nodes["module:sample.models"].source_path == "sample/models.py"
    assert graph.content_hash
    assert graph.graph_id.startswith("graph:sample-project:")


def test_builder_output_is_stable_for_same_source(tmp_path: Path) -> None:
    _write_project(tmp_path)
    builder = ArchitectureGraphBuilder(tmp_path, "sample-project", "revision")
    assert builder.build().to_json() == builder.build().to_json()
