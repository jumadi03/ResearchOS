"""Versioned provenance-aware Scientific Knowledge Graph contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from hashlib import sha256
import json

from app.knowledge.extraction.models import ExtractionReviewState


class KnowledgeNodeType(StrEnum):
    SOURCE_DOCUMENT = "source_document"
    CLAIM = "claim"
    METHOD = "method"
    VARIABLE = "variable"
    DATASET = "dataset"
    RESULT = "result"
    LIMITATION = "limitation"
    CONCLUSION = "conclusion"


class KnowledgeEdgeType(StrEnum):
    CONTAINS = "contains"
    USES_METHOD = "uses_method"
    SUPPORTS = "supports"


@dataclass(frozen=True, slots=True)
class GraphProvenance:
    extraction_id: str
    document_id: str
    object_id: str
    page: int
    quote_hash: str
    confidence: float
    review_state: ExtractionReviewState


@dataclass(frozen=True, slots=True)
class KnowledgeNode:
    node_id: str
    node_type: KnowledgeNodeType
    label: str
    provenance: GraphProvenance | None = None


@dataclass(frozen=True, slots=True)
class KnowledgeEdge:
    edge_id: str
    source_id: str
    target_id: str
    edge_type: KnowledgeEdgeType
    assertion: bool
    provenance: GraphProvenance


@dataclass(frozen=True, slots=True)
class ScientificKnowledgeGraph:
    graph_id: str
    extraction_id: str
    nodes: tuple[KnowledgeNode, ...]
    edges: tuple[KnowledgeEdge, ...]
    content_hash: str = ""
    schema_version: str = "1.0"

    def finalized(self) -> "ScientificKnowledgeGraph":
        payload = asdict(replace(self, content_hash=""))
        digest = sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return replace(self, content_hash=digest)

    def verify(self) -> bool:
        return bool(self.content_hash) and self.finalized().content_hash == self.content_hash
