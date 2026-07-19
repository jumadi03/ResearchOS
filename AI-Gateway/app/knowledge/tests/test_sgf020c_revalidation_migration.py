from pathlib import Path


MIGRATION = (
    Path(__file__).parents[4]
    / "deploy/postgres/init/041_consequential_revalidation_and_appeal.sql"
).read_text(encoding="utf-8")


def test_quorum_snapshots_must_match_database_readiness() -> None:
    assert "enforce_quorum_result_integrity" in MIGRATION
    assert "quorum result does not match database-derived readiness" in MIGRATION
    assert "decision_quorum_results_integrity" in MIGRATION


def test_appeal_resolution_requires_independent_authority() -> None:
    assert "enforce_independent_appeal_resolution" in MIGRATION
    assert "appeal.appellant_authority_id" in MIGRATION
    assert "contested.proposer_authority_id" in MIGRATION
    assert "reviewer_authority_id=NEW.actor_authority_id" in MIGRATION
    assert "resolved appeal requires resulting_decision_id" in MIGRATION


def test_revalidation_queue_is_fail_closed() -> None:
    assert "CREATE VIEW consequential_revalidation_queue" in MIGRATION
    assert "'decision_expired'" in MIGRATION
    assert "'review_overdue'" in MIGRATION
    assert "'ethics_invalid'" in MIGRATION
    assert "'blocked'" in MIGRATION
