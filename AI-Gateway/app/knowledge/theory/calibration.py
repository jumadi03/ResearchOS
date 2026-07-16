"""Versioned, reviewer-governed alignment threshold calibration."""

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path

from app.architecture.persistence import atomic_write


@dataclass(frozen=True, slots=True)
class AlignmentCalibration:
    calibration_id: str
    method: str
    version: str
    current_threshold: float
    proposed_threshold: float
    reviewed_outcomes: int
    observed_precision: float
    observed_recall: float
    benchmark_precision: float
    benchmark_recall: float
    proposer: str
    rationale: str
    proposed_at: str
    status: str = "pending"
    approver: str | None = None
    approved_at: str | None = None
    previous_version: str | None = None
    content_hash: str = ""

    def finalized(self):
        payload = asdict(self)
        payload["content_hash"] = ""
        digest = sha256(json.dumps(
            payload, sort_keys=True, separators=(",", ":")
        ).encode()).hexdigest()
        return AlignmentCalibration(**{**payload, "content_hash": digest})

    def verify(self):
        return bool(self.content_hash) and self.finalized().content_hash == self.content_hash


class AlignmentCalibrationStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def save(self, item: AlignmentCalibration) -> Path:
        if not item.verify():
            raise ValueError("Calibration integrity verification failed")
        path = self.root / f"{item.calibration_id}-{item.content_hash}.json"
        payload = json.dumps(
            asdict(item), sort_keys=True, separators=(",", ":")
        ).encode()
        if not path.exists():
            atomic_write(path, payload)
        elif path.read_bytes() != payload:
            raise RuntimeError("Calibration snapshot conflict")
        return path

    def load_all(self) -> tuple[AlignmentCalibration, ...]:
        if not self.root.exists():
            return ()
        snapshots = []
        for path in self.root.glob("*.json"):
            item = AlignmentCalibration(**json.loads(path.read_text(encoding="utf-8")))
            if not item.verify():
                raise ValueError(f"Calibration snapshot integrity failed: {path.name}")
            snapshots.append((
                item.calibration_id,
                item.status == "approved",
                item.approved_at or item.proposed_at,
                path.stat().st_mtime_ns, path.name, item,
            ))
        latest = {}
        for _, _, _, _, _, item in sorted(snapshots):
            latest[item.calibration_id] = item
        return tuple(sorted(
            latest.values(), key=lambda item: (item.proposed_at, item.calibration_id),
            reverse=True,
        ))
