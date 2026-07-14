"""
Smoke Test + Contract Test
for Symbol Extractor.
"""

from pathlib import Path

from app.architecture import (
    ArchitectureParser,
    ArchitectureScanner,
    SymbolExtractor,
)


def test_contract() -> None:

    #
    # Arrange
    #
    scanner = ArchitectureScanner(
        root=Path("."),
    )

    parser = ArchitectureParser()

    extractor = SymbolExtractor()

    artifacts = scanner.scan()

    module = parser.parse(
        artifacts[0],
    )

    #
    # Act
    #
    symbols = extractor.extract(
        module,
    )

    #
    # Smoke Test
    #
    print(
        "Extractor :",
        extractor,
    )

    print(
        "Symbols   :",
        symbols,
    )

    #
    # Contract Test
    #
    assert isinstance(
        symbols,
        tuple,
    )

    print()

    print(
        "CONTRACT TEST : PASS",
    )

    print(
        "PASS",
    )


