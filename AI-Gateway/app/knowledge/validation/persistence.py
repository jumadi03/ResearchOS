"""Immutable validation report persistence."""

from dataclasses import asdict
import json
from pathlib import Path
from app.architecture.persistence import atomic_write
from app.knowledge.validation.models import ValidationReport


class ValidationReportStore:
    def __init__(self, root: Path) -> None: self.root = root
    def save(self, report: ValidationReport) -> Path:
        if not report.verify(): raise ValueError("Validation report integrity verification failed")
        payload = json.dumps(asdict(report), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        path = self.root / report.report_id / f"v{report.schema_version}-{report.content_hash}.json"
        if not path.exists(): atomic_write(path, payload)
        elif path.read_bytes() != payload: raise RuntimeError("Validation report snapshot conflict")
        return path
