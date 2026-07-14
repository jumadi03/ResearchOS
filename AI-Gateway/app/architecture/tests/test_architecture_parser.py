"""
Smoke Test + Contract Test
for Architecture Parser.
"""

import ast
from pathlib import Path

from app.architecture import (
    ArchitectureParser,
    ArchitectureScanner,
)


def test_contract() -> None:
    #
    # Arrange
    #
    scanner = ArchitectureScanner(
        root=Path("."),
    )

    parser = ArchitectureParser()

    artifacts = scanner.scan()

    #
    # Act
    #
    first = artifacts[0]

    module = parser.parse(
        first,
    )

    #
    # Smoke Test
    #
    print(
        "Parser      :",
        parser,
    )

    print(
        "Artifact    :",
        first.module,
    )

    print(
        "Source Size :",
        len(first.source),
    )

    print(
        "AST         :",
        module,
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


