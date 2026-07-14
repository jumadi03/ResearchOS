"""
ResearchOS Import Extractor.

Semantic extractor for Python import
statements.

Sprint-002A
"""

from __future__ import annotations

import ast
from dataclasses import dataclass

from .models import (
    ArchitectureSymbol,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ImportExtractor:
    """
    Import Extractor.

    Extracts import symbols from a
    collected AST node sequence.

    This extractor performs semantic
    interpretation only.

    It does not:

    - parse source code
    - traverse AST
    - collect nodes
    """

    def extract(
        self,
        nodes: tuple[
            ast.AST,
            ...,
        ],
    ) -> tuple[
        ArchitectureSymbol,
        ...,
    ]:
        """
        Extract import symbols.
        """

        symbols: list[
            ArchitectureSymbol
        ] = []

        for node in nodes:

            if not isinstance(
                node,
                ast.Import,
            ):
                continue

            for alias in node.names:

                symbols.append(
                    ArchitectureSymbol(
                        name=alias.name,
                        symbol_type="import",
                        line=node.lineno,
                    )
                )

        return tuple(
            symbols
        )