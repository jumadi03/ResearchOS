"""Filesystem cache for successful provider search pages."""

from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from app.architecture.persistence import atomic_write
from app.knowledge.discovery.normalization import canonical_json
from app.knowledge.discovery.providers import LiteratureProvider, ProviderPage
from app.knowledge.models import SearchPlan


class CachedProvider:
    def __init__(self, provider: LiteratureProvider, root: Path) -> None:
        self.provider = provider
        self.name = provider.name
        self.root = root

    def _path(self, plan: SearchPlan) -> Path:
        key = sha256(canonical_json(asdict(plan)).encode("utf-8")).hexdigest()
        return self.root / self.name / f"{key}.json"

    def search(self, plan: SearchPlan) -> tuple[ProviderPage, ...]:
        path = self._path(plan)
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            return tuple(
                ProviderPage(tuple(page["records"]), page["request_url"])
                for page in payload["pages"]
            )
        pages = self.provider.search(plan)
        payload = canonical_json(
            {
                "provider": self.name,
                "plan": asdict(plan),
                "pages": [
                    {"records": page.records, "request_url": page.request_url}
                    for page in pages
                ],
            }
        )
        atomic_write(path, payload)
        return pages
