"""Deterministic theory synthesis and human review workflow."""

from dataclasses import replace
from hashlib import sha256
import re
import unicodedata

from app.knowledge.modeling.models import KnowledgeEdgeType, KnowledgeNodeType, ScientificKnowledgeGraph
from app.knowledge.theory.models import (
    CompetingTheory, EvidenceStance, TheoryAlignmentEvent, TheoryBundle, TheoryEvidence,
    TheoryProposal, TheoryReviewEvent, TheoryReviewState,
)


class TheoryBuilder:
    def build(self, graphs: tuple[ScientificKnowledgeGraph, ...], *, created_at: str) -> TheoryBundle:
        if not graphs or any(not graph.verify() for graph in graphs):
            raise ValueError("Theory construction requires verified knowledge graphs")
        claims: dict[str, list[tuple[str, tuple[TheoryEvidence, ...]]]] = {}
        for graph in graphs:
            for node in graph.nodes:
                if node.node_type is not KnowledgeNodeType.CONCLUSION:
                    continue
                evidence = []
                for edge in graph.edges:
                    if edge.target_id == node.node_id and edge.edge_type is KnowledgeEdgeType.SUPPORTS:
                        evidence.append(TheoryEvidence(edge.edge_id, graph.graph_id, edge.provenance.object_id, EvidenceStance.SUPPORTS, edge.provenance.confidence, edge.provenance.quote_hash))
                key = self._claim_key(node.label)
                if key:
                    claims.setdefault(key, []).append((node.label.strip(), tuple(evidence)))
        proposals = []
        for key, occurrences in sorted(claims.items()):
            statement = min((item[0] for item in occurrences), key=self._statement_rank)
            evidence = tuple(sorted(
                (entry for _, entries in occurrences for entry in entries),
                key=lambda item: (item.graph_id, item.edge_id),
            ))
            proposals.append(TheoryProposal(
                f"theory-{sha256(key.encode()).hexdigest()[:24]}", statement,
                evidence, sum(item.stance is EvidenceStance.SUPPORTS for item in evidence),
                sum(item.stance is EvidenceStance.CONTRADICTS for item in evidence),
            ))
        competing = []
        for index, left in enumerate(proposals):
            for right in proposals[index + 1:]:
                if self._compete(left.statement, right.statement):
                    competing.append(CompetingTheory(left.theory_id, right.theory_id, "Shared subject with opposing polarity"))
        graph_ids = tuple(sorted(graph.graph_id for graph in graphs))
        identity = f"{':'.join(graph_ids)}:{created_at}:1.1"
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

    def align(
        self, bundle: TheoryBundle, *, theory_ids: tuple[str, ...], statement: str,
        reviewer: str, rationale: str, occurred_at: str,
    ) -> TheoryBundle:
        if not bundle.verify():
            raise ValueError("Theory alignment requires a verified bundle")
        source_ids = tuple(sorted(set(theory_ids)))
        if len(source_ids) < 2:
            raise ValueError("Theory alignment requires at least two distinct theories")
        if not statement.strip() or not rationale.strip():
            raise ValueError("Alignment statement and rationale are required")
        by_id = {proposal.theory_id: proposal for proposal in bundle.proposals}
        missing = [theory_id for theory_id in source_ids if theory_id not in by_id]
        if missing:
            raise KeyError(f"Unknown theory proposal: {missing[0]}")
        sources = tuple(by_id[theory_id] for theory_id in source_ids)
        if any(item.review_state is not TheoryReviewState.ACCEPTED for item in sources):
            raise ValueError("All aligned theories must be accepted first")
        evidence = tuple(sorted(
            {item.edge_id: item for proposal in sources for item in proposal.evidence}.values(),
            key=lambda item: (item.graph_id, item.edge_id),
        ))
        if len({item.graph_id for item in evidence}) < 2:
            raise ValueError("Theory alignment requires evidence from at least two graphs")
        identity = f"semantic:{':'.join(source_ids)}:{self._claim_key(statement)}"
        resulting_id = f"theory-{sha256(identity.encode()).hexdigest()[:24]}"
        merged = TheoryProposal(
            resulting_id, statement.strip(), evidence,
            sum(item.stance is EvidenceStance.SUPPORTS for item in evidence),
            sum(item.stance is EvidenceStance.CONTRADICTS for item in evidence),
            TheoryReviewState.ACCEPTED,
        )
        proposals = tuple(sorted(
            tuple(item for item in bundle.proposals if item.theory_id not in source_ids) + (merged,),
            key=lambda item: item.theory_id,
        ))
        competing = self._competing(proposals)
        alignment_id = f"alignment-{sha256(f'{identity}:{reviewer}:{occurred_at}'.encode()).hexdigest()[:24]}"
        event = TheoryAlignmentEvent(
            alignment_id, source_ids, resulting_id, statement.strip(), reviewer,
            rationale.strip(), occurred_at,
        )
        return replace(
            bundle, proposals=proposals, competing=competing,
            alignments=bundle.alignments + (event,), content_hash="",
        ).finalized()

    @staticmethod
    def _claim_key(statement: str) -> str:
        normalized = unicodedata.normalize("NFKC", statement).casefold()
        return " ".join(re.findall(r"[^\W_]+", normalized, flags=re.UNICODE))

    @staticmethod
    def _statement_rank(statement: str) -> tuple:
        return (
            not statement[:1].isupper(),
            sum(character.isupper() for character in statement[1:]),
            not statement.endswith((".", "?", "!")),
            statement.casefold(), statement,
        )

    @staticmethod
    def _compete(left: str, right: str) -> bool:
        negations = {"not", "no", "without", "fails", "doesn't", "cannot"}
        left_tokens = set(re.findall(r"[a-z]+", left.lower()))
        right_tokens = set(re.findall(r"[a-z]+", right.lower()))
        shared = (left_tokens - negations) & (right_tokens - negations)
        polarity_differs = bool(left_tokens & negations) != bool(right_tokens & negations)
        return polarity_differs and len(shared) >= 2

    @classmethod
    def _competing(cls, proposals: tuple[TheoryProposal, ...]) -> tuple[CompetingTheory, ...]:
        return tuple(
            CompetingTheory(left.theory_id, right.theory_id, "Shared subject with opposing polarity")
            for index, left in enumerate(proposals)
            for right in proposals[index + 1:]
            if cls._compete(left.statement, right.statement)
        )
