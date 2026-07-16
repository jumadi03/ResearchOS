"""Immutable, source-bound theory translation representations."""

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path

from app.architecture.persistence import atomic_write


@dataclass(frozen=True, slots=True)
class TheoryTranslation:
    translation_id: str
    bundle_id: str
    theory_id: str
    source_language: str
    target_language: str
    source_statement: str
    source_hash: str
    translated_statement: str
    provider: str
    model: str
    generated_by: str
    generated_at: str
    status: str = "advisory"
    reviewer: str | None = None
    review_rationale: str | None = None
    reviewed_at: str | None = None
    content_hash: str = ""

    def finalized(self):
        payload = asdict(self)
        payload["content_hash"] = ""
        digest = sha256(json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()).hexdigest()
        return TheoryTranslation(**{**payload, "content_hash": digest})

    def verify(self):
        return bool(self.content_hash) and self.finalized().content_hash == self.content_hash

    @staticmethod
    def hash_source(statement: str) -> str:
        return sha256(statement.encode("utf-8")).hexdigest()


class TheoryTranslationStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def save(self, item: TheoryTranslation) -> Path:
        if not item.verify():
            raise ValueError("Theory translation integrity verification failed")
        path = self.root / item.translation_id / f"{item.status}-{item.content_hash}.json"
        payload = json.dumps(
            asdict(item), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
        if not path.exists():
            atomic_write(path, payload)
        elif path.read_bytes() != payload:
            raise RuntimeError("Theory translation snapshot conflict")
        return path

    def load_all(self) -> tuple[TheoryTranslation, ...]:
        if not self.root.exists():
            return ()
        items = []
        for directory in sorted(path for path in self.root.iterdir() if path.is_dir()):
            snapshots = tuple(directory.glob("*.json"))
            if not snapshots:
                continue
            path = max(snapshots, key=lambda item: (
                item.name.startswith("reviewed-"), item.stat().st_mtime_ns,
            ))
            item = TheoryTranslation(**json.loads(path.read_text(encoding="utf-8")))
            if not item.verify():
                raise ValueError(f"Theory translation snapshot integrity failed: {path.name}")
            items.append(item)
        return tuple(items)
