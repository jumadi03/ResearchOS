"""Worker execution boundary for one contract-bound source watch."""

from pathlib import Path

from app.knowledge.discovery.engine import LiteratureDiscoveryEngine
from app.knowledge.discovery.persistence import DiscoverySnapshotStore, RawPageStore
from app.knowledge.discovery.providers import (
    CrossrefProvider, OpenAlexProvider, SemanticScholarProvider,
)
from app.knowledge.discovery.source_registry import CanonicalSourceRegistry
from app.knowledge.models import DiscoveryRun
from app.knowledge.monitoring.engine import ScientificMonitoringEngine
from app.knowledge.repositories.postgres import PostgresScientificDataRepository


def execute_source_watch(
    database_url: str, knowledge_root: Path, payload: dict, *,
    timeout: float, max_attempts: int, semantic_scholar_api_key: str | None,
) -> None:
    watch_id = payload.get("watch_id")
    scheduled_at = payload.get("scheduled_at")
    if not watch_id or not scheduled_at:
        raise ValueError("run_source_watch requires watch_id and scheduled_at")
    repository = PostgresScientificDataRepository(database_url)
    watch, baseline = repository.load_source_watch(watch_id)
    if watch.status.value != "active":
        raise ValueError("Scientific source watch is not active")
    providers = (
        OpenAlexProvider(timeout=timeout, max_attempts=max_attempts),
        CrossrefProvider(timeout=timeout, max_attempts=max_attempts),
        SemanticScholarProvider(
            api_key=semantic_scholar_api_key, timeout=timeout,
            max_attempts=max_attempts,
        ),
    )
    selected = tuple(
        item for item in providers if item.name in baseline.search_plan.providers
    )
    engine = LiteratureDiscoveryEngine(
        selected, raw_page_store=RawPageStore(knowledge_root / "runs"),
        source_registry=CanonicalSourceRegistry.for_providers(selected),
    )
    started_at = DiscoveryRun.timestamp()
    current = engine.discover(
        baseline.question, baseline.discovery_contract, baseline.search_plan,
    )
    repository.persist_discovery(current)
    DiscoverySnapshotStore(knowledge_root / "runs").save(current)
    monitoring = ScientificMonitoringEngine().compare(
        watch, baseline, current, scheduled_at=scheduled_at,
        started_at=started_at, completed_at=DiscoveryRun.timestamp(),
    )
    repository.persist_monitoring_run(watch, monitoring, current)
