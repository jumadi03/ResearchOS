"""Immutable theory bundle snapshots."""

from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from app.architecture.persistence import atomic_write
from app.knowledge.theory.models import (
    CompetingTheory, EvidenceStance, TheoryAlignmentDecisionEvent,
    TheoryAlignmentEvent, TheoryBundle, TheoryEvidence, TheoryProposal,
    TheoryReviewEvent, TheoryReviewState,
)


class TheoryBundleStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def save(self, bundle: TheoryBundle) -> Path:
        if not bundle.verify():
            raise ValueError("Theory bundle integrity verification failed")
        payload = json.dumps(asdict(bundle), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        path = self.root / bundle.bundle_id / f"v{bundle.schema_version}-{bundle.content_hash}.json"
        if not path.exists(): atomic_write(path, payload)
        elif path.read_bytes() != payload: raise RuntimeError("Theory bundle snapshot conflict")
        return path

    def load_all(self) -> tuple[TheoryBundle, ...]:
        if not self.root.exists():
            return ()
        bundles = []
        for directory in sorted(path for path in self.root.iterdir() if path.is_dir()):
            snapshots = tuple(directory.glob("v*.json"))
            if not snapshots:
                continue
            def snapshot_rank(item: Path) -> tuple[int, int, str]:
                value = json.loads(item.read_text(encoding="utf-8"))
                event_count = (
                    len(value.get("reviews", ())) + len(value.get("alignments", ()))
                    + len(value.get("alignment_decisions", ()))
                )
                return event_count, item.stat().st_mtime_ns, item.name
            path = max(snapshots, key=snapshot_rank)
            raw = json.loads(path.read_text(encoding="utf-8"))
            proposals = tuple(TheoryProposal(
                item["theory_id"], item["statement"],
                tuple(TheoryEvidence(
                    evidence["edge_id"], evidence["graph_id"], evidence["object_id"],
                    EvidenceStance(evidence["stance"]), evidence["confidence"],
                    evidence["quote_hash"], evidence.get("document_id"),
                    evidence.get("page"),
                ) for evidence in item["evidence"]),
                item["support_count"], item["contradiction_count"],
                TheoryReviewState(item.get("review_state", "proposed")),
            ) for item in raw["proposals"])
            bundle = TheoryBundle(
                bundle_id=raw["bundle_id"], graph_ids=tuple(raw["graph_ids"]),
                created_at=raw["created_at"], proposals=proposals,
                competing=tuple(CompetingTheory(**item) for item in raw.get("competing", ())),
                reviews=tuple(TheoryReviewEvent(
                    item["theory_id"], TheoryReviewState(item["decision"]),
                    item["reviewer"], item["rationale"], item["occurred_at"],
                ) for item in raw.get("reviews", ())),
                alignments=tuple(TheoryAlignmentEvent(
                    item["alignment_id"], tuple(item["source_theory_ids"]),
                    item["resulting_theory_id"], item["statement"], item["reviewer"],
                    item["rationale"], item["occurred_at"],
                    item.get("candidate_id"), item.get("candidate_method"),
                    item.get("candidate_score"), item.get("candidate_threshold"),
                    tuple(item.get("candidate_shared_terms", ())),
                ) for item in raw.get("alignments", ())),
                alignment_decisions=tuple(TheoryAlignmentDecisionEvent(
                    item["decision_id"], tuple(item["theory_ids"]), item["decision"],
                    item["reviewer"], item["rationale"], item["occurred_at"],
                    item.get("candidate_id"), item.get("candidate_method"),
                    item.get("candidate_score"), item.get("candidate_threshold"),
                    tuple(item.get("candidate_shared_terms", ())),
                ) for item in raw.get("alignment_decisions", ())),
                content_hash=raw["content_hash"],
                schema_version=raw.get("schema_version", "1.0"),
            )
            if raw.get("schema_version", "1.0") != "1.3":
                historical = dict(raw)
                expected = historical.get("content_hash", "")
                historical["content_hash"] = ""
                actual = sha256(json.dumps(
                    historical, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ).encode()).hexdigest()
                if not expected or actual != expected:
                    raise ValueError(f"Theory bundle snapshot integrity failed: {path.name}")
                bundle = TheoryBundle(
                    bundle.bundle_id, bundle.graph_ids, bundle.created_at,
                    bundle.proposals, bundle.competing, bundle.reviews,
                    bundle.alignments, bundle.alignment_decisions,
                    schema_version="1.3",
                ).finalized()
            elif not bundle.verify():
                raise ValueError(f"Theory bundle snapshot integrity failed: {path.name}")
            bundles.append(bundle)
        return tuple(bundles)
