"""
Smoke Test + Contract Test
for Architecture Visitor.
"""

import ast
from pathlib import Path

from app.architecture import (
    ArchitectureParser,
    ArchitectureScanner,
    ArchitectureVisitor,
)


def test_contract() -> None:

    #
    # Arrange
    #
    scanner = ArchitectureScanner(
        root=Path("."),
    )

    parser = ArchitectureParser()

    visitor = ArchitectureVisitor()

    artifacts = scanner.scan()

    module = parser.parse(
        artifacts[0],
    )

    #
    # Act
    #
    visitor.walk(module)

    #
    # Smoke Test
    #
    print(
        "Visitor :",
        visitor,
    )

    print(
        "Module  :",
        type(module).__name__,
    )

    #
    # Contract Test
    #
    assert isinstance(
        module,
        ast.Module,
    )

    print()

    print(
        "CONTRACT TEST : PASS",
    )

    print(
        "PASS",
    )


