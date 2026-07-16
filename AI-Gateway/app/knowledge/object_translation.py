"""Source-bound bilingual representations for scientific object titles."""

from dataclasses import asdict, dataclass, replace
from hashlib import sha256
import json
from pathlib import Path

from app.architecture.persistence import atomic_write


@dataclass(frozen=True, slots=True)
class ObjectTranslation:
    translation_id: str
    project_id: str
    object_id: str
    source_text: str
    source_hash: str
    translated_text: str
    provider: str
    model: str
    generated_by: str
    generated_at: str
    status: str = "advisory"
    reviewer: str | None = None
    rationale: str | None = None
    reviewed_at: str | None = None
    content_hash: str = ""

    def finalized(self):
        payload = asdict(self); payload["content_hash"] = ""
        digest = sha256(json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()).hexdigest()
        return ObjectTranslation(**{**payload, "content_hash": digest})

    def verify(self):
        return bool(self.content_hash) and self.finalized().content_hash == self.content_hash

    @staticmethod
    def source_digest(text):
        return sha256(text.encode("utf-8")).hexdigest()


class ObjectTranslationStore:
    def __init__(self, root: Path):
        self.root = root

    def save(self, item):
        if not item.verify():
            raise ValueError("Object translation integrity verification failed")
        path = self.root / item.translation_id / f"{item.status}-{item.content_hash}.json"
        payload = json.dumps(
            asdict(item), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
        if not path.exists():
            atomic_write(path, payload)
        return path

    def load_all(self):
        if not self.root.exists():
            return ()
        items = []
        for directory in self.root.iterdir():
            paths = tuple(directory.glob("*.json"))
            if not paths:
                continue
            path = max(paths, key=lambda value: (
                value.name.startswith("reviewed-"), value.stat().st_mtime_ns,
            ))
            item = ObjectTranslation(**json.loads(path.read_text(encoding="utf-8")))
            if not item.verify():
                raise ValueError(f"Object translation integrity failed: {path.name}")
            items.append(item)
        return tuple(items)
