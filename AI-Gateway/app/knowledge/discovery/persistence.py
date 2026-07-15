"""Immutable, content-addressed discovery snapshots."""

from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from app.architecture.persistence import atomic_write
from app.knowledge.discovery.normalization import canonical_json
from app.knowledge.discovery.providers import ProviderPage
from app.knowledge.models import DiscoveryRun


def serialize_run(run: DiscoveryRun) -> bytes:
    return json.dumps(
        asdict(run), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


class DiscoverySnapshotStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def save(self, run: DiscoveryRun) -> Path:
        payload = serialize_run(run)
        digest = sha256(payload).hexdigest()
        path = self.root / run.run_id / f"discovery-{digest}.json"
        if path.exists():
            if path.read_bytes() != payload:
                raise RuntimeError("Discovery snapshot integrity conflict")
            return path
        atomic_write(path, payload)
        return path


class RawPageStore:
    """Persist immutable provider pages before normalization."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def save(
        self, run_id: str, provider: str, page_number: int, page: ProviderPage
    ) -> str:
        payload = canonical_json(
            {"provider": provider, "request_url": page.request_url, "records": page.records}
        ).encode("utf-8")
        digest = sha256(payload).hexdigest()
        path = self.root / run_id / "raw" / provider / f"page-{page_number:05d}-{digest}.json"
        if path.exists() and path.read_bytes() != payload:
            raise RuntimeError("Raw provider page integrity conflict")
        if not path.exists():
            atomic_write(path, payload)
        return digest
