"""Reviewer-governed semantic relation lifecycle contracts."""

from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from hashlib import sha256
import json

from app.knowledge.modeling.models import KnowledgeEdgeType


ADMISSIBLE_SEMANTIC_RELATION_TYPES = frozenset({
    KnowledgeEdgeType.DERIVED_FROM,
    KnowledgeEdgeType.SUPPORTS,
    KnowledgeEdgeType.CONTRADICTS,
    KnowledgeEdgeType.EXTENDS,
    KnowledgeEdgeType.REPLICATES,
    KnowledgeEdgeType.USES_METHOD,
    KnowledgeEdgeType.MEASURES,
    KnowledgeEdgeType.HAS_LIMITATION,
    KnowledgeEdgeType.INTERPRETS,
    KnowledgeEdgeType.INFERS_FROM,
})


class SemanticRelationState(StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class SemanticRelationReviewEvent:
    review_id: str
    decision: SemanticRelationState
    reviewer: str
    rationale: str
    occurred_at: str
    previous_state: SemanticRelationState


@dataclass(frozen=True, slots=True)
class SemanticRelationAdmissionEvent:
    admission_id: str
    graph_id: str
    intake_id: str
    indexer: str
    occurred_at: str


@dataclass(frozen=True, slots=True)
class SemanticRelation:
    relation_id: str
    extraction_id: str
    source_object_id: str
    target_object_id: str
    edge_type: KnowledgeEdgeType
    provenance_object_id: str
    proposed_by: str
    proposal_rationale: str
    proposed_at: str
    state: SemanticRelationState = SemanticRelationState.PROPOSED
    reviews: tuple[SemanticRelationReviewEvent, ...] = ()
    admissions: tuple[SemanticRelationAdmissionEvent, ...] = ()
    content_hash: str = ""
    schema_version: str = "1.0"

    def finalized(self) -> "SemanticRelation":
        payload = asdict(replace(self, content_hash=""))
        digest = sha256(json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ).encode()).hexdigest()
        return replace(self, content_hash=digest)

    def verify(self) -> bool:
        projected = SemanticRelationState.PROPOSED
        review_chain_valid = True
        for event in self.reviews:
            if (
                event.previous_state is not projected
                or event.reviewer == self.proposed_by
            ):
                review_chain_valid = False
            projected = event.decision
        return bool(
            self.schema_version == "1.0"
            and self.relation_id
            and self.extraction_id
            and self.source_object_id
            and self.target_object_id
            and self.source_object_id != self.target_object_id
            and self.provenance_object_id
            and self.edge_type in ADMISSIBLE_SEMANTIC_RELATION_TYPES
            and self.proposed_by.strip()
            and self.proposal_rationale.strip()
            and self.proposed_at.strip()
            and all(
                event.review_id
                and event.reviewer.strip()
                and event.rationale.strip()
                and event.occurred_at.strip()
                and event.decision is not SemanticRelationState.PROPOSED
                for event in self.reviews
            )
            and len({event.admission_id for event in self.admissions})
            == len(self.admissions)
            and all(
                event.admission_id
                and event.graph_id
                and event.intake_id
                and event.indexer.strip()
                and event.occurred_at.strip()
                for event in self.admissions
            )
            and review_chain_valid
            and projected is self.state
            and self.content_hash == self.finalized().content_hash
        )

    def review(
        self, *, decision: SemanticRelationState, reviewer: str,
        rationale: str, occurred_at: str,
    ) -> "SemanticRelation":
        if decision is SemanticRelationState.PROPOSED:
            raise ValueError("Semantic relation review must accept or reject")
        if decision is self.state:
            raise ValueError(
                f"Semantic relation is already {decision.value}"
            )
        if reviewer == self.proposed_by:
            raise ValueError(
                "Semantic relation reviewer must differ from proposer"
            )
        if not rationale.strip():
            raise ValueError("Semantic relation review rationale is required")
        if not reviewer.strip() or not occurred_at.strip():
            raise ValueError(
                "Semantic relation reviewer and timestamp are required"
            )
        identity = (
            f"{self.relation_id}:{self.content_hash}:{decision.value}:"
            f"{reviewer}:{occurred_at}"
        )
        event = SemanticRelationReviewEvent(
            f"relation-review-{sha256(identity.encode()).hexdigest()[:24]}",
            decision, reviewer, rationale.strip(), occurred_at, self.state,
        )
        return replace(
            self, state=decision, reviews=self.reviews + (event,),
            content_hash="",
        ).finalized()

    def admit(
        self, *, graph_id: str, intake_id: str, indexer: str,
        occurred_at: str,
    ) -> "SemanticRelation":
        if self.state is not SemanticRelationState.ACCEPTED:
            raise ValueError("Only an accepted semantic relation can be admitted")
        identity = f"{self.relation_id}:{graph_id}:{intake_id}"
        admission_id = (
            f"relation-admission-{sha256(identity.encode()).hexdigest()[:24]}"
        )
        existing = next((
            item for item in self.admissions
            if item.admission_id == admission_id
        ), None)
        if existing is not None:
            if (
                existing.graph_id != graph_id
                or existing.intake_id != intake_id
                or existing.indexer != indexer
                or existing.occurred_at != occurred_at
            ):
                raise RuntimeError("Semantic relation admission conflict")
            return self
        event = SemanticRelationAdmissionEvent(
            admission_id, graph_id, intake_id, indexer, occurred_at,
        )
        return replace(
            self, admissions=self.admissions + (event,), content_hash="",
        ).finalized()
