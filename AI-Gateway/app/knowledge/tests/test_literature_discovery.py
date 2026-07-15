from pathlib import Path

from app.knowledge.discovery.engine import LiteratureDiscoveryEngine
from app.knowledge.discovery.cache import CachedProvider
from app.knowledge.discovery.persistence import (
    DiscoverySnapshotStore, RawPageStore, serialize_run,
)
from app.knowledge.discovery.providers import OpenAlexProvider, ProviderError, ProviderPage
from app.knowledge.models import MatchKind, ScientificQuestion, SearchPlan


class StubProvider:
    def __init__(self, name: str, records=(), failure: Exception | None = None) -> None:
        self.name = name
        self.records = tuple(records)
        self.failure = failure

    def search(self, plan: SearchPlan) -> tuple[ProviderPage, ...]:
        if self.failure:
            raise self.failure
        return (ProviderPage(self.records, f"https://example.test/{self.name}"),)


def question() -> ScientificQuestion:
    return ScientificQuestion("question-1", "Why do some tourism villages fail?")


def plan(*providers: str) -> SearchPlan:
    return SearchPlan("plan-1", "tourism village failure", providers)


def test_discovery_normalizes_and_exactly_merges_doi_records() -> None:
    openalex = StubProvider("openalex", ({
        "id": "https://openalex.org/W1", "title": "Tourism Village Failure",
        "doi": "https://doi.org/10.1/ABC", "publication_year": 2024,
        "authorships": [{"author": {"display_name": "Ada Lovelace"}}],
    },))
    crossref = StubProvider("crossref", ({
        "DOI": "10.1/abc", "title": ["Tourism Village Failure"],
        "published": {"date-parts": [[2024]]}, "container-title": ["Journal"],
    },))
    engine = LiteratureDiscoveryEngine(
        (openalex, crossref), clock=lambda: "2026-01-01T00:00:00Z",
        run_id_factory=lambda: "run-1",
    )

    run = engine.discover(question(), plan("openalex", "crossref"))

    assert len(run.records) == 1
    assert run.records[0].doi == "10.1/abc"
    assert run.records[0].match_kind is MatchKind.EXACT
    assert tuple(source.provider for source in run.records[0].source_records) == ("crossref", "openalex")


def test_provider_failure_is_explicit_and_preserves_other_results() -> None:
    successful = StubProvider("openalex", ({"id": "W1", "title": "A result"},))
    failed = StubProvider("crossref", failure=ProviderError("rate limited", retryable=True))
    engine = LiteratureDiscoveryEngine((successful, failed), clock=lambda: "now", run_id_factory=lambda: "run")

    run = engine.discover(question(), plan("openalex", "crossref", "semantic_scholar"))

    assert len(run.records) == 1
    assert [(failure.provider, failure.retryable) for failure in run.failures] == [
        ("crossref", True), ("semantic_scholar", False)
    ]


def test_fuzzy_title_match_is_flagged_but_not_merged() -> None:
    provider = StubProvider("semantic_scholar", (
        {"paperId": "1", "title": "Tourism-village failure", "year": 2024},
        {"paperId": "2", "title": "Tourism village failure", "year": 2024},
    ))
    run = LiteratureDiscoveryEngine(
        (provider,), clock=lambda: "now", run_id_factory=lambda: "run"
    ).discover(question(), plan("semantic_scholar"))

    assert len(run.records) == 2
    assert all(record.match_kind is MatchKind.POSSIBLE for record in run.records)
    assert all(len(record.possible_matches) == 1 for record in run.records)


def test_snapshot_is_byte_stable_and_content_addressed(tmp_path: Path) -> None:
    provider = StubProvider("openalex", ({"id": "W1", "title": "Stable"},))
    engine = LiteratureDiscoveryEngine(
        (provider,), clock=lambda: "2026-01-01T00:00:00Z", run_id_factory=lambda: "run-1"
    )
    first = engine.discover(question(), plan("openalex"))
    second = engine.discover(question(), plan("openalex"))

    assert serialize_run(first) == serialize_run(second)
    store = DiscoverySnapshotStore(tmp_path)
    first_path = store.save(first)
    assert store.save(second) == first_path
    assert first_path.read_bytes() == serialize_run(first)


class FakeResponse:
    def __init__(self, payload, url="https://example.test", status_code=200, headers=None):
        self.payload = payload
        self.url = url
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            response = requests.Response()
            response.status_code = self.status_code
            response.headers.update(self.headers)
            raise requests.HTTPError(f"status {self.status_code}", response=response)


def test_openalex_follows_cursor_and_respects_total_limit() -> None:
    calls = []
    responses = iter((
        FakeResponse({"results": [{"id": "1", "title": "One"}], "meta": {"next_cursor": "next"}}),
        FakeResponse({"results": [{"id": "2", "title": "Two"}], "meta": {"next_cursor": None}}),
    ))

    def transport(url, **kwargs):
        calls.append(kwargs["params"].copy())
        return next(responses)

    pages = OpenAlexProvider(transport=transport).search(
        SearchPlan("p", "query", ("openalex",), limit_per_provider=2)
    )

    assert [page.records[0]["id"] for page in pages] == ["1", "2"]
    assert calls[1]["cursor"] == "next"


def test_http_provider_retries_rate_limit_using_retry_after() -> None:
    responses = iter((FakeResponse({}, status_code=429, headers={"Retry-After": "0"}), FakeResponse({"results": []})))
    delays = []
    provider = OpenAlexProvider(
        transport=lambda *args, **kwargs: next(responses), sleeper=delays.append
    )

    assert len(provider.search(plan("openalex"))) == 1
    assert delays == [0.0]


def test_cache_and_raw_pages_avoid_second_provider_call_and_preserve_hash(tmp_path: Path) -> None:
    underlying = StubProvider("openalex", ({"id": "W1", "title": "Cached"},))
    cached = CachedProvider(underlying, tmp_path / "cache")
    first = cached.search(plan("openalex"))
    underlying.records = ({"id": "W2", "title": "Changed"},)
    second = cached.search(plan("openalex"))
    assert first == second

    engine = LiteratureDiscoveryEngine(
        (cached,), clock=lambda: "now", run_id_factory=lambda: "run",
        raw_page_store=RawPageStore(tmp_path / "runs"),
    )
    run = engine.discover(question(), plan("openalex"))
    raw_files = tuple((tmp_path / "runs" / "run" / "raw" / "openalex").glob("*.json"))
    assert len(raw_files) == 1
    assert run.records[0].source_records[0].response_hash in raw_files[0].name
