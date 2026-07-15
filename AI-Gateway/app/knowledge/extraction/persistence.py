"""Immutable extraction manifest persistence."""

from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from app.architecture.persistence import atomic_write
from app.knowledge.extraction.models import ExtractionManifest


class ExtractionManifestStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def save(self, manifest: ExtractionManifest) -> Path:
        payload = json.dumps(asdict(manifest), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        digest = sha256(payload).hexdigest()
        path = self.root / manifest.document_id / f"v{manifest.schema_version}-{digest}.json"
        if not path.exists():
            atomic_write(path, payload)
        elif path.read_bytes() != payload:
            raise RuntimeError("Extraction manifest integrity conflict")
        return path
