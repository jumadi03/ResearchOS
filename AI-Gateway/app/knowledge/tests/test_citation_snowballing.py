from app.knowledge.discovery.engine import LiteratureDiscoveryEngine
from app.knowledge.discovery.providers import CitationPage, ProviderPage
from app.knowledge.discovery.query_planner import ScientificQueryPlanner
from app.knowledge.discovery.source_registry import (
    CANONICAL_SOURCE_DEFINITIONS, CanonicalSourceRegistry,
)
from app.knowledge.models import (
    DiscoveryContract, QueryConcept, ScientificQuestion, SearchPlan,
)
from app.knowledge.retrieval.snowballing import (
    CitationDirection, CitationSnowballingEngine, CitationStoppingReason,
)


class CitationProvider:
    name = "openalex"
    citation_directions = ("backward", "forward")

    def search(self, plan):
        return (ProviderPage(
            ({"id": "W1", "title": "Seed"},), "https://openalex.test/search",
        ),)

    def citation_links(self, identifier, direction, limit):
        graph = {
            ("W1", "backward"): ("W0",),
            ("W1", "forward"): ("W2",),
            ("W0", "backward"): ("W1",),
            ("W0", "forward"): (),
            ("W2", "backward"): ("W1",),
            ("W2", "forward"): ("W3",),
        }
        records = tuple(
            {"identifier": item}
            for item in graph.get((identifier, str(direction)), ())[:limit]
        )
        return (CitationPage(
            records,
            f"https://openalex.test/{identifier}/{direction}",
        ),)


def discovery(maximum_depth=2, retrieval_budget=10):
    provider = CitationProvider()
    question = ScientificQuestion("q", "Why?")
    contract = DiscoveryContract(
        "c", "researchos-default", "q", "p", "Study discovery",
        ("scholarly_index",), ("Relevant studies",),
        ("Non-scientific sources",), ("en",), ("journal_article",),
        ("reported_result",), maximum_depth, retrieval_budget,
        "metadata_only", "human_review_required", ("budget exhausted",),
    )
    draft = SearchPlan("p", "study", ("openalex",), limit_per_provider=1)
    registry = CanonicalSourceRegistry(CANONICAL_SOURCE_DEFINITIONS)
    plan = ScientificQueryPlanner().plan(
        question, contract, draft,
        (QueryConcept(
            "study", "study", (), ("multidisciplinary",),
            "researcher@example", "Research topic",
        ),),
        registry.resolve(draft, contract),
    )
    run = LiteratureDiscoveryEngine(
        (provider,), clock=lambda: "2026-07-17T00:00:00Z",
        run_id_factory=lambda: "run",
    ).discover(question, contract, plan)
    return provider, run


def test_forward_and_backward_traversal_is_deterministic_and_cycle_safe():
    provider, run = discovery()
    engine = CitationSnowballingEngine((provider,))
    values = dict(
        seed_record_id=run.records[0].record_id,
        directions=(
            CitationDirection.BACKWARD, CitationDirection.FORWARD,
        ),
        maximum_depth=2, retrieval_budget=10,
        created_at="2026-07-17T01:00:00Z",
    )

    first = engine.traverse(run, **values)
    second = engine.traverse(run, **values)

    assert first == second
    assert first.verify()
    assert first.manifest_hash == second.manifest_hash
    assert {item.identifier for item in first.candidates} == {
        "W0", "W2", "W3",
    }
    assert len(first.edges) == 5
    assert max(edge.depth for edge in first.edges) == 2
    assert CitationStoppingReason.DEPTH_LIMIT in first.stopping_reasons
    assert not first.failures


def test_budget_is_enforced_and_recorded():
    provider, run = discovery(retrieval_budget=1)
    result = CitationSnowballingEngine((provider,)).traverse(
        run, seed_record_id=run.records[0].record_id,
        directions=(CitationDirection.BACKWARD, CitationDirection.FORWARD),
        maximum_depth=1, retrieval_budget=1,
        created_at="2026-07-17T01:00:00Z",
    )

    assert len(result.edges) == 1
    assert len(result.candidates) == 1
    assert result.stopping_reasons[0] is CitationStoppingReason.BUDGET_EXHAUSTED


def test_contract_depth_and_budget_cannot_be_bypassed():
    provider, run = discovery(maximum_depth=1, retrieval_budget=2)
    engine = CitationSnowballingEngine((provider,))
    common = dict(
        run=run, seed_record_id=run.records[0].record_id,
        directions=(CitationDirection.BACKWARD,),
        created_at="2026-07-17T01:00:00Z",
    )

    try:
        engine.traverse(maximum_depth=2, retrieval_budget=1, **common)
        raise AssertionError("depth bypass was accepted")
    except ValueError as exc:
        assert "maximum depth" in str(exc)
    try:
        engine.traverse(maximum_depth=1, retrieval_budget=3, **common)
        raise AssertionError("budget bypass was accepted")
    except ValueError as exc:
        assert "retrieval budget" in str(exc)


def test_unsupported_direction_is_an_explicit_partial_failure():
    provider, run = discovery()
    provider.citation_directions = ("backward",)
    result = CitationSnowballingEngine((provider,)).traverse(
        run, seed_record_id=run.records[0].record_id,
        directions=(CitationDirection.FORWARD,),
        maximum_depth=1, retrieval_budget=2,
        created_at="2026-07-17T01:00:00Z",
    )

    assert not result.edges
    assert result.failures[0].error_type == "DirectionNotSupported"
    assert CitationStoppingReason.PARTIAL_PROVIDER_FAILURE in result.stopping_reasons
