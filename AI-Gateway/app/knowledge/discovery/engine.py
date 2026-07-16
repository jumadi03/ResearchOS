"""Orchestration for provider-independent literature discovery."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from uuid import uuid4

from app.knowledge.discovery.deduplication import deduplicate
from app.knowledge.discovery.normalization import normalize
from app.knowledge.discovery.providers import LiteratureProvider, ProviderError
from app.knowledge.discovery.source_registry import CanonicalSourceRegistry
from app.knowledge.models import (
    DiscoveryContract, DiscoveryRun, ProviderFailure, ScientificQuestion,
    SearchPlan,
)


class LiteratureDiscoveryEngine:
    def __init__(
        self,
        providers: Iterable[LiteratureProvider],
        *,
        clock: Callable[[], str] = DiscoveryRun.timestamp,
        run_id_factory: Callable[[], str] = lambda: f"discovery-{uuid4().hex}",
        raw_page_store=None,
        source_registry: CanonicalSourceRegistry | None = None,
    ) -> None:
        provider_items = tuple(providers)
        self._source_registry = (
            source_registry
            or CanonicalSourceRegistry.for_providers(provider_items)
        )
        self._providers = {
            provider.name: provider for provider in provider_items
        }
        self._clock = clock
        self._run_id_factory = run_id_factory
        self._raw_page_store = raw_page_store

    def discover(
        self, question: ScientificQuestion, contract: DiscoveryContract,
        plan: SearchPlan,
    ) -> DiscoveryRun:
        contract.validate_binding(question, plan)
        source_definitions = self._source_registry.resolve(plan, contract)
        started_at = self._clock()
        run_id = self._run_id_factory()
        records = []
        failures = []
        for provider_name in plan.providers:
            provider = self._providers.get(provider_name)
            if provider is None:
                failures.append(ProviderFailure(provider_name, "ProviderNotConfigured", "Provider is not configured", False))
                continue
            try:
                pages = provider.search(plan)
                if hasattr(pages, "records"):
                    pages = (pages,)
                for page_number, page in enumerate(pages, start=1):
                    page_hash = None
                    if self._raw_page_store is not None:
                        page_hash = self._raw_page_store.save(
                            run_id, provider_name, page_number, page,
                        )
                    records.extend(
                        normalize(provider_name, raw, started_at, response_hash=page_hash)
                        for raw in page.records
                    )
            except (ProviderError, ValueError, KeyError, TypeError) as exc:
                failures.append(
                    ProviderFailure(
                        provider_name,
                        type(exc).__name__,
                        str(exc),
                        getattr(exc, "retryable", False),
                    )
                )
        return DiscoveryRun(
            run_id=run_id, question=question, discovery_contract=contract,
            source_definitions=source_definitions, search_plan=plan,
            started_at=started_at, records=deduplicate(tuple(records)),
            failures=tuple(failures),
        )

    @property
    def source_definitions(self):
        return self._source_registry.definitions
