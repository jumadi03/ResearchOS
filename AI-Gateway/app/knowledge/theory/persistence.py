"""Immutable theory bundle snapshots."""

from dataclasses import asdict
import json
from pathlib import Path

from app.architecture.persistence import atomic_write
from app.knowledge.theory.models import TheoryBundle


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
