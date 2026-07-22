"""Immutable publication package persistence."""

from dataclasses import asdict
import json
from pathlib import Path

from app.architecture.persistence import atomic_write
from app.knowledge.publication.models import (
    CitationVerification, PublicationKind, PublicationManifest, PublicationPackage,
    PublicationRelationship, PublicationRelationType,
)


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

    def load_all(self) -> tuple[PublicationPackage, ...]:
        if not self.root.exists():
            return ()
        packages = []
        for directory in sorted(path for path in self.root.iterdir() if path.is_dir()):
            markdown_path = directory / "publication.md"
            manifest_path = directory / "manifest.json"
            if not markdown_path.exists() or not manifest_path.exists():
                continue
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
            item = raw["manifest"]
            citation = item["citation_verification"]
            package = PublicationPackage(
                PublicationManifest(
                    item["publication_id"], PublicationKind(item["kind"]),
                    item["generated_at"], item["generated_by"],
                    item["theory_bundle_id"], item["theory_bundle_hash"],
                    item["validation_report_id"], item["validation_report_hash"],
                    item["validation_status"], item["engine_version"],
                    item["markdown_hash"], CitationVerification(
                        tuple(citation["cited_evidence_ids"]),
                        tuple(citation["available_evidence_ids"]),
                        tuple(citation["unresolved_citations"]),
                        citation["verified"],
                    ), item.get("schema_version", "1.0"),
                ),
                markdown_path.read_text(encoding="utf-8"),
                raw["package_content_hash"],
            )
            if not package.verify():
                raise ValueError(
                    f"Publication package integrity verification failed: {directory.name}"
                )
            packages.append(package)
        return tuple(packages)


class PublicationRelationshipStore:
    def __init__(self, root: Path) -> None: self.root = root

    def save(self, item: PublicationRelationship) -> Path:
        if not item.verify():
            raise ValueError("Publication relationship integrity verification failed")
        path = self.root / f"{item.relationship_id}.json"
        payload = json.dumps(asdict(item), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if path.exists():
            if path.read_text(encoding="utf-8") != payload:
                raise FileExistsError("Publication relationship is immutable")
            return path
        atomic_write(path, payload)
        return path

    def load_all(self) -> tuple[PublicationRelationship, ...]:
        if not self.root.exists(): return ()
        items = []
        for path in sorted(self.root.glob("*.json")):
            raw = json.loads(path.read_text(encoding="utf-8"))
            item = PublicationRelationship(
                raw["relationship_id"], raw["source_publication_id"],
                PublicationRelationType(raw["relation_type"]),
                raw.get("target_publication_id"), raw["actor_id"],
                raw["rationale"], raw["occurred_at"], raw["content_hash"],
                raw.get("schema_version", "1.0"),
            )
            if not item.verify():
                raise ValueError(f"Publication relationship integrity failed: {path.name}")
            items.append(item)
        return tuple(items)
