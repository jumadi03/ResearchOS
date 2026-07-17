"""Immutable portable snapshots of canonical Knowledge Intake decisions."""

from dataclasses import asdict
import json
from pathlib import Path

from app.architecture.persistence import atomic_write
from app.knowledge.intake.models import KnowledgeIntakeManifest


class KnowledgeIntakeStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def save(self, intake: KnowledgeIntakeManifest) -> Path:
        if not intake.verify():
            raise ValueError("Knowledge intake manifest integrity verification failed")
        payload = json.dumps(
            asdict(intake), ensure_ascii=False, sort_keys=True,
            separators=(",", ":"),
        ).encode()
        path = self.root / intake.intake_id / (
            f"v{intake.schema_version}-{intake.content_hash}.json"
        )
        if not path.exists():
            atomic_write(path, payload)
        elif path.read_bytes() != payload:
            raise RuntimeError("Knowledge intake snapshot conflict")
        return path
