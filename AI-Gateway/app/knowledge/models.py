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
class ScientificQuestion:
    question_id: str
    text: str
    phenomenon_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "question_id", _required(self.question_id, "question_id"))
        object.__setattr__(self, "text", _required(self.text, "text"))


@dataclass(frozen=True, slots=True)
class SearchPlan:
    plan_id: str
    query: str
    providers: tuple[str, ...]
    limit_per_provider: int = 25
    year_from: int | None = None
    year_to: int | None = None

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
    search_plan: SearchPlan
    started_at: str
    records: tuple[LiteratureRecord, ...]
    failures: tuple[ProviderFailure, ...] = ()
    schema_version: str = "1.0"

    @classmethod
    def timestamp(cls) -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
