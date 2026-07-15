import json

from app.architecture.models import (
    ArchitectureEdge,
    ArchitectureGraph,
    ArchitectureNode,
)


def test_graph_finalization_is_deterministic() -> None:
    node_a = ArchitectureNode("module:a", "Module", "a")
    node_b = ArchitectureNode("module:b", "Module", "b")
    edge = ArchitectureEdge(
        "imports:module:a:module:b",
        "module:a",
        "module:b",
        "IMPORTS",
    )

    first = ArchitectureGraph(
        graph_id="",
        project_name="sample",
        nodes=(node_b, node_a),
        edges=(edge,),
        source_revision="abc123",
    ).finalized()
    second = ArchitectureGraph(
        graph_id="",
        project_name="sample",
        nodes=(node_a, node_b),
        edges=(edge,),
        source_revision="abc123",
    ).finalized()

    assert first.content_hash == second.content_hash
    assert first.graph_id == second.graph_id
    assert first.to_json() == second.to_json()
    assert json.loads(first.to_json())["content_hash"] == first.content_hash


def test_revision_is_part_of_snapshot_identity() -> None:
    first = ArchitectureGraph("", "sample", source_revision="one").finalized()
    second = ArchitectureGraph("", "sample", source_revision="two").finalized()
    assert first.content_hash != second.content_hash
    assert first.graph_id != second.graph_id
