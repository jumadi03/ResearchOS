from app.knowledge.discovery.engine import LiteratureDiscoveryEngine
from app.knowledge.discovery.providers import ProviderPage
from app.knowledge.discovery.query_planner import ScientificQueryPlanner
from app.knowledge.discovery.source_registry import (
    CANONICAL_SOURCE_DEFINITIONS, CanonicalSourceRegistry,
)
from app.knowledge.models import (
    DiscoveryContract, QueryConcept, ScientificQuestion, SearchPlan,
)
from app.knowledge.retrieval.collector import MetadataCollector
from app.knowledge.retrieval.models import LifecycleSignal


class Provider:
    def __init__(self, name, raw):
        self.name = name
        self.raw = raw

    def search(self, plan):
        return (ProviderPage((self.raw,), f"https://{self.name}.test"),)


def test_metadata_collector_retains_conflicts_citations_and_retraction() -> None:
    openalex = Provider("openalex", {
        "id": "W1", "doi": "10.1/a", "title": "Study", "cited_by_count": 8,
        "is_retracted": True, "open_access": {"is_oa": True},
        "concepts": [{"display_name": "Tourism"}], "referenced_works": ["W0"],
    })
    crossref = Provider("crossref", {
        "DOI": "10.1/a", "title": ["Study"], "is-referenced-by-count": 5,
        "subject": ["Development"], "reference": [{"DOI": "10.1/old"}],
    })
    question = ScientificQuestion("q", "Why?")
    contract = DiscoveryContract(
        "c", "researchos-default", "q", "p", "Study discovery",
        ("scholarly_index",), ("Relevant studies",),
        ("Non-scientific sources",), ("en",), ("journal_article",),
        ("reported_result",), 1, 50, "metadata_only",
        "human_review_required", ("budget exhausted",),
    )
    draft = SearchPlan("p", "study", ("openalex", "crossref"))
    registry = CanonicalSourceRegistry(CANONICAL_SOURCE_DEFINITIONS)
    plan = ScientificQueryPlanner().plan(
        question, contract, draft,
        (QueryConcept(
            "study", "study", (), ("multidisciplinary",),
            "researcher@example", "Research topic",
        ),),
        registry.resolve(draft, contract),
    )
    discovery = LiteratureDiscoveryEngine(
        (openalex, crossref), clock=lambda: "time", run_id_factory=lambda: "run"
    ).discover(
        question, contract, plan,
    )

    result = MetadataCollector().collect(discovery, created_at="later")

    record = result.records[0]
    assert record.lifecycle is LifecycleSignal.RETRACTED
    assert record.citation_count == 8
    assert {conflict.field for conflict in record.conflicts} == {
        "citation_count", "concepts", "lifecycle"
    }
    assert {(edge.provider, edge.cited_identifier) for edge in result.citation_edges} == {
        ("openalex", "W0"), ("crossref", "10.1/old")
    }
