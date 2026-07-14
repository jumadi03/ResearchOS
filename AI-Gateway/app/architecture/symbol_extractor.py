"""
ResearchOS Symbol Extractor.

Foundation implementation.
"""

import ast
from dataclasses import dataclass

from .models import (
    ArchitectureSymbol,
)


@dataclass(
    frozen=True,
    slots=True,
)
class SymbolExtractor:
    """
    Foundation Symbol Extractor.

    Produces ArchitectureSymbol
    objects from AST.
    """

    def extract(
        self,
        module: ast.Module,
    ) -> tuple[
        ArchitectureSymbol,
        ...,
    ]:
        """
        Foundation implementation.

        No extraction yet.
        """

        return ()