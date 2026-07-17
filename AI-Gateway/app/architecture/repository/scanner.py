"""Read-only, content-addressed tracked-file scanner for FMA-001."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Iterable

from .classifier import RepositoryClassifier
from .models import RepositoryFileRecord, RepositoryInventory


class RepositoryScanner:
    """Build a deterministic inventory from an injected tracked-file list."""

    def __init__(
        self, root: Path, classifier: RepositoryClassifier | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.classifier = classifier or RepositoryClassifier()

    @staticmethod
    def _normalize(value: str | Path) -> str:
        raw = str(value).replace("\\", "/")
        path = PurePosixPath(raw)
        if path.is_absolute() or not raw or any(
            part in {"", ".", ".."} for part in path.parts
        ):
            raise ValueError(f"Unsafe repository-relative path: {value}")
        return path.as_posix()

    def _resolve_file(self, relative_path: str) -> Path:
        target = self.root.joinpath(*PurePosixPath(relative_path).parts)
        unresolved = self.root
        for part in PurePosixPath(relative_path).parts:
            unresolved = unresolved / part
            if unresolved.is_symlink():
                raise ValueError(
                    f"Symbolic links are not inventory sources: {relative_path}"
                )
        resolved = target.resolve(strict=True)
        try:
            resolved.relative_to(self.root)
        except ValueError as exc:
            raise ValueError(
                f"Repository path escapes scan root: {relative_path}"
            ) from exc
        if not resolved.is_file():
            raise ValueError(f"Repository path is not a file: {relative_path}")
        return resolved

    def _record(self, relative_path: str) -> RepositoryFileRecord:
        target = self._resolve_file(relative_path)
        before = target.stat()
        content = target.read_bytes()
        after = target.stat()
        if (
            before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns
            or len(content) != after.st_size
        ):
            raise RuntimeError(
                f"Repository file changed during inventory: {relative_path}"
            )
        classification, reason = self.classifier.classify(relative_path)
        return RepositoryFileRecord(
            path=relative_path,
            classification=classification,
            size=len(content),
            sha256=sha256(content).hexdigest(),
            extension=PurePosixPath(relative_path).suffix.lower(),
            tracked=True,
            classification_reason=reason,
        )

    def scan(
        self, tracked_paths: Iterable[str | Path], *,
        project_name: str, source_revision: str,
    ) -> RepositoryInventory:
        if not project_name.strip() or not source_revision.strip():
            raise ValueError("Project name and source revision are required")
        normalized = tuple(self._normalize(item) for item in tracked_paths)
        if not normalized:
            raise ValueError("A repository inventory cannot be empty")
        if len(set(normalized)) != len(normalized):
            raise ValueError("Duplicate repository paths are not allowed")
        inventory = RepositoryInventory(
            inventory_id="",
            project_name=project_name,
            source_revision=source_revision,
            files=tuple(self._record(item) for item in sorted(normalized)),
        ).finalized()
        if not inventory.verify():
            raise ValueError("Repository inventory integrity verification failed")
        return inventory
