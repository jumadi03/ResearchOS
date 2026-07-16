"""Canonical policy registry for scientific discovery sources."""

from collections.abc import Iterable

from app.knowledge.models import (
    DiscoveryContract, SearchPlan, SourceDefinition,
)


CANONICAL_SOURCE_DEFINITIONS = (
    SourceDefinition(
        "source-openalex", "openalex", "scholarly_index",
        "https://api.openalex.org/works", "official_api", "A2",
        ("multidisciplinary",), "none", "respect_retry_after",
        "api_terms_apply", "provider_metadata_terms",
        ("metadata", "abstract", "citations"),
        "curated_open_scholarly_index", "active",
    ),
    SourceDefinition(
        "source-crossref", "crossref", "scholarly_index",
        "https://api.crossref.org/works", "official_api", "A2",
        ("multidisciplinary",), "none", "respect_retry_after",
        "api_terms_apply", "provider_metadata_terms",
        ("metadata", "citations"),
        "doi_registration_agency_metadata", "active",
    ),
    SourceDefinition(
        "source-semantic-scholar", "semantic_scholar",
        "scholarly_index",
        "https://api.semanticscholar.org/graph/v1/paper/search",
        "official_api", "A2", ("multidisciplinary",),
        "optional_api_key", "respect_retry_after", "api_terms_apply",
        "provider_metadata_terms", ("metadata", "abstract", "citations"),
        "curated_scholarly_graph", "active",
    ),
)


class CanonicalSourceRegistry:
    def __init__(
        self, definitions: Iterable[SourceDefinition],
        providers: Iterable | None = None,
    ) -> None:
        items = tuple(definitions)
        by_name = {item.name: item for item in items}
        by_id = {item.source_id: item for item in items}
        if not items:
            raise ValueError("Canonical source registry must not be empty")
        if len(by_name) != len(items):
            raise ValueError("Canonical source name must be unique")
        if len(by_id) != len(items):
            raise ValueError("Canonical source ID must be unique")
        self._definitions = items
        self._by_name = by_name
        if providers is not None:
            for provider in providers:
                self.validate_provider(provider)

    @classmethod
    def for_providers(cls, providers: Iterable) -> "CanonicalSourceRegistry":
        provider_items = tuple(providers)
        return cls(CANONICAL_SOURCE_DEFINITIONS, provider_items)

    @property
    def definitions(self) -> tuple[SourceDefinition, ...]:
        return self._definitions

    def validate_provider(self, provider) -> SourceDefinition:
        name = str(getattr(provider, "name", "")).strip().casefold()
        definition = self._by_name.get(name)
        if definition is None:
            raise ValueError(
                f"Provider has no canonical source definition: {name or '<missing>'}"
            )
        provider_url = str(getattr(provider, "base_url", "")).strip()
        if provider_url and provider_url != definition.base_url:
            raise ValueError(
                f"Provider base URL does not match source definition: {name}"
            )
        return definition

    def resolve(
        self, plan: SearchPlan, contract: DiscoveryContract,
    ) -> tuple[SourceDefinition, ...]:
        allowed_categories = {
            item.strip().casefold() for item in contract.source_categories
        }
        resolved = []
        for provider_name in plan.providers:
            definition = self._by_name.get(provider_name)
            if definition is None:
                raise ValueError(
                    f"Source is not registered: {provider_name}"
                )
            if definition.status != "active":
                raise ValueError(f"Source is not active: {provider_name}")
            if definition.source_type.casefold() not in allowed_categories:
                raise ValueError(
                    f"Source category is not permitted by discovery contract: "
                    f"{provider_name}"
                )
            resolved.append(definition)
        return tuple(resolved)
