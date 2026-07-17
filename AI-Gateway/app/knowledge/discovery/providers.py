"""Provider boundary and HTTP adapters for SK-001A."""

from __future__ import annotations

from dataclasses import dataclass
import re
from time import sleep
from typing import Any, Callable, Protocol
from urllib.parse import quote

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
    total_results: int | None = None


@dataclass(frozen=True, slots=True)
class CitationPage:
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

    def _get(
        self, params: dict[str, Any], headers: dict[str, str] | None = None,
        *, url: str | None = None,
    ) -> requests.Response:
        for attempt in range(1, self.max_attempts + 1):
            try:
                response = self._transport(
                    url or self.base_url, params=params, headers=headers or {}, timeout=self.timeout
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
    citation_directions = ("backward", "forward")

    def search(self, plan: SearchPlan) -> tuple[ProviderPage, ...]:
        filters = []
        if plan.year_from:
            filters.append(f"from_publication_date:{plan.year_from}-01-01")
        if plan.year_to:
            filters.append(f"to_publication_date:{plan.year_to}-12-31")
        page_size = min(plan.limit_per_provider, 200)
        params: dict[str, Any] = {
            "search": plan.query_for(self.name), "per-page": page_size,
            "cursor": "*",
        }
        if filters:
            params["filter"] = ",".join(filters)
        pages = []
        collected = 0
        while collected < plan.limit_per_provider:
            response = self._get(params)
            payload = response.json()
            records = tuple(payload.get("results", ()))[: plan.limit_per_provider - collected]
            pages.append(ProviderPage(
                records, response.url, payload.get("meta", {}).get("count"),
            ))
            collected += len(records)
            cursor = payload.get("meta", {}).get("next_cursor")
            if not records or not cursor or collected >= plan.limit_per_provider:
                break
            params["cursor"] = cursor
        return tuple(pages)

    def citation_links(self, identifier, direction, limit):
        identifier = str(identifier).rsplit("/", 1)[-1]
        if str(direction) == "backward":
            response = self._get({}, url=f"{self.base_url}/{quote(identifier, safe='')}")
            references = response.json().get("referenced_works") or ()
            return (CitationPage(tuple(
                {"identifier": str(item).rsplit("/", 1)[-1]} for item in references[:limit]
            ), response.url),)
        pages = []
        collected = 0
        params = {
            "filter": f"cites:{identifier}",
            "per-page": min(limit, 200), "cursor": "*",
        }
        while collected < limit:
            response = self._get(params)
            payload = response.json()
            records = tuple(
                {
                    "identifier": str(item.get("id") or "").rsplit("/", 1)[-1],
                    "title": item.get("title"),
                    "doi": item.get("doi"),
                }
                for item in payload.get("results", ())[:limit - collected]
            )
            pages.append(CitationPage(records, response.url))
            collected += len(records)
            cursor = payload.get("meta", {}).get("next_cursor")
            if not records or not cursor or collected >= limit:
                break
            params["cursor"] = cursor
        return tuple(pages)


class CrossrefProvider(HttpProvider):
    name = "crossref"
    base_url = "https://api.crossref.org/works"
    citation_directions = ("backward",)

    def search(self, plan: SearchPlan) -> tuple[ProviderPage, ...]:
        doi = plan.query_for(self.name).strip()
        doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
        if re.fullmatch(r"10\.\d{4,9}/\S+", doi, flags=re.IGNORECASE):
            response = self._get({}, url=f"{self.base_url}/{quote(doi, safe='')}")
            record = response.json().get("message") or {}
            return (ProviderPage(
                (record,) if record else (), response.url, 1 if record else 0,
            ),)

        page_size = min(plan.limit_per_provider, 1000)
        params: dict[str, Any] = {
            "query.bibliographic": plan.query_for(self.name),
            "rows": page_size, "cursor": "*",
        }
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
            pages.append(ProviderPage(
                records, response.url, message.get("total-results"),
            ))
            collected += len(records)
            cursor = message.get("next-cursor")
            if not records or not cursor or collected >= plan.limit_per_provider:
                break
            params["cursor"] = cursor
        return tuple(pages)

    def citation_links(self, identifier, direction, limit):
        if str(direction) != "backward":
            raise ProviderError(
                "Crossref public API does not expose a complete forward citation list"
            )
        doi = re.sub(
            r"^https?://(?:dx\.)?doi\.org/", "", str(identifier),
            flags=re.IGNORECASE,
        )
        response = self._get({}, url=f"{self.base_url}/{quote(doi, safe='')}")
        references = response.json().get("message", {}).get("reference") or ()
        return (CitationPage(tuple(
            {"identifier": item.get("DOI")}
            for item in references[:limit] if item.get("DOI")
        ), response.url),)


class SemanticScholarProvider(HttpProvider):
    name = "semantic_scholar"
    base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
    citation_directions = ("backward", "forward")

    def __init__(self, *, api_key: str | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.api_key = api_key

    def search(self, plan: SearchPlan) -> tuple[ProviderPage, ...]:
        page_size = min(plan.limit_per_provider, 100)
        params: dict[str, Any] = {
            "query": plan.query_for(self.name),
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
            payload = response.json()
            records = tuple(payload.get("data", ()))[: plan.limit_per_provider - collected]
            pages.append(ProviderPage(
                records, response.url, payload.get("total"),
            ))
            collected += len(records)
            if len(records) < page_size or collected >= plan.limit_per_provider:
                break
            params["offset"] = collected
        return tuple(pages)

    def citation_links(self, identifier, direction, limit):
        relation = "references" if str(direction) == "backward" else "citations"
        headers = {"x-api-key": self.api_key} if self.api_key else None
        url = (
            "https://api.semanticscholar.org/graph/v1/paper/"
            f"{quote(str(identifier), safe='')}/{relation}"
        )
        paper_key = "citedPaper" if relation == "references" else "citingPaper"
        pages = []
        collected = 0
        while collected < limit:
            response = self._get(
                {
                    "offset": collected, "limit": min(limit - collected, 1000),
                    "fields": "title,externalIds",
                },
                headers, url=url,
            )
            payload = response.json()
            records = tuple(
                {
                    "identifier": item.get(paper_key, {}).get("paperId"),
                    "title": item.get(paper_key, {}).get("title"),
                    "doi": (
                        item.get(paper_key, {}).get("externalIds") or {}
                    ).get("DOI"),
                }
                for item in payload.get("data", ())
                if item.get(paper_key, {}).get("paperId")
            )
            pages.append(CitationPage(records, response.url))
            collected += len(records)
            if not records or payload.get("next") is None or collected >= limit:
                break
        return tuple(pages)
