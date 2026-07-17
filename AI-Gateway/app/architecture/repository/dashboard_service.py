"""Read-only service boundary for repository dashboard projections."""

from __future__ import annotations

from typing import Protocol

from app.architecture.models import ArchitectureGraph

from .dashboard_models import RepositoryDashboardSnapshot
from .dashboard_projector import RepositoryDashboardProjector
from .file_registry_models import RepositoryFileRegistry
from .health_models import RepositoryHealthReport
from .verification_models import RepositoryVerificationReport


class RepositoryDashboardSource(Protocol):
    """Injected canonical source; persistence remains outside the dashboard."""

    def load(
        self,
    ) -> tuple[
        RepositoryFileRegistry,
        RepositoryVerificationReport,
        ArchitectureGraph,
        RepositoryHealthReport,
    ]: ...


class RepositoryDashboardService:
    """Expose only validated snapshots and no repository mutation methods."""

    def __init__(
        self,
        source: RepositoryDashboardSource,
        *,
        projector: RepositoryDashboardProjector | None = None,
    ) -> None:
        self._source = source
        self._projector = projector or RepositoryDashboardProjector()

    def snapshot(self) -> RepositoryDashboardSnapshot:
        registry, verification, graph, health = self._source.load()
        return self._projector.project(
            registry, verification, graph, health,
        )
