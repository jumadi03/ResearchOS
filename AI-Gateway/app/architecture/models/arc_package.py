"""Architecture Review & Compliance package models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from hashlib import sha256
import json
from pathlib import Path
from ..schema import ARC_MIGRATIONS, ARC_SCHEMA


@dataclass(frozen=True, slots=True)
class ARCManifest:
    """Content-addressed manifest for one released ARC package."""

    arc_id: str
    project_name: str
    generated_at: str
    graph_id: str
    graph_hash: str
    source_revision: str | None
    law_bundle_id: str
    law_bundle_hash: str
    compliance_hash: str
    review_id: str
    review_hash: str
    generated_by: str = "system"
    artifact_checksums: dict[str, str] = field(default_factory=dict)
    schema_version: str = "1.1"
    manifest_hash: str = ""

    def canonical_payload(self) -> dict[str, object]:
        payload = asdict(self)
        payload.pop("arc_id")
        payload.pop("manifest_hash")
        if self.schema_version == "1.0":
            payload.pop("generated_by")
        return payload

    def calculate_content_hash(self) -> str:
        encoded = json.dumps(
            self.canonical_payload(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return sha256(encoded).hexdigest()

    def finalized(self) -> ARCManifest:
        manifest_hash = self.calculate_content_hash()
        return replace(
            self,
            arc_id=f"arc:{self.project_name}:{manifest_hash[:16]}",
            manifest_hash=manifest_hash,
        )

    def to_json(self, *, indent: int | None = 2) -> str:
        payload = asdict(self)
        if self.schema_version == "1.0":
            payload.pop("generated_by")
        return json.dumps(payload, ensure_ascii=False, indent=indent, sort_keys=True)

    @classmethod
    def from_json(cls, value: str) -> "ARCManifest":
        payload = json.loads(value)
        schema_version = payload.get("schema_version", "1.0")
        ARC_SCHEMA.require_readable(schema_version)
        payload.setdefault("generated_by", "legacy:unknown")
        manifest = cls(**payload)
        if manifest.calculate_content_hash() != manifest.manifest_hash:
            raise ValueError("ARC manifest content hash is invalid")
        if manifest.finalized().arc_id != manifest.arc_id:
            raise ValueError("ARC manifest identifier is invalid")
        return manifest

    def upgraded(self, *, generated_by: str) -> "ARCManifest":
        """Issue a new current-schema manifest without mutating the release."""
        payload = ARC_MIGRATIONS.migrate(
            asdict(self), source_version=self.schema_version
        )
        payload.update(
            {
                "arc_id": "",
                "manifest_hash": "",
                "generated_by": generated_by,
            }
        )
        return ARCManifest(**payload).finalized()


@dataclass(frozen=True, slots=True)
class ARCPackage:
    """In-memory ARC package ready for persistence or publication."""

    manifest: ARCManifest
    artifacts: dict[str, str | bytes]

    @staticmethod
    def _bytes(content: str | bytes) -> bytes:
        return content if isinstance(content, bytes) else content.encode("utf-8")

    def verify(self) -> bool:
        """Verify manifest identity and every payload checksum."""
        if self.manifest.calculate_content_hash() != self.manifest.manifest_hash:
            return False
        if self.manifest.finalized().arc_id != self.manifest.arc_id:
            return False
        if set(self.artifacts) != set(self.manifest.artifact_checksums):
            return False
        return all(
            sha256(self._bytes(content)).hexdigest()
            == self.manifest.artifact_checksums[name]
            for name, content in self.artifacts.items()
        )

    def all_files(self) -> dict[str, str | bytes]:
        """Return payload plus manifest and a standalone checksum index."""
        checksums = json.dumps(
            self.manifest.artifact_checksums,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        return {
            **self.artifacts,
            "manifest.json": self.manifest.to_json(),
            "checksums.json": checksums,
        }

    def write_to(self, directory: Path, *, overwrite: bool = False) -> tuple[Path, ...]:
        """Persist a verified package without silently replacing prior ARC data."""
        if not self.verify():
            raise ValueError("Cannot persist an ARC package that fails verification")
        directory.mkdir(parents=True, exist_ok=True)
        files = self.all_files()
        targets = tuple(directory / name for name in sorted(files))
        existing = tuple(path for path in targets if path.exists())
        if existing and not overwrite:
            raise FileExistsError(
                "ARC output already exists: " + ", ".join(str(path) for path in existing)
            )
        for name, content in files.items():
            target = directory / name
            if isinstance(content, bytes):
                target.write_bytes(content)
            else:
                target.write_text(content, encoding="utf-8", newline="\n")
        return targets

    @classmethod
    def from_directory(cls, directory: Path) -> "ARCPackage":
        """Load a persisted package and reject missing, extra, or modified payloads."""
        manifest = ARCManifest.from_json(
            (directory / "manifest.json").read_text(encoding="utf-8")
        )
        checksum_index = json.loads(
            (directory / "checksums.json").read_text(encoding="utf-8")
        )
        if checksum_index != manifest.artifact_checksums:
            raise ValueError("ARC checksum index does not match the manifest")
        allowed = {*manifest.artifact_checksums, "manifest.json", "checksums.json"}
        actual = {path.name for path in directory.iterdir() if path.is_file()}
        if actual != allowed:
            raise ValueError("ARC package file set does not match the manifest")
        artifacts: dict[str, str | bytes] = {}
        for name in manifest.artifact_checksums:
            path = directory / name
            artifacts[name] = (
                path.read_bytes() if path.suffix.lower() == ".pdf"
                else path.read_text(encoding="utf-8")
            )
        package = cls(manifest=manifest, artifacts=artifacts)
        if not package.verify():
            raise ValueError("Persisted ARC package failed verification")
        return package
