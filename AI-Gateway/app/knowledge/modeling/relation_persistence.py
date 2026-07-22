"""Immutable snapshots for reviewer-governed semantic relations."""

from dataclasses import asdict
import json
from pathlib import Path

from app.architecture.persistence import atomic_write
from app.knowledge.modeling.models import KnowledgeEdgeType
from app.knowledge.modeling.relation_review import (
    SemanticRelation, SemanticRelationAdmissionEvent,
    SemanticRelationReviewEvent, SemanticRelationState,
)


class SemanticRelationStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def save(self, relation: SemanticRelation) -> Path:
        if not relation.verify():
            raise ValueError("Semantic relation integrity verification failed")
        payload = json.dumps(
            asdict(relation), ensure_ascii=False, sort_keys=True,
            separators=(",", ":"),
        ).encode()
        path = (
            self.root / relation.relation_id
            / f"v{relation.schema_version}-{relation.content_hash}.json"
        )
        if not path.exists():
            atomic_write(path, payload)
        elif path.read_bytes() != payload:
            raise RuntimeError("Semantic relation snapshot conflict")
        return path

    def load_all(self) -> tuple[SemanticRelation, ...]:
        if not self.root.exists():
            return ()
        restored = []
        for directory in sorted(
            item for item in self.root.iterdir() if item.is_dir()
        ):
            snapshots = tuple(directory.glob("v*.json"))
            if not snapshots:
                continue
            raw_by_path = {
                path: json.loads(path.read_text(encoding="utf-8"))
                for path in snapshots
            }
            path = max(
                snapshots,
                key=lambda item: (
                    len(raw_by_path[item].get("reviews", ())),
                    len(raw_by_path[item].get("admissions", ())),
                    item.stat().st_mtime_ns, item.name,
                ),
            )
            raw = raw_by_path[path]
            relation = SemanticRelation(
                raw["relation_id"], raw["extraction_id"],
                raw["source_object_id"], raw["target_object_id"],
                KnowledgeEdgeType(raw["edge_type"]),
                raw["provenance_object_id"], raw["proposed_by"],
                raw["proposal_rationale"], raw["proposed_at"],
                SemanticRelationState(raw["state"]),
                tuple(SemanticRelationReviewEvent(
                    item["review_id"], SemanticRelationState(item["decision"]),
                    item["reviewer"], item["rationale"], item["occurred_at"],
                    SemanticRelationState(item["previous_state"]),
                ) for item in raw.get("reviews", ())),
                tuple(SemanticRelationAdmissionEvent(**item)
                      for item in raw.get("admissions", ())),
                raw["content_hash"], raw.get("schema_version", "1.0"),
            )
            if not relation.verify():
                raise ValueError(
                    f"Semantic relation snapshot integrity failed: {path.name}"
                )
            restored.append(relation)
        return tuple(restored)
