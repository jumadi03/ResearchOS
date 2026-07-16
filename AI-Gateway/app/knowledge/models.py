"""Canonical contracts for literature discovery (SK-001A)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


def _required(value: str, name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must not be empty")
    return normalized


class MatchKind(StrEnum):
    """Confidence class for a group of source records."""

    EXACT = "exact"
    POSSIBLE = "possible"
    UNIQUE = "unique"


@dataclass(frozen=True, slots=True)
class SourceDefinition:
    source_id: str
    name: str
    source_type: str
    base_url: str
    access_method: str
    authority_level: str
    disciplines: tuple[str, ...]
    authentication: str
    rate_limit_policy: str
    robots_policy: str
    license_policy: str
    content_types: tuple[str, ...]
    trust_profile: str
    status: str

    def __post_init__(self) -> None:
        for field_name in (
            "source_id", "name", "source_type", "base_url",
            "access_method", "authority_level", "authentication",
            "rate_limit_policy", "robots_policy", "license_policy",
            "trust_profile", "status",
        ):
            object.__setattr__(
                self, field_name,
                _required(getattr(self, field_name), field_name),
            )
        normalized_name = self.name.casefold()
        object.__setattr__(self, "name", normalized_name)
        if not self.base_url.startswith("https://"):
            raise ValueError("base_url must use HTTPS")
        if self.authority_level not in {"A1", "A2", "B1", "B2", "C1", "C2"}:
            raise ValueError("authority_level is not recognized")
        if self.status not in {"active", "inactive"}:
            raise ValueError("source status is not recognized")
        for field_name in ("disciplines", "content_types"):
            values = tuple(dict.fromkeys(
                item.strip().casefold()
                for item in getattr(self, field_name) if item.strip()
            ))
            if not values:
                raise ValueError(f"{field_name} must not be empty")
            object.__setattr__(self, field_name, values)


@dataclass(frozen=True, slots=True)
class ScientificQuestion:
    question_id: str
    text: str
    phenomenon_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "question_id", _required(self.question_id, "question_id"))
        object.__setattr__(self, "text", _required(self.text, "text"))


@dataclass(frozen=True, slots=True)
class DiscoveryContract:
    contract_id: str
    project_id: str
    research_question_id: str
    search_plan_id: str
    scope: str
    source_categories: tuple[str, ...]
    inclusion_rules: tuple[str, ...]
    exclusion_rules: tuple[str, ...]
    languages: tuple[str, ...]
    document_types: tuple[str, ...]
    evidence_types: tuple[str, ...]
    maximum_depth: int
    retrieval_budget: int
    license_policy: str
    human_review_policy: str
    stopping_conditions: tuple[str, ...]
    year_from: int | None = None
    year_to: int | None = None

    def __post_init__(self) -> None:
        for name in (
            "contract_id", "project_id", "research_question_id",
            "search_plan_id", "scope", "license_policy",
            "human_review_policy",
        ):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        for name in (
            "source_categories", "inclusion_rules", "exclusion_rules",
            "languages", "document_types", "evidence_types",
            "stopping_conditions",
        ):
            values = tuple(dict.fromkeys(
                item.strip() for item in getattr(self, name) if item.strip()
            ))
            if not values:
                raise ValueError(f"{name} must not be empty")
            object.__setattr__(self, name, values)
        if not 1 <= self.maximum_depth <= 10:
            raise ValueError("maximum_depth must be between 1 and 10")
        if not 1 <= self.retrieval_budget <= 100_000:
            raise ValueError(
                "retrieval_budget must be between 1 and 100000"
            )
        if self.year_from and self.year_to and self.year_from > self.year_to:
            raise ValueError("year_from must not exceed year_to")

    def validate_binding(
        self, question: "ScientificQuestion", plan: "SearchPlan",
    ) -> None:
        if self.research_question_id != question.question_id:
            raise ValueError(
                "Discovery contract does not match research question"
            )
        if self.search_plan_id != plan.plan_id:
            raise ValueError("Discovery contract does not match search plan")
        if self.year_from != plan.year_from or self.year_to != plan.year_to:
            raise ValueError(
                "Discovery contract date range does not match search plan"
            )
        planned_retrievals = len(plan.providers) * plan.limit_per_provider
        if planned_retrievals > self.retrieval_budget:
            raise ValueError(
                "Search plan exceeds discovery contract retrieval budget"
            )


@dataclass(frozen=True, slots=True)
class QueryConcept:
    concept_id: str
    preferred_term: str
    synonyms: tuple[str, ...]
    disciplines: tuple[str, ...]
    attributed_by: str
    rationale: str

    def __post_init__(self) -> None:
        for name in (
            "concept_id", "preferred_term", "attributed_by", "rationale",
        ):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if any(not item.strip() for item in self.synonyms):
            raise ValueError("synonyms must not contain empty values")
        synonyms = tuple(item.strip() for item in self.synonyms)
        synonym_keys = tuple(item.casefold() for item in synonyms)
        if (
            len(set(synonym_keys)) != len(synonyms)
            or self.preferred_term.casefold() in synonym_keys
        ):
            raise ValueError("synonyms must be unique")
        disciplines = tuple(dict.fromkeys(
            item.strip().casefold() for item in self.disciplines
            if item.strip()
        ))
        if not disciplines:
            raise ValueError("disciplines must not be empty")
        object.__setattr__(self, "synonyms", synonyms)
        object.__setattr__(self, "disciplines", disciplines)


@dataclass(frozen=True, slots=True)
class QueryFamily:
    family_id: str
    concept_ids: tuple[str, ...]
    terms: tuple[str, ...]
    purpose: str


@dataclass(frozen=True, slots=True)
class SourceQuery:
    provider: str
    source_id: str
    family_id: str
    query: str


@dataclass(frozen=True, slots=True)
class SearchPlan:
    plan_id: str
    query: str
    providers: tuple[str, ...]
    limit_per_provider: int = 25
    year_from: int | None = None
    year_to: int | None = None
    concepts: tuple[QueryConcept, ...] = ()
    query_families: tuple[QueryFamily, ...] = ()
    source_queries: tuple[SourceQuery, ...] = ()
    planning_method: str = "manual-query-v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "plan_id", _required(self.plan_id, "plan_id"))
        object.__setattr__(self, "query", _required(self.query, "query"))
        normalized = tuple(dict.fromkeys(p.strip().lower() for p in self.providers if p.strip()))
        if not normalized:
            raise ValueError("providers must not be empty")
        if self.limit_per_provider < 1:
            raise ValueError("limit_per_provider must be positive")
        if self.year_from and self.year_to and self.year_from > self.year_to:
            raise ValueError("year_from must not exceed year_to")
        object.__setattr__(self, "providers", normalized)

    def query_for(self, provider: str) -> str:
        matches = tuple(
            item.query for item in self.source_queries
            if item.provider == provider
        )
        if len(matches) > 1:
            raise ValueError(
                f"Search plan has duplicate source queries: {provider}"
            )
        return matches[0] if matches else self.query

    def validate_planned(self) -> None:
        if self.planning_method != "scientific-query-planner-v1":
            raise ValueError(
                "Scientific Query Planner is required for discovery"
            )
        if not self.concepts or not self.query_families:
            raise ValueError(
                "Scientific query plan requires concepts and query families"
            )
        concept_ids_sequence = tuple(
            item.concept_id for item in self.concepts
        )
        if len(concept_ids_sequence) != len(set(concept_ids_sequence)):
            raise ValueError("Scientific query concept IDs must be unique")
        providers = tuple(item.provider for item in self.source_queries)
        if len(providers) != len(set(providers)):
            raise ValueError("Source queries must be unique by provider")
        if set(providers) != set(self.providers):
            raise ValueError(
                "Scientific query plan requires one query per provider"
            )
        family_ids = {item.family_id for item in self.query_families}
        if len(family_ids) != len(self.query_families):
            raise ValueError("Query family IDs must be unique")
        concept_ids = {item.concept_id for item in self.concepts}
        if any(
            not family.family_id.strip()
            or not family.purpose.strip()
            or not family.terms
            or not family.concept_ids
            or not set(family.concept_ids).issubset(concept_ids)
            for family in self.query_families
        ):
            raise ValueError("Query family provenance is incomplete")
        if any(item.family_id not in family_ids for item in self.source_queries):
            raise ValueError(
                "Source query is not bound to a query family"
            )
        if any(
            not item.source_id.strip() or not item.query.strip()
            for item in self.source_queries
        ):
            raise ValueError("Source query provenance is incomplete")


@dataclass(frozen=True, slots=True)
class SourceRecord:
    provider: str
    source_id: str
    retrieved_at: str
    response_hash: str
    raw: dict[str, Any] = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in ("provider", "source_id", "retrieved_at", "response_hash"):
            object.__setattr__(self, name, _required(getattr(self, name), name))


@dataclass(frozen=True, slots=True)
class LiteratureRecord:
    record_id: str
    title: str
    authors: tuple[str, ...]
    year: int | None
    doi: str | None
    abstract: str | None
    venue: str | None
    work_type: str | None
    source_records: tuple[SourceRecord, ...]
    match_kind: MatchKind = MatchKind.UNIQUE
    possible_matches: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ProviderFailure:
    provider: str
    error_type: str
    message: str
    retryable: bool


@dataclass(frozen=True, slots=True)
class DiscoveryRun:
    run_id: str
    question: ScientificQuestion
    discovery_contract: DiscoveryContract
    source_definitions: tuple[SourceDefinition, ...]
    search_plan: SearchPlan
    started_at: str
    records: tuple[LiteratureRecord, ...]
    failures: tuple[ProviderFailure, ...] = ()
    schema_version: str = "1.0"

    def __post_init__(self) -> None:
        self.validate_query_plan()

    def validate_query_plan(self) -> None:
        self.discovery_contract.validate_binding(
            self.question, self.search_plan,
        )
        self.search_plan.validate_planned()
        definitions = {
            item.name: item for item in self.source_definitions
        }
        if set(definitions) != set(self.search_plan.providers):
            raise ValueError(
                "Discovery run sources do not match search plan providers"
            )
        if any(
            definitions.get(item.provider) is None
            or definitions[item.provider].source_id != item.source_id
            for item in self.search_plan.source_queries
        ):
            raise ValueError(
                "Discovery run source query provenance is invalid"
            )

    @classmethod
    def timestamp(cls) -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
