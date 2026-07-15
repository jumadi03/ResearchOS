"""Deterministic theory synthesis and human review workflow."""

from dataclasses import replace
from hashlib import sha256
import re

from app.knowledge.modeling.models import KnowledgeEdgeType, KnowledgeNodeType, ScientificKnowledgeGraph
from app.knowledge.theory.models import (
    CompetingTheory, EvidenceStance, TheoryBundle, TheoryEvidence,
    TheoryProposal, TheoryReviewEvent, TheoryReviewState,
)


class TheoryBuilder:
    def build(self, graphs: tuple[ScientificKnowledgeGraph, ...], *, created_at: str) -> TheoryBundle:
        if not graphs or any(not graph.verify() for graph in graphs):
            raise ValueError("Theory construction requires verified knowledge graphs")
        proposals = []
        for graph in graphs:
            by_id = {node.node_id: node for node in graph.nodes}
            for node in graph.nodes:
                if node.node_type is not KnowledgeNodeType.CONCLUSION:
                    continue
                evidence = []
                for edge in graph.edges:
                    if edge.target_id == node.node_id and edge.edge_type is KnowledgeEdgeType.SUPPORTS:
                        evidence.append(TheoryEvidence(edge.edge_id, graph.graph_id, edge.provenance.object_id, EvidenceStance.SUPPORTS, edge.provenance.confidence, edge.provenance.quote_hash))
                identity = f"{node.label}:{graph.graph_id}"
                proposals.append(TheoryProposal(
                    f"theory-{sha256(identity.encode()).hexdigest()[:24]}", node.label,
                    tuple(evidence), len(evidence), 0,
                ))
        competing = []
        for index, left in enumerate(proposals):
            for right in proposals[index + 1:]:
                if self._compete(left.statement, right.statement):
                    competing.append(CompetingTheory(left.theory_id, right.theory_id, "Shared subject with opposing polarity"))
        graph_ids = tuple(sorted(graph.graph_id for graph in graphs))
        identity = f"{':'.join(graph_ids)}:{created_at}:1.0"
        return TheoryBundle(
            f"theory-bundle-{sha256(identity.encode()).hexdigest()[:24]}", graph_ids,
            created_at, tuple(sorted(proposals, key=lambda item: item.theory_id)),
            tuple(competing),
        ).finalized()

    def review(self, bundle: TheoryBundle, *, theory_id: str, decision: TheoryReviewState, reviewer: str, rationale: str, occurred_at: str) -> TheoryBundle:
        if decision is TheoryReviewState.PROPOSED:
            raise ValueError("Review decision must be accepted or rejected")
        if not rationale.strip():
            raise ValueError("Review rationale is required")
        if not any(item.theory_id == theory_id for item in bundle.proposals):
            raise KeyError(f"Unknown theory proposal: {theory_id}")
        proposals = tuple(replace(item, review_state=decision) if item.theory_id == theory_id else item for item in bundle.proposals)
        event = TheoryReviewEvent(theory_id, decision, reviewer, rationale.strip(), occurred_at)
        return replace(bundle, proposals=proposals, reviews=bundle.reviews + (event,), content_hash="").finalized()

    @staticmethod
    def _compete(left: str, right: str) -> bool:
        negations = {"not", "no", "without", "fails", "doesn't", "cannot"}
        left_tokens = set(re.findall(r"[a-z]+", left.lower()))
        right_tokens = set(re.findall(r"[a-z]+", right.lower()))
        shared = (left_tokens - negations) & (right_tokens - negations)
        polarity_differs = bool(left_tokens & negations) != bool(right_tokens & negations)
        return polarity_differs and len(shared) >= 2
