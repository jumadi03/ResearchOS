"""Immutable Scientific Knowledge Graph snapshots."""

from dataclasses import asdict
import json
from pathlib import Path

from app.architecture.persistence import atomic_write
from app.knowledge.modeling.models import ScientificKnowledgeGraph


class KnowledgeGraphStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def save(self, graph: ScientificKnowledgeGraph) -> Path:
        graph.validate_evidence_admission()
        if not graph.verify():
            raise ValueError("Scientific Knowledge Graph integrity verification failed")
        payload = json.dumps(asdict(graph), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        path = self.root / graph.graph_id / f"v{graph.schema_version}-{graph.content_hash}.json"
        if not path.exists():
            atomic_write(path, payload)
        elif path.read_bytes() != payload:
            raise RuntimeError("Scientific Knowledge Graph snapshot conflict")
        return path
