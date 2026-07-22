"""Build a deterministic graph whose relationships remain assertions."""

from hashlib import sha256

from app.knowledge.extraction.models import ExtractionManifest, ScientificObjectType
from app.knowledge.modeling.admission import EvidenceAdmissionGate
from app.knowledge.modeling.models import (
    GraphProvenance, KnowledgeEdge, KnowledgeEdgeType, KnowledgeNode,
    KnowledgeNodeType, KnowledgeRelationAssertion, ScientificKnowledgeGraph,
)


class ScientificKnowledgeGraphBuilder:
    def __init__(self, admission_gate: EvidenceAdmissionGate | None = None) -> None:
        self.admission_gate = admission_gate or EvidenceAdmissionGate()

    def build(
        self, manifest: ExtractionManifest, admissions=None,
        evidence_object_ids: tuple[str, ...] | None = None,
        relations: tuple[KnowledgeRelationAssertion, ...] = (),
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
        provenance_by_object = {}
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
            provenance_by_object[item.object_id] = provenance
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
        for relation in relations:
            referenced = {
                relation.source_object_id,
                relation.target_object_id,
                relation.provenance_object_id,
            }
            missing = sorted(referenced - selected_ids)
            if missing:
                raise ValueError(
                    "Explicit relation requires accepted graph evidence: "
                    f"{missing[0]}"
                )
            if relation.source_object_id == relation.target_object_id:
                raise ValueError("Explicit relation cannot be self-referential")
            provenance = provenance_by_object[relation.provenance_object_id]
            edges.append(self._edge(
                f"node:{relation.source_object_id}",
                f"node:{relation.target_object_id}",
                relation.edge_type,
                provenance,
            ))
        selection = ",".join(sorted(selected_ids))
        relation_identity = ",".join(sorted(
            f"{item.source_object_id}:{item.edge_type.value}:"
            f"{item.target_object_id}:{item.provenance_object_id}"
            for item in relations
        ))
        graph_identity = (
            (
                f"{manifest.extraction_id}:{manifest.document_content_hash}:"
                f"{selection}:{relation_identity}:1.1"
            )
            if relations else
            (
                f"{manifest.extraction_id}:{manifest.document_content_hash}:"
                f"{selection}:1.0"
            )
        )
        edges_by_id = {edge.edge_id: edge for edge in edges}
        graph = ScientificKnowledgeGraph(
            f"graph-{sha256(graph_identity.encode()).hexdigest()[:24]}",
            manifest.extraction_id,
            tuple(sorted(nodes, key=lambda node: node.node_id)),
            tuple(sorted(edges_by_id.values(), key=lambda edge: edge.edge_id)),
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
