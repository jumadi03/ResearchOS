"""Content-addressed citation traversal snapshots."""

from dataclasses import asdict
import json
from pathlib import Path

from app.architecture.persistence import atomic_write
from app.knowledge.retrieval.snowballing import CitationTraversalRun


class CitationTraversalSnapshotStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def save(self, run: CitationTraversalRun) -> Path:
        if not run.verify():
            raise ValueError("Citation traversal manifest integrity verification failed")
        payload = json.dumps(
            asdict(run), ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")
        path = (
            self.root / run.discovery_run_id / "citations"
            / f"v{run.schema_version}-{run.manifest_hash}.json"
        )
        if not path.exists():
            atomic_write(path, payload)
        elif path.read_bytes() != payload:
            raise RuntimeError("Citation traversal snapshot integrity conflict")
        return path
