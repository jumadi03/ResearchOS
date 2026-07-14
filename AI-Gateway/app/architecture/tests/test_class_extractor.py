"""
Smoke Test + Contract Test
for Class Extractor.

Sprint-002B
"""

import ast

from app.architecture import (
    ClassExtractor,
    NodeCollector,
)


SOURCE = """
class User:
    pass


class Product:
    pass


print("hello")
"""


def main() -> None:

    #
    # Arrange
    #
    collector = NodeCollector()

    extractor = ClassExtractor()

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

    assert symbols[0].name == "User"

    assert symbols[1].name == "Product"

    print()

    print(
        "CONTRACT TEST : PASS",
    )

    print(
        "PASS",
    )


if __name__ == "__main__":
    main()