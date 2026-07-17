"""Versioned provenance-aware Scientific Knowledge Graph contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from hashlib import sha256
import json

from app.knowledge.extraction.models import (
    EvidenceReviewEvent, ExtractionReviewState,
)


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
    review_state: ExtractionReviewState | None
    review_event: EvidenceReviewEvent | None


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

    def validate_evidence_admission(self) -> None:
        evidence_nodes = [
            node for node in self.nodes
            if node.node_type is not KnowledgeNodeType.SOURCE_DOCUMENT
        ]
        if not evidence_nodes:
            raise ValueError("Canonical knowledge graph requires accepted evidence")
        for node in evidence_nodes:
            if node.provenance is None:
                raise ValueError(
                    f"Evidence review status is missing: {node.node_id}"
                )
            self._validate_provenance(node.provenance)
        for edge in self.edges:
            self._validate_provenance(edge.provenance)

    @staticmethod
    def _validate_provenance(provenance: GraphProvenance) -> None:
        object_id = provenance.object_id
        if provenance.review_state is None:
            raise ValueError(f"Evidence review status is missing: {object_id}")
        if provenance.review_state is ExtractionReviewState.REJECTED:
            raise ValueError(
                f"Knowledge graph contains rejected evidence: {object_id}"
            )
        if provenance.review_state is not ExtractionReviewState.ACCEPTED:
            raise ValueError(
                f"Evidence is not accepted: {object_id} "
                f"(status={provenance.review_state.value})"
            )
        event = provenance.review_event
        if (
            event is None
            or event.evidence_object_id != object_id
            or event.decision is not ExtractionReviewState.ACCEPTED
            or not event.review_id.strip()
            or not event.reviewer.strip()
            or not event.rationale.strip()
            or not event.occurred_at.strip()
            or not event.provenance_id.strip()
            or not event.previous_state.strip()
            or event.assessment is None
            or not event.assessment.permits_acceptance()
            or event.assessment_hash != event.assessment.digest()
        ):
            raise ValueError(
                f"Evidence review provenance is incomplete: {object_id}"
            )
