"""Immutable gap analysis snapshots."""

from dataclasses import asdict
import json
from pathlib import Path

from app.architecture.persistence import atomic_write
from app.knowledge.gaps.models import GapAnalysis


class GapAnalysisStore:
    def __init__(self, root: Path) -> None: self.root = root

    def save(self, analysis: GapAnalysis) -> Path:
        if not analysis.verify(): raise ValueError("Gap analysis integrity verification failed")
        payload = json.dumps(asdict(analysis), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        path = self.root / analysis.analysis_id / f"v{analysis.schema_version}-{analysis.content_hash}.json"
        if not path.exists(): atomic_write(path, payload)
        elif path.read_bytes() != payload: raise RuntimeError("Gap analysis snapshot conflict")
        return path
