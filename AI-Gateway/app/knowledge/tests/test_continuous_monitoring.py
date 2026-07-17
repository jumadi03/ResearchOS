from dataclasses import replace

import pytest

from app.knowledge.models import ProviderFailure
from app.knowledge.monitoring.engine import ScientificMonitoringEngine
from app.knowledge.monitoring.models import (
    ScientificChangeKind, ScientificSourceWatch, SourceWatchStatus,
)
from app.knowledge.monitoring.serialization import (
    discovery_run_from_payload, discovery_run_payload,
)
from app.knowledge.tests.test_citation_snowballing import discovery


def baseline():
    _, run = discovery()
    run = replace(
        run,
        search_plan=replace(run.search_plan, limit_per_provider=2),
        enumerations=(
            replace(
                run.enumerations[0], requested_limit=2, truncated=False,
            ),
        ),
    )
    watch = ScientificSourceWatch(
        "watch-1", run.discovery_contract.project_id,
        run.discovery_contract.contract_id, run.question.question_id,
        run.search_plan.plan_id, 60, "researcher@example",
        run.discovery_contract.human_review_policy,
        "2026-07-17T00:00:00Z", "2026-07-17T01:00:00Z",
    ).finalized()
    return watch, run


def compare(watch, old, new):
    return ScientificMonitoringEngine().compare(
        watch, old, new, scheduled_at="2026-07-17T01:00:00Z",
        started_at="2026-07-17T01:00:01Z",
        completed_at="2026-07-17T01:00:02Z",
    )


def test_watch_is_contract_bound_and_integrity_protected():
    watch, run = baseline()
    assert watch.verify()
    assert not replace(watch, search_plan_id="other").verify()
    with pytest.raises(ValueError, match="does not match"):
        compare(watch, run, replace(
            run, run_id="run-2",
            discovery_contract=replace(
                run.discovery_contract, contract_id="other",
            ),
        ))


def test_new_metadata_citation_retraction_and_failure_are_explicit():
    watch, old = baseline()
    source = old.records[0].source_records[0]
    changed_source = replace(
        source, raw={**source.raw, "cited_by_count": 9, "is_retracted": True},
    )
    changed = replace(
        old.records[0], title="Changed title",
        source_records=(changed_source,),
    )
    new_record = replace(
        old.records[0], record_id="new-record", doi="10.1/new",
        title="New candidate",
        source_records=(
            replace(
                old.records[0].source_records[0],
                source_id="W2", discovery_rank=2,
            ),
        ),
    )
    current = replace(
        old, run_id="run-2", records=(changed, new_record),
        enumerations=(
            replace(
                old.enumerations[0], enumerated_count=2, truncated=True,
            ),
        ),
    )
    result = compare(watch, old, current)
    kinds = {item.kind for item in result.changes}
    assert {
        ScientificChangeKind.NEW_CANDIDATE,
        ScientificChangeKind.METADATA_CHANGED,
        ScientificChangeKind.CITATION_CHANGED,
        ScientificChangeKind.RETRACTED,
    }.issubset(kinds)
    assert result.verify()

    failed = replace(
        old, run_id="run-3", records=(), enumerations=(),
        failures=(ProviderFailure("openalex", "Timeout", "slow", True),),
    )
    partial = compare(watch, old, failed)
    assert partial.stopping_reason == "partial_provider_failure"
    assert [item.kind for item in partial.changes] == [
        ScientificChangeKind.PROVIDER_FAILURE
    ]
    assert ScientificChangeKind.UNAVAILABLE not in {
        item.kind for item in partial.changes
    }


def test_disappearance_does_not_claim_unavailability():
    watch, old = baseline()
    current = replace(
        old, run_id="run-2", records=(),
        enumerations=(
            replace(
                old.enumerations[0], enumerated_count=0, truncated=False,
            ),
        ),
    )
    result = compare(watch, old, current)
    assert not result.changes


def test_discovery_baseline_round_trip_is_lossless():
    _, run = baseline()
    restored = discovery_run_from_payload(discovery_run_payload(run))
    assert restored == run
    restored.validate_query_plan()


def test_paused_or_tampered_watch_is_rejected():
    watch, run = baseline()
    paused = replace(watch, status=SourceWatchStatus.PAUSED)
    assert paused.verify()
    tampered = replace(watch, cadence_minutes=5)
    with pytest.raises(ValueError, match="integrity"):
        compare(tampered, run, run)
