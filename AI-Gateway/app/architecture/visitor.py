"""
ResearchOS Architecture Visitor.

Foundation AST visitor for
Architecture Engine.
"""

import ast
from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class ArchitectureVisitor(
    ast.NodeVisitor,
):
    """
    Foundation Architecture Visitor.

    Provides the canonical AST
    traversal mechanism.
    """

    def walk(
        self,
        module: ast.Module,
    ) -> None:
        """
        Visit one AST module.
        """

        self.visit(module)