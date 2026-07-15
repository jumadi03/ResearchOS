"""Build a canonical Architecture Graph from Python project source."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from .class_extractor import ClassExtractor
from .models import ArchitectureEdge, ArchitectureGraph, ArchitectureNode
from .node_collector import NodeCollector
from .parser import ArchitectureParser
from .scanner import ArchitectureScanner


@dataclass(frozen=True, slots=True)
class ArchitectureGraphBuilder:
    """Orchestrate deterministic source discovery and graph construction."""

    root: Path
    project_name: str
    source_revision: str | None = None

    @staticmethod
    def _module_node_id(module: str) -> str:
        return f"module:{module}"

    @staticmethod
    def _imported_modules(nodes: tuple[ast.AST, ...]) -> tuple[tuple[str, int], ...]:
        imports: list[tuple[str, int]] = []
        for node in nodes:
            if isinstance(node, ast.Import):
                imports.extend((alias.name, node.lineno) for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append((node.module, node.lineno))
        return tuple(imports)

    def build(self) -> ArchitectureGraph:
        """Scan the configured root and return a finalized graph snapshot."""
        scanner = ArchitectureScanner(self.root)
        parser = ArchitectureParser()
        collector = NodeCollector()
        class_extractor = ClassExtractor()
        artifacts = scanner.scan()

        project_id = f"project:{self.project_name}"
        nodes: dict[str, ArchitectureNode] = {
            project_id: ArchitectureNode(
                node_id=project_id,
                node_type="Project",
                canonical_name=self.project_name,
            )
        }
        edges: dict[str, ArchitectureEdge] = {}

        for artifact in artifacts:
            module_id = self._module_node_id(artifact.module)
            nodes[module_id] = ArchitectureNode(
                node_id=module_id,
                node_type="Module",
                canonical_name=artifact.module,
                source_path=artifact.metadata.get("path"),
                metadata={"external": False},
            )
            contains_id = f"contains:{project_id}:{module_id}"
            edges[contains_id] = ArchitectureEdge(
                edge_id=contains_id,
                source_id=project_id,
                target_id=module_id,
                relation_type="CONTAINS",
            )

            module_ast = parser.parse(artifact)
            ast_nodes = collector.collect(module_ast)

            for symbol in class_extractor.extract(ast_nodes):
                class_id = f"class:{artifact.module}:{symbol.name}"
                nodes[class_id] = ArchitectureNode(
                    node_id=class_id,
                    node_type="Class",
                    canonical_name=f"{artifact.module}.{symbol.name}",
                    source_path=artifact.metadata.get("path"),
                    source_line=symbol.line,
                )
                edge_id = f"defines:{module_id}:{class_id}"
                edges[edge_id] = ArchitectureEdge(
                    edge_id=edge_id,
                    source_id=module_id,
                    target_id=class_id,
                    relation_type="DEFINES",
                )

            for imported_module, line in self._imported_modules(ast_nodes):
                imported_id = self._module_node_id(imported_module)
                nodes.setdefault(
                    imported_id,
                    ArchitectureNode(
                        node_id=imported_id,
                        node_type="Module",
                        canonical_name=imported_module,
                        metadata={"external": True},
                    ),
                )
                edge_id = f"imports:{module_id}:{imported_id}"
                existing = edges.get(edge_id)
                lines = sorted({line, *(existing.metadata.get("lines", []) if existing else [])})
                edges[edge_id] = ArchitectureEdge(
                    edge_id=edge_id,
                    source_id=module_id,
                    target_id=imported_id,
                    relation_type="IMPORTS",
                    metadata={"lines": lines},
                )

        graph = ArchitectureGraph(
            graph_id="",
            project_name=self.project_name,
            source_revision=self.source_revision,
            nodes=tuple(sorted(nodes.values(), key=lambda item: item.node_id)),
            edges=tuple(sorted(edges.values(), key=lambda item: item.edge_id)),
        )
        return graph.finalized()
