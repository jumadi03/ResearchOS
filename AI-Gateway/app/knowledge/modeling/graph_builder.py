"""Build a deterministic graph whose relationships remain assertions."""

from hashlib import sha256

from app.knowledge.extraction.models import ExtractionManifest, ScientificObjectType
from app.knowledge.modeling.admission import EvidenceAdmissionGate
from app.knowledge.modeling.models import (
    GraphProvenance, KnowledgeEdge, KnowledgeEdgeType, KnowledgeNode,
    KnowledgeNodeType, ScientificKnowledgeGraph,
)


class ScientificKnowledgeGraphBuilder:
    def __init__(self, admission_gate: EvidenceAdmissionGate | None = None) -> None:
        self.admission_gate = admission_gate or EvidenceAdmissionGate()

    def build(
        self, manifest: ExtractionManifest, admissions=None,
        evidence_object_ids: tuple[str, ...] | None = None,
    ) -> ScientificKnowledgeGraph:
        accepted = self.admission_gate.admit(
            manifest, admissions, evidence_object_ids,
        )
        selected_ids = set(accepted)
        document_node = KnowledgeNode(
            f"node:{manifest.document_id}", KnowledgeNodeType.SOURCE_DOCUMENT,
            manifest.document_id,
        )
        nodes = [document_node]
        edges = []
        methods = []
        results = []
        conclusions = []
        for item in manifest.objects:
            if item.object_id not in selected_ids:
                continue
            provenance = GraphProvenance(
                manifest.extraction_id, manifest.document_id, item.object_id,
                item.coordinates.page, item.coordinates.quote_hash,
                item.confidence, accepted[item.object_id].decision,
                accepted[item.object_id],
            )
            node = KnowledgeNode(
                f"node:{item.object_id}", KnowledgeNodeType(item.object_type.value),
                item.content, provenance,
            )
            nodes.append(node)
            edges.append(self._edge(document_node.node_id, node.node_id, KnowledgeEdgeType.CONTAINS, provenance))
            if item.object_type is ScientificObjectType.METHOD:
                methods.append((node, provenance))
            elif item.object_type is ScientificObjectType.RESULT:
                results.append((node, provenance))
            elif item.object_type is ScientificObjectType.CONCLUSION:
                conclusions.append((node, provenance))
        for result, provenance in results:
            for method, _ in methods:
                edges.append(self._edge(result.node_id, method.node_id, KnowledgeEdgeType.USES_METHOD, provenance))
        for conclusion, provenance in conclusions:
            for result, _ in results:
                edges.append(self._edge(result.node_id, conclusion.node_id, KnowledgeEdgeType.SUPPORTS, provenance))
        selection = ",".join(sorted(selected_ids))
        graph_identity = (
            f"{manifest.extraction_id}:{manifest.document_content_hash}:"
            f"{selection}:1.0"
        )
        graph = ScientificKnowledgeGraph(
            f"graph-{sha256(graph_identity.encode()).hexdigest()[:24]}",
            manifest.extraction_id,
            tuple(sorted(nodes, key=lambda node: node.node_id)),
            tuple(sorted(edges, key=lambda edge: edge.edge_id)),
        )
        graph.validate_evidence_admission()
        return graph.finalized()

    @staticmethod
    def _edge(source: str, target: str, kind: KnowledgeEdgeType, provenance: GraphProvenance) -> KnowledgeEdge:
        identity = f"{source}:{kind.value}:{target}:{provenance.object_id}"
        return KnowledgeEdge(
            f"edge-{sha256(identity.encode()).hexdigest()[:24]}", source, target,
            kind, True, provenance,
        )
