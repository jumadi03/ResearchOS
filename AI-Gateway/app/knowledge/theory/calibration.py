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


@dataclass(frozen=True, slots=True)
class CalibrationReview:
    reviewer: str
    decision: str
    rationale: str
    reviewed_at: str
    role: str = "independent"


@dataclass(frozen=True, slots=True)
class CalibrationCase:
    case_id: str
    bundle_id: str
    theory_ids: tuple[str, str]
    statements: tuple[str, str]
    graph_ids: tuple[str, ...]
    evidence_by_theory: tuple[tuple[dict, ...], tuple[dict, ...]]
    method: str
    score: float
    stratum: str
    created_at: str
    reviews: tuple[CalibrationReview, ...] = ()
    status: str = "awaiting_first_review"
    final_outcome: str | None = None
    finalized_at: str | None = None
    content_hash: str = ""

    def finalized(self):
        payload = asdict(self)
        payload["content_hash"] = ""
        digest = sha256(json.dumps(
            payload, sort_keys=True, separators=(",", ":")
        ).encode()).hexdigest()
        return CalibrationCase(
            **{
                **payload,
                "theory_ids": tuple(payload["theory_ids"]),
                "statements": tuple(payload["statements"]),
                "graph_ids": tuple(payload["graph_ids"]),
                "evidence_by_theory": tuple(
                    tuple(items) for items in payload["evidence_by_theory"]
                ),
                "reviews": tuple(CalibrationReview(**item) for item in payload["reviews"]),
                "content_hash": digest,
            }
        )

    def verify(self):
        return bool(self.content_hash) and self.finalized().content_hash == self.content_hash


class CalibrationCaseStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def save(self, item: CalibrationCase) -> Path:
        if not item.verify():
            raise ValueError("Calibration case integrity verification failed")
        path = self.root / item.case_id / f"{len(item.reviews)}-{item.content_hash}.json"
        payload = json.dumps(
            asdict(item), sort_keys=True, separators=(",", ":")
        ).encode()
        if not path.exists():
            atomic_write(path, payload)
        elif path.read_bytes() != payload:
            raise RuntimeError("Calibration case snapshot conflict")
        return path

    def load_all(self) -> tuple[CalibrationCase, ...]:
        if not self.root.exists():
            return ()
        cases = []
        for directory in sorted(path for path in self.root.iterdir() if path.is_dir()):
            paths = tuple(directory.glob("*.json"))
            if not paths:
                continue
            path = max(paths, key=lambda item: (int(item.name.split("-", 1)[0]), item.stat().st_mtime_ns))
            raw = json.loads(path.read_text(encoding="utf-8"))
            item = CalibrationCase(
                case_id=raw["case_id"], bundle_id=raw["bundle_id"],
                theory_ids=tuple(raw["theory_ids"]),
                statements=tuple(raw["statements"]),
                graph_ids=tuple(raw["graph_ids"]),
                evidence_by_theory=tuple(
                    tuple(evidence for evidence in entries)
                    for entries in raw["evidence_by_theory"]
                ),
                method=raw["method"], score=raw["score"],
                stratum=raw["stratum"], created_at=raw["created_at"],
                reviews=tuple(CalibrationReview(**review) for review in raw["reviews"]),
                status=raw["status"], final_outcome=raw["final_outcome"],
                finalized_at=raw["finalized_at"], content_hash=raw["content_hash"],
            )
            if not item.verify():
                raise ValueError(f"Calibration case snapshot integrity failed: {path.name}")
            cases.append(item)
        return tuple(cases)
