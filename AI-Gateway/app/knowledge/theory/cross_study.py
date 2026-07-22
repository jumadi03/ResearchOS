"""Reviewer-governed cross-study propositions with evidence provenance."""

from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from hashlib import sha256
import json
from pathlib import Path

from app.architecture.persistence import atomic_write
from app.knowledge.extraction.models import ExtractionReviewState
from app.knowledge.modeling.models import (
    KnowledgeNodeType, ScientificKnowledgeGraph,
)
from app.knowledge.theory.models import (
    EvidenceStance, TheoryBundle, TheoryEvidence, TheoryProposal,
)


class CrossStudyPropositionState(StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class CrossStudyEvidenceReference:
    graph_id: str
    object_id: str
    stance: EvidenceStance
    quote_hash: str
    document_id: str
    page: int
    confidence: float
    node_type: KnowledgeNodeType


@dataclass(frozen=True, slots=True)
class CrossStudyPropositionReview:
    review_id: str
    decision: CrossStudyPropositionState
    reviewer: str
    rationale: str
    occurred_at: str
    previous_state: CrossStudyPropositionState


@dataclass(frozen=True, slots=True)
class CrossStudyProposition:
    proposition_id: str
    statement: str
    evidence: tuple[CrossStudyEvidenceReference, ...]
    proposed_by: str
    rationale: str
    proposed_at: str
    state: CrossStudyPropositionState = CrossStudyPropositionState.PROPOSED
    reviews: tuple[CrossStudyPropositionReview, ...] = ()
    content_hash: str = ""
    schema_version: str = "1.0"

    def expected_hash(self) -> str:
        payload = asdict(replace(self, content_hash=""))
        return sha256(json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ).encode()).hexdigest()

    def finalized(self):
        return replace(self, content_hash=self.expected_hash())

    def verify(self) -> bool:
        graph_ids = {item.graph_id for item in self.evidence}
        object_ids = {item.object_id for item in self.evidence}
        document_ids = {item.document_id for item in self.evidence}
        projected = CrossStudyPropositionState.PROPOSED
        for review in self.reviews:
            if review.previous_state is not projected:
                return False
            projected = review.decision
        return bool(
            self.schema_version == "1.0"
            and self.statement.strip() and self.rationale.strip()
            and self.proposed_by.strip() and self.proposed_at.strip()
            and len(self.evidence) >= 2
            and len(graph_ids) >= 2 and len(object_ids) >= 2
            and len(document_ids) >= 2
            and all(
                item.quote_hash and len(item.quote_hash) == 64
                and item.document_id.strip()
                and 0 <= item.confidence <= 1
                and item.node_type in {
                    KnowledgeNodeType.RESULT,
                    KnowledgeNodeType.CONCLUSION,
                    KnowledgeNodeType.LIMITATION,
                }
                for item in self.evidence
            )
            and projected is self.state
            and all(
                item.decision is not CrossStudyPropositionState.PROPOSED
                and item.reviewer.strip() and item.rationale.strip()
                and item.occurred_at.strip()
                and item.reviewer != self.proposed_by
                for item in self.reviews
            )
            and self.content_hash == self.expected_hash()
        )

    def review(self, *, decision, reviewer, rationale, occurred_at):
        choice = CrossStudyPropositionState(decision)
        if choice is CrossStudyPropositionState.PROPOSED:
            raise ValueError("Proposition review must accept or reject")
        if reviewer == self.proposed_by:
            raise ValueError("Proposition reviewer must differ from proposer")
        if not rationale.strip():
            raise ValueError("Proposition review rationale is required")
        identity = (
            f"{self.proposition_id}:{self.content_hash}:{choice.value}:"
            f"{reviewer}:{occurred_at}"
        )
        event = CrossStudyPropositionReview(
            f"cross-study-review-{sha256(identity.encode()).hexdigest()[:24]}",
            choice, reviewer, rationale.strip(), occurred_at, self.state,
        )
        return replace(
            self, state=choice, reviews=self.reviews + (event,),
            content_hash="",
        ).finalized()


class CrossStudyPropositionStore:
    def __init__(self, root: Path):
        self.root = root

    def save(self, item: CrossStudyProposition) -> Path:
        if not item.verify():
            raise ValueError("Cross-study proposition integrity failed")
        payload = json.dumps(
            asdict(item), ensure_ascii=False, sort_keys=True,
            separators=(",", ":"),
        ).encode()
        path = (
            self.root / item.proposition_id
            / f"v{item.schema_version}-{item.content_hash}.json"
        )
        if not path.exists():
            atomic_write(path, payload)
        elif path.read_bytes() != payload:
            raise RuntimeError("Cross-study proposition snapshot conflict")
        return path

    def load_all(self) -> tuple[CrossStudyProposition, ...]:
        if not self.root.exists():
            return ()
        items = []
        for directory in sorted(p for p in self.root.iterdir() if p.is_dir()):
            snapshots = tuple(directory.glob("v*.json"))
            if not snapshots:
                continue
            path = max(
                snapshots,
                key=lambda p: (
                    len(json.loads(p.read_text(encoding="utf-8")).get(
                        "reviews", ()
                    )),
                    p.stat().st_mtime_ns,
                ),
            )
            raw = json.loads(path.read_text(encoding="utf-8"))
            item = CrossStudyProposition(
                raw["proposition_id"], raw["statement"],
                tuple(CrossStudyEvidenceReference(
                    value["graph_id"], value["object_id"],
                    EvidenceStance(value["stance"]), value["quote_hash"],
                    value["document_id"], value["page"], value["confidence"],
                    KnowledgeNodeType(value["node_type"]),
                ) for value in raw["evidence"]),
                raw["proposed_by"], raw["rationale"], raw["proposed_at"],
                CrossStudyPropositionState(raw["state"]),
                tuple(CrossStudyPropositionReview(
                    value["review_id"],
                    CrossStudyPropositionState(value["decision"]),
                    value["reviewer"], value["rationale"],
                    value["occurred_at"],
                    CrossStudyPropositionState(value["previous_state"]),
                ) for value in raw.get("reviews", ())),
                raw["content_hash"], raw.get("schema_version", "1.0"),
            )
            if not item.verify():
                raise ValueError(
                    f"Cross-study proposition snapshot failed: {path.name}"
                )
            items.append(item)
        return tuple(items)


def bind_cross_study_evidence(
    graphs: dict[str, ScientificKnowledgeGraph],
    references: tuple[tuple[str, str, str], ...],
) -> tuple[CrossStudyEvidenceReference, ...]:
    if len(references) < 2:
        raise ValueError("Cross-study proposition requires two evidence references")
    bound = []
    seen = set()
    for graph_id, object_id, stance in references:
        key = graph_id, object_id
        if key in seen:
            raise ValueError("Cross-study evidence reference is duplicated")
        seen.add(key)
        graph = graphs.get(graph_id)
        if graph is None or not graph.verify():
            raise ValueError(f"Verified graph is required: {graph_id}")
        node = next(
            (
                item for item in graph.nodes
                if item.provenance is not None
                and item.provenance.object_id == object_id
            ),
            None,
        )
        if node is None:
            raise ValueError(
                f"Evidence object does not belong to graph: {object_id}"
            )
        provenance = node.provenance
        if (
            provenance.review_state is not ExtractionReviewState.ACCEPTED
            or provenance.review_event is None
        ):
            raise ValueError(f"Accepted evidence is required: {object_id}")
        bound.append(CrossStudyEvidenceReference(
            graph_id, object_id, EvidenceStance(stance),
            provenance.quote_hash, provenance.document_id, provenance.page,
            provenance.confidence, node.node_type,
        ))
    return tuple(sorted(
        bound, key=lambda item: (item.graph_id, item.object_id),
    ))


def proposition_theory_bundle(
    item: CrossStudyProposition, *, created_at: str,
) -> TheoryBundle:
    if (
        not item.verify()
        or item.state is not CrossStudyPropositionState.ACCEPTED
    ):
        raise ValueError("Accepted cross-study proposition is required")
    evidence = tuple(TheoryEvidence(
        "proposition-support-" + sha256(
            f"{item.proposition_id}:{ref.graph_id}:{ref.object_id}".encode()
        ).hexdigest()[:24],
        ref.graph_id, ref.object_id, ref.stance, ref.confidence,
        ref.quote_hash, ref.document_id, ref.page,
    ) for ref in item.evidence)
    identity = f"{item.proposition_id}:{item.content_hash}:{created_at}:1.3"
    proposal = TheoryProposal(
        f"theory-{sha256(item.statement.casefold().encode()).hexdigest()[:24]}",
        item.statement, evidence,
        sum(ref.stance is EvidenceStance.SUPPORTS for ref in item.evidence),
        sum(ref.stance is EvidenceStance.CONTRADICTS for ref in item.evidence),
    )
    return TheoryBundle(
        f"theory-bundle-{sha256(identity.encode()).hexdigest()[:24]}",
        tuple(sorted({ref.graph_id for ref in item.evidence})),
        created_at, (proposal,), (),
    ).finalized()
