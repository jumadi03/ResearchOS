"""Immutable Scientific Knowledge Graph snapshots."""

from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from app.architecture.persistence import atomic_write
from app.knowledge.extraction.models import (
    EpistemicClassification, EvidenceReviewAssessment, EvidenceReviewEvent,
    ExtractionReviewState,
)
from app.knowledge.modeling.models import (
    GraphProvenance, KnowledgeEdge, KnowledgeEdgeType, KnowledgeNode,
    KnowledgeNodeType, ScientificKnowledgeGraph,
)


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

    def load_all(self) -> tuple[ScientificKnowledgeGraph, ...]:
        if not self.root.exists():
            return ()
        graphs = []
        for directory in sorted(p for p in self.root.iterdir() if p.is_dir()):
            snapshots = tuple(directory.glob("v*.json"))
            if not snapshots:
                continue
            path = max(snapshots, key=lambda item: item.stat().st_mtime_ns)
            raw = json.loads(path.read_text(encoding="utf-8"))
            stored_hash = raw.get("content_hash", "")
            hash_payload = dict(raw)
            hash_payload["content_hash"] = ""
            calculated_hash = sha256(json.dumps(
                hash_payload, ensure_ascii=False, sort_keys=True,
                separators=(",", ":"),
            ).encode()).hexdigest()
            if not stored_hash or calculated_hash != stored_hash:
                raise ValueError(
                    f"Scientific graph snapshot integrity failed: {path.name}"
                )

            # Graphs created before review provenance became mandatory can be
            # hash-valid while still carrying provisional or incomplete
            # evidence admission. Exclude them before typed reconstruction;
            # they remain immutable historical snapshots, not current graph
            # authority.
            evidence_provenance = [
                item.get("provenance")
                for item in raw["nodes"]
                if item["node_type"] != KnowledgeNodeType.SOURCE_DOCUMENT.value
            ]
            edge_provenance = [
                item.get("provenance") for item in raw["edges"]
            ]
            admissions = evidence_provenance + edge_provenance
            if any(
                value is None
                or value.get("review_state") != ExtractionReviewState.ACCEPTED.value
                or value.get("review_event") is None
                for value in admissions
            ):
                continue

            def decode_provenance(value):
                if value is None:
                    return None
                event_raw = value.get("review_event")
                event = None
                if event_raw is not None:
                    assessment_raw = event_raw.get("assessment")
                    assessment = None
                    if assessment_raw is not None:
                        assessment = EvidenceReviewAssessment(
                            assessment_raw["citation_fidelity"],
                            assessment_raw["context_preserved"],
                            assessment_raw["relevant"],
                            assessment_raw["confidence_assessment"],
                            EpistemicClassification(
                                assessment_raw["epistemic_classification"]
                            ),
                            assessment_raw["reviewed_statement_hash"],
                            assessment_raw["extraction_manifest_hash"],
                        )
                    event = EvidenceReviewEvent(
                        event_raw["review_id"],
                        event_raw["evidence_object_id"],
                        ExtractionReviewState(event_raw["decision"]),
                        event_raw["reviewer"], event_raw["rationale"],
                        event_raw["occurred_at"], event_raw["provenance_id"],
                        event_raw["previous_state"], assessment,
                        event_raw.get("assessment_hash", ""),
                    )
                return GraphProvenance(
                    value["extraction_id"], value["document_id"],
                    value["object_id"], value["page"], value["quote_hash"],
                    value["confidence"],
                    (
                        ExtractionReviewState(value["review_state"])
                        if value.get("review_state") is not None else None
                    ),
                    event,
                )

            graph = ScientificKnowledgeGraph(
                raw["graph_id"], raw["extraction_id"],
                tuple(KnowledgeNode(
                    item["node_id"], KnowledgeNodeType(item["node_type"]),
                    item["label"], decode_provenance(item.get("provenance")),
                ) for item in raw["nodes"]),
                tuple(KnowledgeEdge(
                    item["edge_id"], item["source_id"], item["target_id"],
                    KnowledgeEdgeType(item["edge_type"]), item["assertion"],
                    decode_provenance(item["provenance"]),
                ) for item in raw["edges"]),
                raw["content_hash"], raw.get("schema_version", "1.0"),
            )
            if not graph.verify():
                raise ValueError(
                    f"Scientific graph snapshot integrity failed: {path.name}"
                )
            try:
                graph.validate_evidence_admission()
            except ValueError:
                # Historical pre-admission graph snapshots can contain
                # provisional embedded review state. They are not current
                # graph authority and must not prevent recovery of later,
                # admissible graphs. Hash corruption still fails above.
                continue
            graphs.append(graph)
        return tuple(graphs)
