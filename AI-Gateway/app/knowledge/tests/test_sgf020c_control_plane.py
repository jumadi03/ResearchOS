from pathlib import Path


ROOT = Path(__file__).parents[4]
SERVICE = (ROOT / "AI-Gateway/app/knowledge/consequential_controls.py").read_text()
ROUTER = (ROOT / "AI-Gateway/app/router/consequential.py").read_text()
MAIN = (ROOT / "AI-Gateway/app/main.py").read_text()
SETTINGS = (ROOT / "AI-Gateway/app/settings.py").read_text()


def test_control_plane_is_database_backed_and_fail_closed() -> None:
    assert "consequential_research_profiles" in SERVICE
    assert "human_authorities" in SERVICE
    assert "project_consequential_profiles" in SERVICE
    assert "consequential_decision_readiness" in SERVICE
    assert "authority_qualifications" in SERVICE
    assert "ethics_approvals" in SERVICE
    assert "conflict_of_interest_declarations" in SERVICE
    assert "decision_review_votes" in SERVICE
    assert "decision_quorum_results" in SERVICE
    assert "decision_appeals" in SERVICE
    assert "Authenticated principal is not a registered active human authority" in SERVICE
    assert "DATABASE_URL is required" in SERVICE


def test_control_plane_requires_explicit_roles() -> None:
    assert "KnowledgeRole.ADMIN" in ROUTER
    assert "KnowledgeRole.AUDITOR" in ROUTER
    assert "KnowledgeRole.REVIEWER" in ROUTER
    assert "KnowledgeRole.PUBLISHER" in ROUTER
    assert "consequential_profile_activated" in ROUTER
    assert '/decisions/{decision_id}/votes' in ROUTER
    assert '/decisions/{decision_id}/appeals' in ROUTER


def test_application_requires_schema_40_and_mounts_router() -> None:
    assert 'os.getenv("DATABASE_SCHEMA_VERSION", "41")' in SETTINGS
    assert "app.state.consequential_controls" in MAIN
    assert "app.include_router(consequential_router)" in MAIN


def test_revalidation_and_independent_appeal_are_exposed() -> None:
    assert "consequential_revalidation_queue" in SERVICE
    assert "decision_appeal_events" in SERVICE
    assert '"/revalidation"' in ROUTER
    assert '"/appeals/{appeal_id}/events"' in ROUTER
