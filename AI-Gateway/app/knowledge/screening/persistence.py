"""Content-addressed portable screening-decision snapshots."""

from dataclasses import asdict
import json
from pathlib import Path

from app.architecture.persistence import atomic_write
from app.knowledge.screening.models import (
    ScreeningDecision, ScreeningDimension, ScreeningReason, ScreeningStatus,
)


class ScreeningDecisionStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def save(self, decision: ScreeningDecision) -> Path:
        if not decision.verify():
            raise ValueError("Screening decision integrity verification failed")
        path = self.root / decision.document_id / f"v{decision.schema_version}-{decision.decision_hash}.json"
        payload = json.dumps(asdict(decision), ensure_ascii=False, sort_keys=True)
        if path.exists() and path.read_text(encoding="utf-8") != payload:
            raise RuntimeError("Screening decision snapshot conflict")
        if not path.exists():
            atomic_write(path, payload)
        return path

    def load(self, path: Path) -> ScreeningDecision:
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["status"] = ScreeningStatus(raw["status"])
        raw["reasons"] = tuple(
            ScreeningReason(
                ScreeningDimension(item["dimension"]), item["code"],
                item["passed"], item["explanation"],
            )
            for item in raw["reasons"]
        )
        decision = ScreeningDecision(**raw)
        if not decision.verify():
            raise ValueError("Screening decision integrity verification failed")
        return decision

    def find_eligible(
        self, document_id: str, content_hash: str,
        inspection_manifest_hash: str,
    ) -> ScreeningDecision | None:
        for path in sorted((self.root / document_id).glob("v*.json"), reverse=True):
            decision = self.load(path)
            if (
                decision.document_content_hash == content_hash
                and decision.inspection_manifest_hash == inspection_manifest_hash
                and decision.status is ScreeningStatus.ELIGIBLE
            ):
                return decision
        return None
