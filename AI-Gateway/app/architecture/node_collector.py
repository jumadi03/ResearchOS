"""
ResearchOS AST Node Collector.

Foundation implementation.
"""

import ast
from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class NodeCollector:
    """
    Foundation Node Collector.

    Collects AST nodes.

    Does not perform any semantic
    interpretation.
    """

    def collect(
        self,
        module: ast.Module,
    ) -> tuple[
        ast.AST,
        ...,
    ]:
        """
        Collect every node
        inside one AST.
        """

        return tuple(
            ast.walk(module)
        )