"""End-to-end verifier for SCAN-001N/O monitoring and safety boundaries."""

import os
from uuid import uuid4

from app.knowledge.discovery.engine import LiteratureDiscoveryEngine
from app.knowledge.discovery.providers import ProviderPage
from app.knowledge.discovery.query_planner import ScientificQueryPlanner
from app.knowledge.discovery.source_registry import (
    CANONICAL_SOURCE_DEFINITIONS, CanonicalSourceRegistry,
)
from app.knowledge.models import (
    DiscoveryContract, QueryConcept, ScientificQuestion, SearchPlan,
)
from app.knowledge.monitoring.engine import ScientificMonitoringEngine
from app.knowledge.repositories.postgres import PostgresScientificDataRepository


class Provider:
    name = "openalex"

    def __init__(self, records):
        self.records = records

    def search(self, _plan):
        return (ProviderPage(self.records, "https://openalex.test/monitoring"),)


def discovery(identity, records, clock):
    question = ScientificQuestion(f"question-{identity}", "What changed?")
    contract = DiscoveryContract(
        f"contract-{identity}", "researchos-default", question.question_id,
        f"plan-{identity}", "Continuous monitoring verification",
        ("scholarly_index",), ("Relevant studies",),
        ("Non-scientific sources",), ("en",), ("journal_article",),
        ("reported_result",), 1, 10, "metadata_only",
        "human_review_required", ("retrieval budget exhausted",),
    )
    draft = SearchPlan(contract.search_plan_id, "monitoring", ("openalex",), 10)
    registry = CanonicalSourceRegistry(CANONICAL_SOURCE_DEFINITIONS)
    plan = ScientificQueryPlanner().plan(
        question, contract, draft,
        (QueryConcept(
            f"concept-{identity}", "monitoring", (), ("multidisciplinary",),
            "ci-verifier", "Consolidation verification",
        ),),
        registry.resolve(draft, contract),
    )
    return LiteratureDiscoveryEngine(
        (Provider(records),), clock=lambda: clock,
        run_id_factory=lambda: f"discovery-{identity}-{clock[11:13]}",
    ).discover(question, contract, plan)


def main():
    identity = uuid4().hex
    repository = PostgresScientificDataRepository(os.environ["DATABASE_URL"])
    baseline = discovery(
        identity, ({"id": "W1", "title": "Baseline study"},),
        "2026-07-17T01:00:00Z",
    )
    repository.persist_discovery(baseline)
    watch = repository.create_source_watch(
        baseline, cadence_minutes=60, owner_id="ci-verifier",
        created_at="2026-07-17T01:00:00Z",
        next_run_at="2026-07-17T02:00:00Z", maximum_runs=2,
    )
    loaded, restored = repository.load_source_watch(watch.watch_id)
    assert loaded.verify() and restored == baseline

    paused = repository.transition_source_watch(
        watch.watch_id, to_status="paused", actor_id="ci-verifier",
        rationale="Verify pause boundary", occurred_at="2026-07-17T01:10:00Z",
    )
    assert paused.verify()
    loaded, _ = repository.load_source_watch(watch.watch_id)
    assert loaded.status.value == "paused"
    resumed = repository.transition_source_watch(
        watch.watch_id, to_status="active", actor_id="ci-verifier",
        rationale="Verify controlled resume", occurred_at="2026-07-17T01:20:00Z",
        next_run_at="2026-07-17T02:00:00Z",
    )
    assert resumed.verify()

    current = discovery(
        identity,
        (
            {"id": "W1", "title": "Updated baseline study"},
            {"id": "W2", "title": "New candidate", "doi": "10.1/new"},
        ),
        "2026-07-17T02:00:00Z",
    )
    repository.persist_discovery(current)
    monitoring = ScientificMonitoringEngine().compare(
        watch, baseline, current, scheduled_at="2026-07-17T02:00:00Z",
        started_at="2026-07-17T02:00:01Z",
        completed_at="2026-07-17T02:00:02Z",
    )
    repository.persist_monitoring_run(watch, monitoring, current)
    repository.persist_monitoring_run(watch, monitoring, current)
    runs = repository.list_monitoring_runs(watch.watch_id)
    changes = repository.list_scientific_changes(
        watch.watch_id, unacknowledged_only=True,
    )
    assert len(runs) == 1 and len(changes) >= 2
    assert all(item["candidate_status"] == "discovery_only" for item in changes)
    acknowledgement = repository.acknowledge_scientific_change(
        changes[0]["change_id"], actor_id="reviewer@ci",
        rationale="Reviewed as a discovery candidate only",
        occurred_at="2026-07-17T02:10:00Z",
    )
    assert acknowledgement.startswith("ack-")
    remaining = repository.list_scientific_changes(
        watch.watch_id, unacknowledged_only=True,
    )
    assert len(remaining) == len(changes) - 1

    with repository._connect() as connection, connection.cursor() as cursor:
        cursor.execute("""
            SELECT count(*) FROM evidence_objects e
            JOIN provenance_events p ON p.output_object_id=e.evidence_id
            WHERE p.execution_id LIKE %s
        """, (f"%{identity}%",))
        assert cursor.fetchone()[0] == 0
        cursor.execute("""
            SELECT count(*) FROM knowledge_edges k
            JOIN provenance_events p ON p.provenance_id=k.provenance_id
            WHERE p.execution_id LIKE %s OR p.event_payload::text LIKE %s
        """, (f"%{identity}%", f"%{identity}%"))
        assert cursor.fetchone()[0] == 0
    print("continuous-monitoring=passed")


if __name__ == "__main__":
    main()
