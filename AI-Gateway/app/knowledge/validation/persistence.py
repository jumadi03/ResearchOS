"""Immutable validation report persistence."""

from dataclasses import asdict
import json
from pathlib import Path
from app.architecture.persistence import atomic_write
from app.knowledge.validation.models import (
    AssessmentMethod, RiskOfBias, TheoryAssessment, ValidationReport,
    ValidationStatus,
)


class ValidationReportStore:
    def __init__(self, root: Path) -> None: self.root = root
    def save(self, report: ValidationReport) -> Path:
        if not report.verify(): raise ValueError("Validation report integrity verification failed")
        payload = json.dumps(asdict(report), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        path = self.root / report.report_id / f"v{report.schema_version}-{report.content_hash}.json"
        if not path.exists(): atomic_write(path, payload)
        elif path.read_bytes() != payload: raise RuntimeError("Validation report snapshot conflict")
        return path

    def load_all(self) -> tuple[ValidationReport, ...]:
        if not self.root.exists(): return ()
        reports = []
        for directory in sorted(path for path in self.root.iterdir() if path.is_dir()):
            snapshots = tuple(directory.glob("v*.json"))
            if not snapshots: continue
            path = max(snapshots, key=lambda item: (item.stat().st_mtime_ns, item.name))
            raw = json.loads(path.read_text(encoding="utf-8"))
            method = raw["method"]
            report = ValidationReport(
                raw["report_id"], raw["theory_bundle_id"], raw["assessed_at"],
                raw["search_completed_at"], raw["max_age_days"], raw["reviewer"],
                AssessmentMethod(
                    method["method_id"], method["version"], method["minimum_replications"],
                    tuple((RiskOfBias(item[0]), item[1]) for item in method["bias_factors"]),
                    method["contradiction_penalty"],
                ),
                tuple(TheoryAssessment(
                    item["theory_id"], ValidationStatus(item["status"]),
                    item["confidence_score"], item["support_assertions"],
                    item["independent_graphs"], item["contradiction_assertions"],
                    RiskOfBias(item["risk_of_bias"]), tuple(item["reasons"]),
                    tuple(item["evidence_edge_ids"]),
                ) for item in raw["assessments"]),
                ValidationStatus(raw["status"]), raw["content_hash"],
                raw.get("schema_version", "1.0"),
            )
            if not report.verify():
                raise ValueError(f"Validation report snapshot integrity failed: {path.name}")
            reports.append(report)
        return tuple(reports)
