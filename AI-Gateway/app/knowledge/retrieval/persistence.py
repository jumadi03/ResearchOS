"""Content-addressed metadata snapshot persistence."""

from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from app.architecture.persistence import atomic_write
from app.knowledge.retrieval.models import MetadataRun


class MetadataSnapshotStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def save(self, run: MetadataRun) -> Path:
        payload = json.dumps(asdict(run), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        digest = sha256(payload).hexdigest()
        path = self.root / run.discovery_run_id / "metadata" / f"v{run.schema_version}-{digest}.json"
        if not path.exists():
            atomic_write(path, payload)
        elif path.read_bytes() != payload:
            raise RuntimeError("Metadata snapshot integrity conflict")
        return path
