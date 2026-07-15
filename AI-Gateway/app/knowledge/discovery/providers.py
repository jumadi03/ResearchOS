"""Provider boundary and HTTP adapters for SK-001A."""

from __future__ import annotations

from dataclasses import dataclass
from time import sleep
from typing import Any, Callable, Protocol

import requests

from app.knowledge.models import SearchPlan


class ProviderError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


@dataclass(frozen=True, slots=True)
class ProviderPage:
    records: tuple[dict[str, Any], ...]
    request_url: str


class LiteratureProvider(Protocol):
    name: str

    def search(self, plan: SearchPlan) -> tuple[ProviderPage, ...]: ...


Transport = Callable[..., requests.Response]


class HttpProvider:
    name = ""
    base_url = ""

    def __init__(
        self, *, timeout: float = 20.0, transport: Transport = requests.get,
        max_attempts: int = 3, backoff_seconds: float = 0.25,
        sleeper: Callable[[float], None] = sleep,
    ) -> None:
        self.timeout = timeout
        self._transport = transport
        self.max_attempts = max_attempts
        self.backoff_seconds = backoff_seconds
        self._sleeper = sleeper

    def _get(self, params: dict[str, Any], headers: dict[str, str] | None = None) -> requests.Response:
        for attempt in range(1, self.max_attempts + 1):
            try:
                response = self._transport(
                    self.base_url, params=params, headers=headers or {}, timeout=self.timeout
                )
                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                status = getattr(exc.response, "status_code", None)
                retryable = status is None or status == 429 or status >= 500
                if not retryable or attempt == self.max_attempts:
                    raise ProviderError(str(exc), retryable=retryable) from exc
                retry_after = (
                    getattr(exc.response, "headers", {}).get("Retry-After")
                    if exc.response is not None else None
                )
                try:
                    delay = float(retry_after) if retry_after else self.backoff_seconds * attempt
                except ValueError:
                    delay = self.backoff_seconds * attempt
                self._sleeper(max(0.0, delay))
        raise AssertionError("retry loop exited unexpectedly")


class OpenAlexProvider(HttpProvider):
    name = "openalex"
    base_url = "https://api.openalex.org/works"

    def search(self, plan: SearchPlan) -> tuple[ProviderPage, ...]:
        filters = []
        if plan.year_from:
            filters.append(f"from_publication_date:{plan.year_from}-01-01")
        if plan.year_to:
            filters.append(f"to_publication_date:{plan.year_to}-12-31")
        page_size = min(plan.limit_per_provider, 200)
        params: dict[str, Any] = {"search": plan.query, "per-page": page_size, "cursor": "*"}
        if filters:
            params["filter"] = ",".join(filters)
        pages = []
        collected = 0
        while collected < plan.limit_per_provider:
            response = self._get(params)
            payload = response.json()
            records = tuple(payload.get("results", ()))[: plan.limit_per_provider - collected]
            pages.append(ProviderPage(records, response.url))
            collected += len(records)
            cursor = payload.get("meta", {}).get("next_cursor")
            if not records or not cursor or collected >= plan.limit_per_provider:
                break
            params["cursor"] = cursor
        return tuple(pages)


class CrossrefProvider(HttpProvider):
    name = "crossref"
    base_url = "https://api.crossref.org/works"

    def search(self, plan: SearchPlan) -> tuple[ProviderPage, ...]:
        page_size = min(plan.limit_per_provider, 1000)
        params: dict[str, Any] = {"query.bibliographic": plan.query, "rows": page_size, "cursor": "*"}
        filters = []
        if plan.year_from:
            filters.append(f"from-pub-date:{plan.year_from}-01-01")
        if plan.year_to:
            filters.append(f"until-pub-date:{plan.year_to}-12-31")
        if filters:
            params["filter"] = ",".join(filters)
        pages = []
        collected = 0
        while collected < plan.limit_per_provider:
            response = self._get(params)
            message = response.json().get("message", {})
            records = tuple(message.get("items", ()))[: plan.limit_per_provider - collected]
            pages.append(ProviderPage(records, response.url))
            collected += len(records)
            cursor = message.get("next-cursor")
            if not records or not cursor or collected >= plan.limit_per_provider:
                break
            params["cursor"] = cursor
        return tuple(pages)


class SemanticScholarProvider(HttpProvider):
    name = "semantic_scholar"
    base_url = "https://api.semanticscholar.org/graph/v1/paper/search"

    def __init__(self, *, api_key: str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.api_key = api_key

    def search(self, plan: SearchPlan) -> tuple[ProviderPage, ...]:
        page_size = min(plan.limit_per_provider, 100)
        params: dict[str, Any] = {
            "query": plan.query,
            "limit": page_size,
            "offset": 0,
            "fields": "paperId,title,authors,year,externalIds,abstract,venue,publicationTypes,citationCount,references.paperId,fieldsOfStudy,openAccessPdf",
        }
        if plan.year_from or plan.year_to:
            params["year"] = f"{plan.year_from or ''}-{plan.year_to or ''}"
        headers = {"x-api-key": self.api_key} if self.api_key else None
        pages = []
        collected = 0
        while collected < plan.limit_per_provider:
            response = self._get(params, headers)
            records = tuple(response.json().get("data", ()))[: plan.limit_per_provider - collected]
            pages.append(ProviderPage(records, response.url))
            collected += len(records)
            if len(records) < page_size or collected >= plan.limit_per_provider:
                break
            params["offset"] = collected
        return tuple(pages)
