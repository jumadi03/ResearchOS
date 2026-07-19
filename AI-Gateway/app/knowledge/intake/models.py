"""Immutable contracts for registering accepted evidence in the Knowledge Layer."""

from dataclasses import asdict, dataclass, replace
from hashlib import sha256
import json


@dataclass(frozen=True, slots=True)
class KnowledgeIntakeDecision:
    evidence_object_id: str
    admitted: bool
    reason: str
    review_provenance_id: str = ""


@dataclass(frozen=True, slots=True)
class KnowledgeIntakeManifest:
    intake_id: str
    extraction_id: str
    extraction_manifest_hash: str
    graph_id: str
    graph_content_hash: str
    requested_evidence_object_ids: tuple[str, ...]
    admitted_evidence_object_ids: tuple[str, ...]
    decisions: tuple[KnowledgeIntakeDecision, ...]
    actor_id: str
    occurred_at: str
    content_hash: str = ""
    schema_version: str = "1.0"
    semantic_relation_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "requested_evidence_object_ids",
            tuple(self.requested_evidence_object_ids),
        )
        object.__setattr__(
            self, "admitted_evidence_object_ids",
            tuple(self.admitted_evidence_object_ids),
        )
        object.__setattr__(self, "decisions", tuple(self.decisions))
        object.__setattr__(
            self, "semantic_relation_ids", tuple(self.semantic_relation_ids),
        )

    def expected_hash(self) -> str:
        payload = asdict(replace(self, content_hash=""))
        if self.schema_version == "1.0":
            payload.pop("semantic_relation_ids", None)
        return sha256(json.dumps(
            payload, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"),
        ).encode()).hexdigest()

    def finalized(self) -> "KnowledgeIntakeManifest":
        return replace(self, content_hash=self.expected_hash())

    def verify(self) -> bool:
        requested = tuple(sorted(set(self.requested_evidence_object_ids)))
        admitted = tuple(sorted(set(self.admitted_evidence_object_ids)))
        decision_ids = tuple(sorted(item.evidence_object_id for item in self.decisions))
        admitted_from_decisions = tuple(sorted(
            item.evidence_object_id for item in self.decisions if item.admitted
        ))
        return bool(
            self.schema_version in {"1.0", "1.1"}
            and (
                self.schema_version == "1.1"
                or not self.semantic_relation_ids
            )
            and self.intake_id
            and self.extraction_id
            and len(self.extraction_manifest_hash) == 64
            and self.graph_id
            and len(self.graph_content_hash) == 64
            and requested
            and admitted
            and requested == self.requested_evidence_object_ids
            and admitted == self.admitted_evidence_object_ids
            and decision_ids == requested
            and admitted_from_decisions == admitted
            and all(
                item.reason.strip()
                and (
                    not item.admitted
                    or bool(item.review_provenance_id.strip())
                )
                for item in self.decisions
            )
            and self.actor_id.strip()
            and self.occurred_at.strip()
            and tuple(sorted(set(self.semantic_relation_ids)))
            == self.semantic_relation_ids
            and self.content_hash == self.expected_hash()
        )
