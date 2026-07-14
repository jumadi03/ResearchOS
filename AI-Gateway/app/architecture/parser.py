"""
ResearchOS Architecture Parser.

Parses ArchitectureArtifact objects
into Python AST.
"""

import ast
from dataclasses import dataclass

from .models import (
    ArchitectureArtifact,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ArchitectureParser:
    """
    Foundation Architecture Parser.

    Converts ArchitectureArtifact
    source code into Python AST.
    """

    def parse(
        self,
        artifact: ArchitectureArtifact,
    ) -> ast.Module:
        """
        Parse one ArchitectureArtifact.

        Foundation implementation.
        """

        return ast.parse(
            artifact.source,
        )