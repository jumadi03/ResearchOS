"""Content-addressed portable source-inspection snapshots."""

from dataclasses import asdict
import json
from pathlib import Path

from app.architecture.persistence import atomic_write
from app.knowledge.inspection.models import (
    HeadingObservation, PageInspection, SourceInspection,
)


class SourceInspectionStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def save(self, inspection: SourceInspection) -> Path:
        if not inspection.verify():
            raise ValueError("Source inspection integrity verification failed")
        path = (
            self.root / inspection.document_id
            / f"v{inspection.schema_version}-{inspection.manifest_hash}.json"
        )
        payload = json.dumps(
            asdict(inspection), ensure_ascii=False, sort_keys=True,
            separators=(",", ":"),
        ).encode()
        if path.exists() and path.read_bytes() != payload:
            raise RuntimeError("Source inspection snapshot conflict")
        if not path.exists():
            atomic_write(path, payload)
        return path

    def load(self, path: Path) -> SourceInspection:
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["pages"] = tuple(
            PageInspection(
                page=item["page"],
                character_count=item["character_count"],
                text_hash=item["text_hash"],
                has_extractable_text=item["has_extractable_text"],
                headings=tuple(
                    HeadingObservation(**heading)
                    for heading in item["headings"]
                ),
            )
            for item in raw["pages"]
        )
        inspection = SourceInspection(**raw)
        if not inspection.verify():
            raise ValueError("Source inspection integrity verification failed")
        return inspection

    def find(
        self, document_id: str, document_content_hash: str,
        inspector_name: str, inspector_version: str,
    ) -> SourceInspection | None:
        directory = self.root / document_id
        if not directory.exists():
            return None
        for path in sorted(directory.glob("v*.json")):
            inspection = self.load(path)
            if (
                inspection.document_content_hash == document_content_hash
                and inspection.inspector_name == inspector_name
                and inspection.inspector_version == inspector_version
            ):
                return inspection
        return None
