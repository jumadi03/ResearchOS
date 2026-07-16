"""Immutable theory bundle snapshots."""

from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from app.architecture.persistence import atomic_write
from app.knowledge.theory.models import (
    CompetingTheory, EvidenceStance, TheoryAlignmentEvent, TheoryBundle,
    TheoryEvidence, TheoryProposal, TheoryReviewEvent, TheoryReviewState,
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
                event_count = len(value.get("reviews", ())) + len(value.get("alignments", ()))
                return event_count, item.stat().st_mtime_ns, item.name
            path = max(snapshots, key=snapshot_rank)
            raw = json.loads(path.read_text(encoding="utf-8"))
            proposals = tuple(TheoryProposal(
                item["theory_id"], item["statement"],
                tuple(TheoryEvidence(
                    evidence["edge_id"], evidence["graph_id"], evidence["object_id"],
                    EvidenceStance(evidence["stance"]), evidence["confidence"],
                    evidence["quote_hash"],
                ) for evidence in item["evidence"]),
                item["support_count"], item["contradiction_count"],
                TheoryReviewState(item.get("review_state", "proposed")),
            ) for item in raw["proposals"])
            bundle = TheoryBundle(
                raw["bundle_id"], tuple(raw["graph_ids"]), raw["created_at"], proposals,
                tuple(CompetingTheory(**item) for item in raw.get("competing", ())),
                tuple(TheoryReviewEvent(
                    item["theory_id"], TheoryReviewState(item["decision"]),
                    item["reviewer"], item["rationale"], item["occurred_at"],
                ) for item in raw.get("reviews", ())),
                tuple(TheoryAlignmentEvent(
                    item["alignment_id"], tuple(item["source_theory_ids"]),
                    item["resulting_theory_id"], item["statement"], item["reviewer"],
                    item["rationale"], item["occurred_at"],
                ) for item in raw.get("alignments", ())),
                raw["content_hash"], raw.get("schema_version", "1.0"),
            )
            if raw.get("schema_version", "1.0") == "1.0":
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
                    bundle.alignments, schema_version="1.1",
                ).finalized()
            elif not bundle.verify():
                raise ValueError(f"Theory bundle snapshot integrity failed: {path.name}")
            bundles.append(bundle)
        return tuple(bundles)
