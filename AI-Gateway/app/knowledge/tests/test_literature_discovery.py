from pathlib import Path
from dataclasses import replace

from app.knowledge.discovery.engine import LiteratureDiscoveryEngine
from app.knowledge.discovery.cache import CachedProvider
from app.knowledge.discovery.persistence import (
    DiscoverySnapshotStore, RawPageStore, serialize_run,
)
from app.knowledge.discovery.providers import (
    CrossrefProvider, OpenAlexProvider, ProviderError, ProviderPage,
)
from app.knowledge.discovery.query_planner import ScientificQueryPlanner
from app.knowledge.discovery.normalization import normalize_doi
from app.knowledge.discovery.source_registry import (
    CANONICAL_SOURCE_DEFINITIONS, CanonicalSourceRegistry,
)
from app.knowledge.models import (
    DiscoveryContract, MatchKind, QueryConcept, ScientificQuestion,
    SearchPlan,
)


class StubProvider:
    def __init__(
        self, name: str, records=(), failure: Exception | None = None,
        total_results: int | None = None,
    ) -> None:
        self.name = name
        self.records = tuple(records)
        self.failure = failure
        self.total_results = total_results

    def search(self, plan: SearchPlan) -> tuple[ProviderPage, ...]:
        if self.failure:
            raise self.failure
        return (ProviderPage(
            self.records, f"https://example.test/{self.name}",
            self.total_results,
        ),)


def question() -> ScientificQuestion:
    return ScientificQuestion("question-1", "Why do some tourism villages fail?")


def plan(*providers: str, limit=25) -> SearchPlan:
    return SearchPlan(
        "plan-1", "tourism village failure", providers,
        limit_per_provider=limit,
    )


def contract(*, budget=100, question_id="question-1", plan_id="plan-1"):
    return DiscoveryContract(
        "contract-1", "researchos-default", question_id, plan_id,
        "Tourism village research", ("scholarly_index",),
        ("Studies about tourism villages",), ("Non-scientific commentary",),
        ("en",), ("journal_article",), ("observational_result",),
        1, budget, "metadata_only", "human_review_required",
        ("retrieval budget exhausted",),
    )


def concepts():
    return (
        QueryConcept(
            "concept-tourism-village", "tourism village",
            ("community tourism",), ("tourism",),
            "researcher@example", "Core phenomenon in the research question",
        ),
        QueryConcept(
            "concept-failure", "failure", ("unsuccessful",),
            ("organizational studies",), "researcher@example",
            "Outcome specified by the research question",
        ),
    )


def planned(*providers: str, budget=100, limit=25):
    draft = plan(*providers, limit=limit)
    registry = CanonicalSourceRegistry(CANONICAL_SOURCE_DEFINITIONS)
    return ScientificQueryPlanner().plan(
        question(), contract(budget=budget), draft, concepts(),
        registry.resolve(draft, contract(budget=budget)),
    )


def test_discovery_normalizes_and_exactly_merges_doi_records() -> None:
    openalex = StubProvider("openalex", ({
        "id": "https://openalex.org/W1", "title": "Tourism Village Failure",
        "doi": "https://doi.org/10.1000/ABC", "publication_year": 2024,
        "authorships": [{"author": {"display_name": "Ada Lovelace"}}],
    },))
    crossref = StubProvider("crossref", ({
        "DOI": "10.1000/abc", "title": ["Tourism Village Failure"],
        "published": {"date-parts": [[2024]]}, "container-title": ["Journal"],
    },))
    engine = LiteratureDiscoveryEngine(
        (openalex, crossref), clock=lambda: "2026-01-01T00:00:00Z",
        run_id_factory=lambda: "run-1",
    )

    run = engine.discover(
        question(), contract(), planned("openalex", "crossref"),
    )

    assert len(run.records) == 1
    assert run.records[0].doi == "10.1000/abc"
    assert run.records[0].match_kind is MatchKind.EXACT
    assert tuple(source.provider for source in run.records[0].source_records) == ("crossref", "openalex")


def test_doi_normalization_is_strict_and_merge_is_order_independent() -> None:
    assert normalize_doi("HTTPS://DOI.ORG/10.1234/ABC") == "10.1234/abc"
    assert normalize_doi("not-a-doi") is None
    assert normalize_doi("10.12/too-short-prefix") is None
    left = StubProvider("openalex", ({
        "id": "W1", "title": "Canonical title",
        "doi": "10.1234/same", "publication_year": 2024,
    },))
    right = StubProvider("crossref", ({
        "DOI": "https://doi.org/10.1234/SAME",
        "title": ["Canonical title"], "published": {"date-parts": [[2024]]},
    },))
    first = LiteratureDiscoveryEngine(
        (left, right), clock=lambda: "now", run_id_factory=lambda: "run",
    ).discover(question(), contract(), planned("openalex", "crossref"))
    second = LiteratureDiscoveryEngine(
        (right, left), clock=lambda: "now", run_id_factory=lambda: "run",
    ).discover(question(), contract(), planned("crossref", "openalex"))
    assert first.records[0].title == second.records[0].title
    assert first.records[0].authors == second.records[0].authors


def test_provider_failure_is_explicit_and_preserves_other_results() -> None:
    successful = StubProvider("openalex", ({"id": "W1", "title": "A result"},))
    failed = StubProvider("crossref", failure=ProviderError("rate limited", retryable=True))
    engine = LiteratureDiscoveryEngine((successful, failed), clock=lambda: "now", run_id_factory=lambda: "run")

    run = engine.discover(
        question(), contract(),
        planned("openalex", "crossref", "semantic_scholar"),
    )

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
    ).discover(question(), contract(), planned("semantic_scholar"))

    assert len(run.records) == 2
    assert all(record.match_kind is MatchKind.POSSIBLE for record in run.records)
    assert all(len(record.possible_matches) == 1 for record in run.records)


def test_snapshot_is_byte_stable_and_content_addressed(tmp_path: Path) -> None:
    provider = StubProvider("openalex", ({"id": "W1", "title": "Stable"},))
    engine = LiteratureDiscoveryEngine(
        (provider,), clock=lambda: "2026-01-01T00:00:00Z", run_id_factory=lambda: "run-1"
    )
    first = engine.discover(question(), contract(), planned("openalex"))
    second = engine.discover(question(), contract(), planned("openalex"))

    assert serialize_run(first) == serialize_run(second)
    store = DiscoverySnapshotStore(tmp_path)
    first_path = store.save(first)
    assert store.save(second) == first_path
    assert first_path.read_bytes() == serialize_run(first)
    assert tuple(item.name for item in first.source_definitions) == ("openalex",)


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


def test_crossref_resolves_exact_doi_without_ranked_search() -> None:
    calls = []

    def transport(url, **kwargs):
        calls.append((url, kwargs["params"]))
        return FakeResponse(
            {"message": {"DOI": "10.1371/journal.pone.0319334", "title": ["Exact"]}},
            url=url,
        )

    pages = CrossrefProvider(transport=transport).search(
        SearchPlan(
            "p", "https://doi.org/10.1371/journal.pone.0319334", ("crossref",),
            limit_per_provider=10, year_from=2025, year_to=2025,
        )
    )

    assert pages[0].records[0]["DOI"] == "10.1371/journal.pone.0319334"
    assert calls == [
        ("https://api.crossref.org/works/10.1371%2Fjournal.pone.0319334", {})
    ]


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
    run = engine.discover(question(), contract(), planned("openalex"))
    raw_files = tuple((tmp_path / "runs" / "run" / "raw" / "openalex").glob("*.json"))
    assert len(raw_files) == 1
    assert run.records[0].source_records[0].response_hash in raw_files[0].name


def test_discovery_contract_is_bound_and_budgeted_before_provider_call() -> None:
    import pytest

    provider = StubProvider("openalex", ({"id": "W1", "title": "Result"},))
    engine = LiteratureDiscoveryEngine((provider,))
    with pytest.raises(ValueError, match="research question"):
        engine.discover(
            question(), contract(question_id="other"), planned("openalex"),
        )
    with pytest.raises(ValueError, match="search plan"):
        engine.discover(
            question(), contract(plan_id="other"), planned("openalex"),
        )
    with pytest.raises(ValueError, match="retrieval budget"):
        engine.discover(
            question(), contract(budget=1), plan("openalex", "crossref"),
        )


def test_canonical_source_registry_rejects_unknown_inactive_and_wrong_category() -> None:
    import pytest

    registry = CanonicalSourceRegistry(CANONICAL_SOURCE_DEFINITIONS)
    with pytest.raises(ValueError, match="not registered"):
        registry.resolve(plan("unknown"), contract())

    openalex = next(
        item for item in CANONICAL_SOURCE_DEFINITIONS
        if item.name == "openalex"
    )
    inactive = CanonicalSourceRegistry((replace(openalex, status="inactive"),))
    with pytest.raises(ValueError, match="not active"):
        inactive.resolve(plan("openalex"), contract())

    with pytest.raises(ValueError, match="category is not permitted"):
        registry.resolve(
            plan("openalex"),
            replace(contract(), source_categories=("general_web",)),
        )


def test_canonical_source_registry_rejects_duplicate_and_mismatched_provider() -> None:
    import pytest

    openalex = next(
        item for item in CANONICAL_SOURCE_DEFINITIONS
        if item.name == "openalex"
    )
    with pytest.raises(ValueError, match="name must be unique"):
        CanonicalSourceRegistry((openalex, replace(
            openalex, source_id="other-source",
        )))

    class MismatchedProvider:
        name = "openalex"
        base_url = "https://example.test/works"

    with pytest.raises(ValueError, match="base URL"):
        CanonicalSourceRegistry(
            CANONICAL_SOURCE_DEFINITIONS, (MismatchedProvider(),),
        )


def test_discovery_run_preserves_complete_source_policy() -> None:
    provider = StubProvider("openalex", ({"id": "W1", "title": "Result"},))
    run = LiteratureDiscoveryEngine(
        (provider,), clock=lambda: "now", run_id_factory=lambda: "run",
    ).discover(question(), contract(), planned("openalex"))

    definition = run.source_definitions[0]
    assert definition.name == "openalex"
    assert definition.authority_level == "A2"
    assert definition.access_method == "official_api"
    assert definition.rate_limit_policy
    assert definition.robots_policy
    assert definition.license_policy
    assert definition.trust_profile


def test_enumerator_preserves_rank_query_page_url_and_truncation() -> None:
    provider = StubProvider(
        "openalex",
        (
            {"id": "W1", "title": "First"},
            {"id": "W2", "title": "Second"},
        ),
        total_results=50,
    )
    run = LiteratureDiscoveryEngine(
        (provider,), clock=lambda: "now", run_id_factory=lambda: "run",
    ).discover(
        question(), contract(), planned("openalex", limit=2),
    )

    summary = run.enumerations[0]
    assert summary.enumerated_count == 2
    assert summary.total_available == 50
    assert summary.page_count == 1
    assert summary.truncated is True
    observations = tuple(
        source for record in run.records
        for source in record.source_records
    )
    assert sorted(item.discovery_rank for item in observations) == [1, 2]
    assert all(
        item.source_definition_id == "source-openalex"
        and item.query_family_id == run.search_plan.query_families[0].family_id
        and item.source_query == run.search_plan.query_for("openalex")
        and item.page_number == 1
        and item.request_url == "https://example.test/openalex"
        and item.canonical_url.startswith("https://openalex.org/")
        for item in observations
    )


def test_discovery_run_rejects_inconsistent_enumeration_inventory() -> None:
    import pytest

    run = LiteratureDiscoveryEngine(
        (StubProvider("openalex", ({"id": "W1", "title": "First"},)),),
        clock=lambda: "now", run_id_factory=lambda: "run",
    ).discover(question(), contract(), planned("openalex"))
    inconsistent = replace(
        run.enumerations[0], enumerated_count=0,
    )
    with pytest.raises(ValueError, match="enumeration provenance"):
        replace(run, enumerations=(inconsistent,))


def test_scientific_query_planner_is_deterministic_and_traceable() -> None:
    first = planned("openalex", "crossref")
    second = planned("openalex", "crossref")

    assert first == second
    assert first.planning_method == "scientific-query-planner-v1"
    assert tuple(item.concept_id for item in first.concepts) == (
        "concept-tourism-village", "concept-failure",
    )
    assert len(first.query_families) == 1
    assert {item.provider for item in first.source_queries} == {
        "openalex", "crossref",
    }
    assert all(item.source_id for item in first.source_queries)
    assert first.query_for("openalex") == (
        '("tourism village" OR "community tourism") AND '
        '("failure" OR "unsuccessful")'
    )


def test_discovery_rejects_manual_query_plan_bypass() -> None:
    import pytest

    engine = LiteratureDiscoveryEngine((StubProvider("openalex"),))
    with pytest.raises(ValueError, match="Query Planner is required"):
        engine.discover(question(), contract(), plan("openalex"))


def test_planned_search_contract_rejects_duplicate_concept_identity() -> None:
    import pytest

    valid = planned("openalex")
    duplicate = replace(valid, concepts=(valid.concepts[0], valid.concepts[0]))
    with pytest.raises(ValueError, match="concept IDs must be unique"):
        duplicate.validate_planned()


def test_query_planner_rejects_missing_attribution_and_duplicate_synonyms() -> None:
    import pytest

    with pytest.raises(ValueError, match="attributed_by"):
        QueryConcept(
            "concept", "governance", (), ("social science",), "",
            "Research scope",
        )
    with pytest.raises(ValueError, match="synonyms must be unique"):
        QueryConcept(
            "concept", "governance", ("Governance",),
            ("social science",), "researcher@example", "Research scope",
        )
    with pytest.raises(ValueError, match="empty values"):
        QueryConcept(
            "concept", "governance", ("",), ("social science",),
            "researcher@example", "Research scope",
        )


def test_query_planner_preserves_exact_doi_lookup() -> None:
    question = ScientificQuestion("doi-question", "Find this exact paper")
    contract = DiscoveryContract(
        "doi-contract", "researchos-default", "doi-question", "doi-plan",
        "Exact paper lookup", ("scholarly_index",), ("Exact DOI",),
        ("Other works",), ("en",), ("journal_article",),
        ("reported_result",), 1, 10, "metadata_only",
        "human_review_required", ("exact work found",),
    )
    draft = SearchPlan(
        "doi-plan", "https://doi.org/10.1371/journal.pone.0319334",
        ("crossref",), limit_per_provider=10,
    )
    registry = CanonicalSourceRegistry(CANONICAL_SOURCE_DEFINITIONS)
    planned_doi = ScientificQueryPlanner().plan(
        question, contract, draft,
        (QueryConcept(
            "doi-concept", "reproducibility", ("replicability",),
            ("metascience",), "researcher@example", "Known target paper",
        ),),
        registry.resolve(draft, contract),
    )

    assert planned_doi.query_for("crossref") == draft.query
    assert planned_doi.query_families[0].purpose == "Exact DOI lookup"
