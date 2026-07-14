"""
Smoke Test + Contract Test
for Import Extractor.

Sprint-002A
"""

import ast

from app.architecture import (
    ImportExtractor,
    NodeCollector,
)


SOURCE = """
import os
import sys

print("hello")
"""


def test_contract() -> None:

    #
    # Arrange
    #
    collector = NodeCollector()

    extractor = ImportExtractor()

    module = ast.parse(
        SOURCE,
    )

    nodes = collector.collect(
        module,
    )

    #
    # Act
    #
    symbols = extractor.extract(
        nodes,
    )

    #
    # Smoke Test
    #
    print(
        "Extractor :",
        extractor,
    )

    print(
        "Symbol Count :",
        len(symbols),
    )

    print()

    for symbol in symbols:

        print(
            symbol,
        )

    #
    # Contract Test
    #
    assert isinstance(
        symbols,
        tuple,
    )

    assert len(
        symbols,
    ) == 2

    print()

    print(
        "CONTRACT TEST : PASS",
    )

    print(
        "PASS",
    )


