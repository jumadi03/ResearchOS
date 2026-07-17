"""Versioned and deterministically serializable Architecture Graph."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from hashlib import sha256
import json

from .architecture_edge import ArchitectureEdge
from .architecture_node import ArchitectureNode
from ..schema import GRAPH_SCHEMA


@dataclass(frozen=True, slots=True)
class ArchitectureGraph:
    """Immutable snapshot of a project's architectural structure."""

    graph_id: str
    project_name: str
    nodes: tuple[ArchitectureNode, ...] = ()
    edges: tuple[ArchitectureEdge, ...] = ()
    source_revision: str | None = None
    schema_version: str = "1.1"
    content_hash: str = ""

    def canonical_payload(self) -> dict[str, object]:
        """Return the content used for deterministic serialization and hashing."""
        return {
            "schema_version": self.schema_version,
            "project_name": self.project_name,
            "source_revision": self.source_revision,
            "nodes": [
                asdict(node)
                for node in sorted(self.nodes, key=lambda item: item.node_id)
            ],
            "edges": [
                asdict(edge)
                for edge in sorted(self.edges, key=lambda item: item.edge_id)
            ],
        }

    def calculate_content_hash(self) -> str:
        """Calculate a stable SHA-256 hash without self-referential fields."""
        encoded = json.dumps(
            self.canonical_payload(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return sha256(encoded).hexdigest()

    def finalized(self) -> ArchitectureGraph:
        """Return a snapshot carrying its stable hash and graph identifier."""
        content_hash = self.calculate_content_hash()
        return replace(
            self,
            graph_id=f"graph:{self.project_name}:{content_hash[:16]}",
            content_hash=content_hash,
        )

    def verify(self) -> bool:
        """Verify identity, uniqueness, and edge referential integrity."""
        try:
            GRAPH_SCHEMA.require_readable(self.schema_version)
            expected = self.finalized()
        except (TypeError, ValueError):
            return False
        node_ids = [node.node_id for node in self.nodes]
        edge_ids = [edge.edge_id for edge in self.edges]
        known_nodes = set(node_ids)
        return (
            bool(self.project_name.strip())
            and all(
                node.node_id.strip()
                and node.node_type.strip()
                and node.canonical_name.strip()
                for node in self.nodes
            )
            and all(
                edge.edge_id.strip()
                and edge.source_id in known_nodes
                and edge.target_id in known_nodes
                and edge.relation_type.strip()
                for edge in self.edges
            )
            and len(node_ids) == len(known_nodes)
            and len(edge_ids) == len(set(edge_ids))
            and self == expected
        )

    def to_json(self, *, indent: int | None = 2) -> str:
        """Serialize the complete graph deterministically."""
        payload = {
            "graph_id": self.graph_id,
            "content_hash": self.content_hash,
            **self.canonical_payload(),
        }
        return json.dumps(
            payload,
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    @classmethod
    def from_json(cls, value: str) -> "ArchitectureGraph":
        """Load a graph snapshot and reject modified identity or content."""
        payload = json.loads(value)
        GRAPH_SCHEMA.require_readable(payload.get("schema_version", ""))
        graph = cls(
            graph_id=payload.get("graph_id", ""),
            project_name=payload["project_name"],
            nodes=tuple(ArchitectureNode(**item) for item in payload.get("nodes", [])),
            edges=tuple(ArchitectureEdge(**item) for item in payload.get("edges", [])),
            source_revision=payload.get("source_revision"),
            schema_version=payload.get("schema_version", "1.0"),
            content_hash=payload.get("content_hash", ""),
        )
        expected = graph.finalized()
        if (
            graph.content_hash != expected.content_hash
            or graph.graph_id != expected.graph_id
            or not expected.verify()
        ):
            raise ValueError("Architecture Graph identity or content hash is invalid")
        return expected
