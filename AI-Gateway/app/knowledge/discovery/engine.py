"""Orchestration for provider-independent literature discovery."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from uuid import uuid4

from app.knowledge.discovery.deduplication import deduplicate
from app.knowledge.discovery.normalization import normalize
from app.knowledge.discovery.providers import LiteratureProvider, ProviderError
from app.knowledge.discovery.source_registry import CanonicalSourceRegistry
from app.knowledge.models import (
    DiscoveryContract, DiscoveryRun, ProviderEnumeration, ProviderFailure,
    ScientificQuestion, SearchPlan,
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
        plan.validate_planned()
        source_definitions = self._source_registry.resolve(plan, contract)
        source_ids = {
            item.name: item.source_id for item in source_definitions
        }
        if any(
            source_ids.get(item.provider) != item.source_id
            for item in plan.source_queries
        ):
            raise ValueError(
                "Source query does not match canonical source definition"
            )
        started_at = self._clock()
        run_id = self._run_id_factory()
        records = []
        failures = []
        enumerations = []
        source_by_provider = {
            item.name: item for item in source_definitions
        }
        query_by_provider = {
            item.provider: item for item in plan.source_queries
        }
        for provider_name in plan.providers:
            provider = self._providers.get(provider_name)
            if provider is None:
                failures.append(ProviderFailure(provider_name, "ProviderNotConfigured", "Provider is not configured", False))
                continue
            try:
                pages = provider.search(plan)
                if hasattr(pages, "records"):
                    pages = (pages,)
                rank = 0
                totals = []
                for page_number, page in enumerate(pages, start=1):
                    if page.total_results is not None:
                        totals.append(page.total_results)
                    page_hash = None
                    if self._raw_page_store is not None:
                        page_hash = self._raw_page_store.save(
                            run_id, provider_name, page_number, page,
                        )
                    for raw in page.records:
                        rank += 1
                        records.append(normalize(
                            provider_name, raw, started_at,
                            response_hash=page_hash,
                            source_definition_id=source_by_provider[
                                provider_name
                            ].source_id,
                            query_family_id=query_by_provider[
                                provider_name
                            ].family_id,
                            source_query=query_by_provider[
                                provider_name
                            ].query,
                            discovery_rank=rank, page_number=page_number,
                            request_url=page.request_url,
                        ))
                total_available = max(totals) if totals else None
                enumerations.append(ProviderEnumeration(
                    provider_name,
                    source_by_provider[provider_name].source_id,
                    query_by_provider[provider_name].family_id,
                    plan.limit_per_provider, rank, total_available,
                    len(pages),
                    (
                        total_available > rank
                        if total_available is not None
                        else rank == plan.limit_per_provider
                    ),
                ))
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
            started_at=started_at, enumerations=tuple(enumerations),
            records=deduplicate(tuple(records)),
            failures=tuple(failures),
        )

    @property
    def source_definitions(self):
        return self._source_registry.definitions

    def resolve_sources(self, plan, contract):
        return self._source_registry.resolve(plan, contract)
