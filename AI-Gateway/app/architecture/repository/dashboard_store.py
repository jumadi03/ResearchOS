"""Transactional publication and rehydration for repository dashboard artifacts."""

from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
from uuid import uuid4

from app.architecture.models import ArchitectureGraph
from app.architecture.persistence import (
    InterProcessFileLock,
    atomic_write,
    remove_internal_temporary_entries,
)

from .dashboard_models import RepositoryDashboardSnapshot
from .dashboard_projector import RepositoryDashboardProjector
from .file_registry_models import RepositoryFileRegistry
from .health_models import RepositoryHealthReport
from .verification_models import RepositoryVerificationReport


class RepositoryDashboardArtifactStore:
    """Publish complete immutable bundles and expose one verified active source."""

    _FILES = {
        "registry": "file-registry.json",
        "verification": "verification-report.json",
        "graph": "architecture-graph.json",
        "health": "health-report.json",
        "dashboard": "dashboard-snapshot.json",
    }

    def __init__(
        self,
        root: Path,
        *,
        expected_revision: str | None = None,
    ) -> None:
        self.root = root.resolve()
        self.expected_revision = expected_revision
        self.recovered_temporary_entries = remove_internal_temporary_entries(
            self.root
        )

    def _lock(self) -> InterProcessFileLock:
        return InterProcessFileLock(self.root / ".dashboard.lock")

    @property
    def _pointer_path(self) -> Path:
        return self.root / "active.json"

    def _release_directory(self, content_hash: str) -> Path:
        if len(content_hash) != 64 or any(
            character not in "0123456789abcdef" for character in content_hash
        ):
            raise ValueError("Repository dashboard release hash is invalid")
        return self.root / "releases" / content_hash

    @staticmethod
    def _pointer(
        snapshot: RepositoryDashboardSnapshot,
    ) -> dict[str, str]:
        payload = {
            "schema_version": "1.0",
            "snapshot_id": snapshot.snapshot_id,
            "content_hash": snapshot.content_hash,
            "source_revision": snapshot.source_revision,
        }
        pointer_hash = sha256(json.dumps(
            payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True,
        ).encode("utf-8")).hexdigest()
        return {**payload, "pointer_hash": pointer_hash}

    @staticmethod
    def _verify_pointer(payload: dict[str, object]) -> bool:
        if set(payload) != {
            "schema_version", "snapshot_id", "content_hash",
            "source_revision", "pointer_hash",
        }:
            return False
        candidate = {
            key: payload[key] for key in (
                "schema_version", "snapshot_id", "content_hash",
                "source_revision",
            )
        }
        expected = sha256(json.dumps(
            candidate, ensure_ascii=False, separators=(",", ":"), sort_keys=True,
        ).encode("utf-8")).hexdigest()
        return (
            payload["schema_version"] == "1.0"
            and isinstance(payload["snapshot_id"], str)
            and str(payload["snapshot_id"]).startswith("repository-dashboard:")
            and isinstance(payload["content_hash"], str)
            and isinstance(payload["source_revision"], str)
            and bool(str(payload["source_revision"]).strip())
            and payload["pointer_hash"] == expected
        )

    def _read_release(
        self,
        content_hash: str,
    ) -> tuple[
        RepositoryFileRegistry,
        RepositoryVerificationReport,
        ArchitectureGraph,
        RepositoryHealthReport,
        RepositoryDashboardSnapshot,
    ]:
        directory = self._release_directory(content_hash)
        try:
            registry = RepositoryFileRegistry.from_json(
                (directory / self._FILES["registry"]).read_text(encoding="utf-8")
            )
            verification = RepositoryVerificationReport.from_json(
                (directory / self._FILES["verification"]).read_text(
                    encoding="utf-8"
                )
            )
            graph = ArchitectureGraph.from_json(
                (directory / self._FILES["graph"]).read_text(encoding="utf-8")
            )
            health = RepositoryHealthReport.from_json(
                (directory / self._FILES["health"]).read_text(encoding="utf-8")
            )
            snapshot = RepositoryDashboardSnapshot.from_json(
                (directory / self._FILES["dashboard"]).read_text(
                    encoding="utf-8"
                )
            )
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError(
                "Repository dashboard release is incomplete or invalid"
            ) from exc
        projected = RepositoryDashboardProjector().project(
            registry, verification, graph, health,
        )
        if projected != snapshot or snapshot.content_hash != content_hash:
            raise ValueError("Repository dashboard release provenance mismatch")
        return registry, verification, graph, health, snapshot

    def publish(
        self,
        registry: RepositoryFileRegistry,
        verification: RepositoryVerificationReport,
        graph: ArchitectureGraph,
        health: RepositoryHealthReport,
    ) -> RepositoryDashboardSnapshot:
        snapshot = RepositoryDashboardProjector().project(
            registry, verification, graph, health,
        )
        release = self._release_directory(snapshot.content_hash)
        with self._lock():
            if release.exists():
                existing = self._read_release(snapshot.content_hash)[-1]
                if existing != snapshot:
                    raise FileExistsError(
                        "Repository dashboard immutable release conflict"
                    )
            else:
                release.parent.mkdir(parents=True, exist_ok=True)
                staging = release.parent / f".tmp-dashboard-{uuid4().hex}"
                staging.mkdir()
                try:
                    atomic_write(
                        staging / self._FILES["registry"], registry.to_json()
                    )
                    atomic_write(
                        staging / self._FILES["verification"],
                        verification.to_json(),
                    )
                    atomic_write(staging / self._FILES["graph"], graph.to_json())
                    atomic_write(
                        staging / self._FILES["health"], health.to_json()
                    )
                    atomic_write(
                        staging / self._FILES["dashboard"], snapshot.to_json()
                    )
                    os.replace(staging, release)
                    self._read_release(snapshot.content_hash)
                finally:
                    remove_internal_temporary_entries(release.parent)
            atomic_write(
                self._pointer_path,
                json.dumps(
                    self._pointer(snapshot),
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                ),
            )
        return snapshot

    def _active(
        self,
    ) -> tuple[
        RepositoryFileRegistry,
        RepositoryVerificationReport,
        ArchitectureGraph,
        RepositoryHealthReport,
        RepositoryDashboardSnapshot,
    ]:
        try:
            pointer = json.loads(self._pointer_path.read_text(encoding="utf-8"))
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError(
                "Repository dashboard active pointer is unavailable or invalid"
            ) from exc
        if not isinstance(pointer, dict) or not self._verify_pointer(pointer):
            raise ValueError("Repository dashboard active pointer is invalid")
        release = self._read_release(str(pointer["content_hash"]))
        snapshot = release[-1]
        if (
            snapshot.snapshot_id != pointer["snapshot_id"]
            or snapshot.content_hash != pointer["content_hash"]
            or snapshot.source_revision != pointer["source_revision"]
        ):
            raise ValueError("Repository dashboard active pointer provenance mismatch")
        if (
            self.expected_revision is not None
            and snapshot.source_revision != self.expected_revision
        ):
            raise ValueError(
                "Repository dashboard active snapshot revision is stale"
            )
        return release

    def load(
        self,
    ) -> tuple[
        RepositoryFileRegistry,
        RepositoryVerificationReport,
        ArchitectureGraph,
        RepositoryHealthReport,
    ]:
        registry, verification, graph, health, _ = self._active()
        return registry, verification, graph, health

    def snapshot(self) -> RepositoryDashboardSnapshot:
        return self._active()[-1]
