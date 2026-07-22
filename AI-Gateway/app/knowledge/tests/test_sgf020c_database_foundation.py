from pathlib import Path


MIGRATION = (
    Path(__file__).parents[4]
    / "deploy"
    / "postgres"
    / "init"
    / "040_consequential_research_controls.sql"
).read_text(encoding="utf-8")


def test_sgf020c_defines_required_control_registries() -> None:
    for relation in (
        "consequential_research_profiles",
        "human_authorities",
        "authority_qualifications",
        "conflict_of_interest_declarations",
        "ethics_approvals",
        "scientific_decisions",
        "decision_review_votes",
        "decision_quorum_results",
        "decision_appeals",
        "decision_appeal_events",
    ):
        assert f"CREATE TABLE {relation}" in MIGRATION


def test_sgf020c_is_fail_closed_and_append_only() -> None:
    assert "required_reviewer_quorum >= 2" in MIGRATION
    assert "reviewer_authority_id <> d.proposer_authority_id" in MIGRATION
    assert "require_distinct_release_authority" in MIGRATION
    assert "ethics_satisfied" in MIGRATION
    assert "conflicts_satisfied" in MIGRATION
    assert "freshness_satisfied" in MIGRATION
    assert "assert_consequential_decision_ready" in MIGRATION
    assert "artifact_consequential_publication_gate" in MIGRATION
    assert MIGRATION.count("EXECUTE FUNCTION reject_ledger_mutation()") >= 12


def test_sgf020c_preserves_appeal_and_correction_history() -> None:
    assert "contested_decision_id" in MIGRATION
    assert "resulting_decision_id" in MIGRATION
    assert "'resolved_upheld'" in MIGRATION
    assert "'resolved_overturned'" in MIGRATION
    assert "'resolved_remanded'" in MIGRATION
