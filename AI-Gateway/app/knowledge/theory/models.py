"""Canonical theory proposal and review contracts."""

from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from hashlib import sha256
import json


class EvidenceStance(StrEnum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"


class TheoryReviewState(StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class TheoryEvidence:
    edge_id: str
    graph_id: str
    object_id: str
    stance: EvidenceStance
    confidence: float
    quote_hash: str
    document_id: str | None = None
    page: int | None = None


@dataclass(frozen=True, slots=True)
class CompetingTheory:
    left_theory_id: str
    right_theory_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class TheoryProposal:
    theory_id: str
    statement: str
    evidence: tuple[TheoryEvidence, ...]
    support_count: int
    contradiction_count: int
    review_state: TheoryReviewState = TheoryReviewState.PROPOSED


@dataclass(frozen=True, slots=True)
class TheoryReviewEvent:
    theory_id: str
    decision: TheoryReviewState
    reviewer: str
    rationale: str
    occurred_at: str


@dataclass(frozen=True, slots=True)
class TheoryAlignmentEvent:
    alignment_id: str
    source_theory_ids: tuple[str, ...]
    resulting_theory_id: str
    statement: str
    reviewer: str
    rationale: str
    occurred_at: str


@dataclass(frozen=True, slots=True)
class TheoryAlignmentDecisionEvent:
    decision_id: str
    theory_ids: tuple[str, str]
    decision: str
    reviewer: str
    rationale: str
    occurred_at: str


@dataclass(frozen=True, slots=True)
class TheoryAlignmentCandidate:
    candidate_id: str
    theory_ids: tuple[str, str]
    statements: tuple[str, str]
    graph_ids: tuple[str, ...]
    evidence_by_theory: tuple[tuple[TheoryEvidence, ...], tuple[TheoryEvidence, ...]]
    lexical_overlap_score: float
    shared_terms: tuple[str, ...] = ()
    shared_bigrams: tuple[str, ...] = ()
    score_components: tuple[tuple[str, float], ...] = ()
    explanation: str = ""
    method: str = "explainable-lexical-v2"
    advisory: bool = True


@dataclass(frozen=True, slots=True)
class TheoryBundle:
    bundle_id: str
    graph_ids: tuple[str, ...]
    created_at: str
    proposals: tuple[TheoryProposal, ...]
    competing: tuple[CompetingTheory, ...]
    reviews: tuple[TheoryReviewEvent, ...] = ()
    alignments: tuple[TheoryAlignmentEvent, ...] = ()
    alignment_decisions: tuple[TheoryAlignmentDecisionEvent, ...] = ()
    content_hash: str = ""
    schema_version: str = "1.2"

    def finalized(self):
        payload = asdict(replace(self, content_hash=""))
        digest = sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return replace(self, content_hash=digest)

    def verify(self) -> bool:
        return bool(self.content_hash) and self.finalized().content_hash == self.content_hash
