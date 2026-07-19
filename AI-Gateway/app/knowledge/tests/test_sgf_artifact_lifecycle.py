"""SGF-020/030/040 compliance tests for canonical artifact lifecycle actions."""

from pathlib import Path

from app.knowledge.authentication import KnowledgePrincipal, KnowledgeRole
from app.knowledge.repositories.artifacts import (
    ARTIFACT_LIFECYCLE_STATES,
    ARTIFACT_LIFECYCLE_TRANSITIONS,
    next_artifact_status,
    require_artifact_transition,
)
from app.knowledge.repository_service import KnowledgeRepositoryService


EXPECTED_TRANSITIONS = {
    "planned": "draft",
    "draft": "review",
    "review": "validated",
    "validated": "ratified",
    "ratified": "published",
    "published": "deprecated",
    "deprecated": "archived",
}


class ReadModelRepository:
    def __init__(self, status: str) -> None:
        self.status = status

    def get_object_read_model(self, object_ref: str, project_id: str) -> dict:
        return {
            "identity": {
                "object_id": object_ref,
                "object_type": "research_artifact",
            },
            "artifact": {"status": self.status},
            "evidence": None,
            "project_id": project_id,
        }

    def get_work_queue(self, project_id: str) -> dict:
        return {"project_id": project_id, "pending_transitions": []}


def principal(*roles: KnowledgeRole) -> KnowledgePrincipal:
    return KnowledgePrincipal("actor@example", frozenset(roles))


def test_sgf_040_canonical_transition_sequence_is_complete_and_forward_only():
    assert ARTIFACT_LIFECYCLE_TRANSITIONS == EXPECTED_TRANSITIONS
    assert ARTIFACT_LIFECYCLE_STATES == frozenset((*EXPECTED_TRANSITIONS, "archived"))
    assert next_artifact_status("archived") is None


def test_sgf_040_accepts_every_canonical_edge():
    for current, expected in EXPECTED_TRANSITIONS.items():
        require_artifact_transition(current, expected)


def test_sgf_040_rejects_skipped_reverse_repeated_and_terminal_edges():
    invalid = (
        ("draft", "validated"),
        ("validated", "review"),
        ("review", "review"),
        ("archived", "planned"),
    )
    for current, requested in invalid:
        try:
            require_artifact_transition(current, requested)
        except ValueError as exc:
            assert f"{current} -> {requested}" in str(exc)
        else:
            raise AssertionError(f"transition unexpectedly permitted: {current} -> {requested}")


def test_reviewer_receives_only_the_next_canonical_transition_for_every_state():
    for current, expected in EXPECTED_TRANSITIONS.items():
        service = KnowledgeRepositoryService(ReadModelRepository(current))
        role = (
            KnowledgeRole.PUBLISHER
            if expected == "published"
            else KnowledgeRole.REVIEWER
        )
        result = service.get_object_read_model(
            "artifact-1", "project-1", principal(role)
        )
        actions = result["permissions"]["available_actions"]
        assert actions == [{
            "action": "artifact:transition",
            "method": "POST",
            "href": "/knowledge/artifacts/artifact-1/transitions",
            "to_status": expected,
        }]


def test_draft_requires_review_and_cannot_skip_directly_to_validated():
    service = KnowledgeRepositoryService(ReadModelRepository("draft"))
    result = service.get_object_read_model(
        "artifact-1", "project-1", principal(KnowledgeRole.REVIEWER)
    )
    action = result["permissions"]["available_actions"][0]
    assert action["to_status"] == "review"
    assert action["to_status"] != "validated"


def test_archived_artifact_has_no_transition_action():
    service = KnowledgeRepositoryService(ReadModelRepository("archived"))
    result = service.get_object_read_model(
        "artifact-1", "project-1", principal(KnowledgeRole.REVIEWER)
    )
    assert result["permissions"]["available_actions"] == []


def test_reviewer_cannot_release_ratified_artifact_and_publisher_can():
    service = KnowledgeRepositoryService(ReadModelRepository("ratified"))
    reviewer = service.get_object_read_model(
        "artifact-1", "project-1", principal(KnowledgeRole.REVIEWER)
    )
    publisher = service.get_object_read_model(
        "artifact-1", "project-1", principal(KnowledgeRole.PUBLISHER)
    )
    assert reviewer["permissions"]["available_actions"] == []
    assert publisher["permissions"]["available_actions"][0]["to_status"] == "published"


def test_non_reviewer_cannot_receive_artifact_transition_authority():
    service = KnowledgeRepositoryService(ReadModelRepository("draft"))
    for role in (
        KnowledgeRole.ADMIN,
        KnowledgeRole.AUDITOR,
        KnowledgeRole.DISCOVERER,
        KnowledgeRole.INDEXER,
        KnowledgeRole.PUBLISHER,
    ):
        result = service.get_object_read_model(
            "artifact-1", "project-1", principal(role)
        )
        assert all(
            item["action"] != "artifact:transition"
            for item in result["permissions"]["available_actions"]
        )


def test_work_queue_exposes_distinct_review_and_publish_authority():
    service = KnowledgeRepositoryService(ReadModelRepository("ratified"))
    reviewer = service.get_work_queue(
        "project-1", principal(KnowledgeRole.REVIEWER)
    )["permissions"]
    publisher = service.get_work_queue(
        "project-1", principal(KnowledgeRole.PUBLISHER)
    )["permissions"]
    assert reviewer["can_review"] is True
    assert reviewer["can_publish"] is False
    assert publisher["can_review"] is False
    assert publisher["can_publish"] is True


def test_workspace_uses_publish_authority_for_published_transition():
    workspace = (
        Path(__file__).resolve().parents[2]
        / "product" / "static" / "workspace.js"
    ).read_text(encoding="utf-8")
    assert "x.next_status==='published'?q.permissions.can_publish" in workspace


def test_sgf_040d_publication_relationship_migration_is_immutable_and_typed():
    migration = (
        Path(__file__).resolve().parents[4]
        / "deploy" / "postgres" / "init"
        / "033_publication_relationships.sql"
    ).read_text(encoding="utf-8")
    assert "CREATE TABLE publication_relationships" in migration
    assert "('corrects','supersedes','retracts')" in migration
    assert "publication_relationships_immutable" in migration
    assert "target_artifact_id IS NULL" in migration
    assert "source_artifact_id <> target_artifact_id" in migration


def test_sgf_040e_impact_review_is_human_resolved_and_immutable():
    migration = (
        Path(__file__).resolve().parents[4]
        / "deploy" / "postgres" / "init"
        / "034_scientific_impact_review.sql"
    ).read_text(encoding="utf-8")
    assert "CREATE TABLE scientific_impact_review_resolutions" in migration
    assert "'evidence_review_required'" in migration
    assert "'publication_review_required'" in migration
    assert "scientific_impact_review_resolutions_immutable" in migration
    assert "change_id text NOT NULL UNIQUE" in migration


def test_sgf_040f_follow_up_case_routing_is_non_automating():
    from app.knowledge.monitoring.models import (
        ImpactReviewDecision, ImpactReviewResolution,
    )
    evidence = ImpactReviewResolution(
        "resolution-1", "change-1",
        ImpactReviewDecision.EVIDENCE_REVIEW_REQUIRED,
        "reviewer@example", "Evidence impact requires review", "time",
    ).follow_up_case()
    publication = ImpactReviewResolution(
        "resolution-2", "change-2",
        ImpactReviewDecision.PUBLICATION_REVIEW_REQUIRED,
        "reviewer@example", "Publication impact requires review", "time",
    ).follow_up_case()
    assert evidence["case_id"] == "follow-up:resolution-1"
    assert evidence["required_role"] == "reviewer"
    assert publication["required_role"] == "publisher"
    assert evidence["decision_automation"] is False
    assert ImpactReviewResolution(
        "resolution-3", "change-3", ImpactReviewDecision.NO_ACTION,
        "reviewer@example", "No material connection found", "time",
    ).follow_up_case() is None


def test_sgf_040g_target_linkage_is_typed_unique_and_immutable():
    migration = (
        Path(__file__).resolve().parents[4]
        / "deploy" / "postgres" / "init"
        / "035_scientific_follow_up_case_targets.sql"
    ).read_text(encoding="utf-8")
    assert "CREATE TABLE scientific_follow_up_case_targets" in migration
    assert "target_kind IN ('evidence','publication')" in migration
    assert "resolution_id text NOT NULL UNIQUE" in migration
    assert "scientific_follow_up_case_targets_immutable" in migration
    assert "REFERENCES canonical_objects(object_id)" in migration


def test_sgf_040h_consequential_actions_reuse_audited_workflows():
    source = (
        Path(__file__).resolve().parents[2]
        / "knowledge" / "repository_service.py"
    ).read_text(encoding="utf-8")
    assert '"requires_confirmation": True' in source
    assert '"audit_workflow": "evidence_review_event"' in source
    assert '"audit_workflow": "publication_relationship"' in source
    assert "/knowledge/evidence/" in source
    assert "/knowledge/publications/" in source


def test_sgf_040i_closure_requires_matching_canonical_action_event():
    source = (
        Path(__file__).resolve().parents[2]
        / "knowledge" / "repositories" / "postgres_read_model.py"
    ).read_text(encoding="utf-8")
    assert "e.evidence_id=t.target_object_id" in source
    assert "p.source_artifact_id=t.target_object_id" in source
    assert "p.relation_type='retracts'" in source
    assert "e.occurred_at>=t.occurred_at" in source
    assert '"completed_follow_up_cases"' in source
    assert '"stage": "case_closed"' in source


def test_work_queue_exposes_domain_artifact_id_for_lifecycle_endpoint():
    source = (
        Path(__file__).resolve().parents[2]
        / "knowledge" / "repositories" / "postgres_read_model.py"
    ).read_text(encoding="utf-8")
    assert "regexp_replace(c.stable_key, '^artifact:', '')" in source


def test_extraction_reuses_equivalent_content_and_parser_manifest():
    pipeline = (
        Path(__file__).resolve().parents[2]
        / "knowledge" / "ingestion_pipeline.py"
    ).read_text(encoding="utf-8")
    repository = (
        Path(__file__).resolve().parents[2]
        / "knowledge" / "repositories" / "postgres_evidence.py"
    ).read_text(encoding="utf-8")
    assert "find_equivalent_extraction" in pipeline
    assert "document.content_hash" in pipeline
    assert "self.extraction_engine.parser_version" in pipeline
    assert "find_equivalent_extraction" in repository
    assert "document_content_hash=%s" in repository
    assert "parser_version=%s" in repository


def test_workspace_exposes_sgf_040_operational_queues_and_confirmations():
    static = Path(__file__).resolve().parents[2] / "product" / "static"
    html = (static / "index.html").read_text(encoding="utf-8")
    script = (static / "workspace.js").read_text(encoding="utf-8")
    assert 'data-queue="impact"' in html
    assert 'data-queue="followup"' in html
    assert 'data-queue="history"' in html
    assert 'id="targetDialog"' in html
    assert "impact_reviews" in script
    assert "completed_follow_up_cases" in script
    assert "/knowledge/impact-reviews/" in script
    assert "evidence-follow-up-cases" in script
    assert "publication-follow-up-cases" in script
    assert 'id="targetConfirm"' in html
    assert 'id="impactEvidenceConfirm"' in html
    assert 'id="impactPublicationConfirm"' in html
    assert 'id="evidenceImpactDialog"' in html
    assert 'id="publicationImpactDialog"' in html
    assert "citation_fidelity" in script
    assert "context_preserved" in script
    assert "epistemic_classification" in script
    assert "relation_type:'retracts'" in script
