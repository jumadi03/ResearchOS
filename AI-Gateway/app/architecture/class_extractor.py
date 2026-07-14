"""
ResearchOS Class Extractor.

Semantic extractor for Python class
definitions.

Sprint-002B
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
class ClassExtractor:
    """
    Class Extractor.

    Extracts class symbols from a
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
        Extract class symbols.
        """

        symbols: list[
            ArchitectureSymbol,
        ] = []

        for node in nodes:

            if not isinstance(
                node,
                ast.ClassDef,
            ):
                continue

            symbols.append(
                ArchitectureSymbol(
                    name=node.name,
                    symbol_type="class",
                    line=node.lineno,
                )
            )

        return tuple(
            symbols
        )