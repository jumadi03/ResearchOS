"""
Smoke Test + Contract Test
for AST Node Collector.
"""

import ast
from pathlib import Path

from app.architecture import (
    ArchitectureParser,
    ArchitectureScanner,
    NodeCollector,
)


def test_contract() -> None:

    #
    # Arrange
    #
    scanner = ArchitectureScanner(
        root=Path("."),
    )

    parser = ArchitectureParser()

    collector = NodeCollector()

    artifacts = scanner.scan()

    module = parser.parse(
        artifacts[0],
    )

    #
    # Act
    #
    nodes = collector.collect(
        module,
    )

    #
    # Smoke Test
    #
    print(
        "Collector :",
        collector,
    )

    print(
        "Node Count:",
        len(nodes),
    )

    #
    # Contract Test
    #
    assert isinstance(
        nodes,
        tuple,
    )

    assert all(
        isinstance(
            node,
            ast.AST,
        )
        for node in nodes
    )

    print()

    print(
        "CONTRACT TEST : PASS",
    )

    print(
        "PASS",
    )


