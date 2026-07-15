"""Immutable publication package persistence."""

from dataclasses import asdict
import json
from pathlib import Path

from app.architecture.persistence import atomic_write
from app.knowledge.publication.models import PublicationPackage


class PublicationStore:
    def __init__(self, root: Path) -> None: self.root = root

    def save(self, package: PublicationPackage) -> Path:
        if not package.verify(): raise ValueError("Publication package integrity verification failed")
        root = self.root / package.manifest.publication_id
        markdown = root / "publication.md"
        manifest = root / "manifest.json"
        manifest_payload = json.dumps(
            {"manifest": asdict(package.manifest), "package_content_hash": package.content_hash},
            ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        )
        if markdown.exists() or manifest.exists():
            if markdown.read_text(encoding="utf-8") != package.markdown or manifest.read_text(encoding="utf-8") != manifest_payload:
                raise FileExistsError("Released publication package is immutable")
            return root
        atomic_write(markdown, package.markdown)
        atomic_write(manifest, manifest_payload)
        return root
