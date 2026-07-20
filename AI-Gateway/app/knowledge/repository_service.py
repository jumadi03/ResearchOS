"""Canonical repository operations and product read-model orchestration."""

from app.knowledge.authentication import KnowledgeRole
from app.knowledge.repositories.artifacts import next_artifact_status


class KnowledgeRepositoryService:
    def __init__(self, repository) -> None:
        self.repository = repository

    def _required(self, purpose: str):
        if self.repository is None:
            raise RuntimeError(f"Canonical repository is required for {purpose}")
        return self.repository

    def review_evidence(self, evidence_object_id: str, **options):
        return self._required("evidence review").review_evidence(
            evidence_object_id, **options
        )

    def transition_artifact(self, artifact_id: str, **options):
        return self._required("artifact lifecycle").transition_artifact(
            artifact_id, **options
        )

    def enqueue_semantic_index(self, **options):
        return self._required("semantic indexing").enqueue_semantic_index(**options)

    def semantic_search(self, **options):
        return self._required("semantic retrieval").semantic_search(**options)

    def create_source_watch(self, baseline, **options):
        return self._required("continuous monitoring").create_source_watch(
            baseline, **options
        )

    def list_source_watches(self, project_id):
        return self._required("continuous monitoring").list_source_watches(
            project_id
        )

    def transition_source_watch(self, watch_id, **options):
        return self._required("continuous monitoring").transition_source_watch(
            watch_id, **options
        )

    def list_monitoring_runs(self, watch_id):
        return self._required("continuous monitoring").list_monitoring_runs(
            watch_id
        )

    def list_scientific_changes(self, watch_id, **options):
        return self._required("continuous monitoring").list_scientific_changes(
            watch_id, **options
        )

    def acknowledge_scientific_change(self, change_id, **options):
        return self._required(
            "scientific change acknowledgement"
        ).acknowledge_scientific_change(change_id, **options)

    def resolve_impact_review(self, change_id, **options):
        return self._required(
            "scientific impact review"
        ).resolve_impact_review(change_id, **options)

    def select_follow_up_target(self, resolution_id, **options):
        return self._required(
            "follow-up case target selection"
        ).select_follow_up_target(resolution_id, **options)

    def list_projects(self):
        return self._required("product reads").list_projects()

    def list_objects(self, project_id: str, **options):
        return self._required("product reads").list_objects(project_id, **options)

    def get_object_read_model(self, object_ref: str, project_id: str, principal):
        result = self._required("product reads").get_object_read_model(
            object_ref, project_id
        )
        actions = []
        evidence = result.get("evidence")
        artifact = result.get("artifact")
        stable_key = result["identity"].get("stable_key", "")
        domain_object_id = (
            stable_key.split(":", 1)[1]
            if ":" in stable_key
            else result["identity"]["object_id"]
        )
        if (
            evidence and evidence.get("review_status") == "pending"
            and principal.has_role(KnowledgeRole.REVIEWER)
        ):
            href = f"/knowledge/evidence/{domain_object_id}/reviews"
            actions.extend((
                {"action": "evidence:accept", "method": "POST", "href": href},
                {"action": "evidence:reject", "method": "POST", "href": href},
            ))
        if (
            evidence and evidence.get("review_status") == "accepted"
            and principal.has_role(KnowledgeRole.INDEXER)
        ):
            actions.append({
                "action": "semantic:index", "method": "POST",
                "href": "/knowledge/semantic-index/jobs",
            })
        if artifact:
            next_status = next_artifact_status(artifact.get("status"))
            required_role = (
                KnowledgeRole.PUBLISHER
                if next_status == "published"
                else KnowledgeRole.REVIEWER
            )
            if next_status and principal.has_role(required_role):
                actions.append({
                    "action": "artifact:transition", "method": "POST",
                    "href": f"/knowledge/artifacts/{domain_object_id}/transitions",
                    "to_status": next_status,
                })
            if (
                artifact.get("status") in {"validated", "ratified", "published"}
                and principal.has_role(KnowledgeRole.INDEXER)
            ):
                actions.append({
                    "action": "semantic:index", "method": "POST",
                    "href": "/knowledge/semantic-index/jobs",
                })
        result["permissions"] = {
            "can_read": True,
            "roles": sorted(role.value for role in principal.roles),
            "available_actions": actions,
        }
        return result

    def get_work_queue(self, project_id: str, principal):
        queue = self._required("workflow reads").get_work_queue(project_id)
        queue["permissions"] = {
            "can_review": principal.has_role(KnowledgeRole.REVIEWER),
            "can_index": principal.has_role(KnowledgeRole.INDEXER),
            "can_publish": principal.has_role(KnowledgeRole.PUBLISHER),
            "roles": sorted(role.value for role in principal.roles),
        }
        for case in queue.get("follow_up_cases", []):
            authorized = (
                principal.has_role(KnowledgeRole.REVIEWER)
                if case["required_role"] == "reviewer"
                else principal.has_role(KnowledgeRole.PUBLISHER)
            )
            case["action_authorized"] = authorized
            case["available_action"] = None
            target = case.get("target_selection")
            if authorized and case.get("status") == "target_selected" and target:
                if case["case_type"] == "evidence_review":
                    stable_key = target.get("target_stable_key") or ""
                    evidence_id = (
                        stable_key.removeprefix("evidence:")
                        if stable_key.startswith("evidence:") else None
                    )
                    if evidence_id:
                        case["available_action"] = {
                            "action": "evidence:review",
                            "method": "POST",
                            "href": f"/knowledge/evidence/{evidence_id}/reviews",
                            "requires_confirmation": True,
                            "audit_workflow": "evidence_review_event",
                            "reviewed_statement_hash": target.get(
                                "reviewed_statement_hash"
                            ),
                            "extraction_manifest_hash": target.get(
                                "extraction_manifest_hash"
                            ),
                        }
                elif case["case_type"] == "publication_review":
                    stable_key = target.get("target_stable_key") or ""
                    publication_id = (
                        stable_key.removeprefix("artifact:")
                        if stable_key.startswith("artifact:") else None
                    )
                    if publication_id:
                        case["available_action"] = {
                            "action": "publication:retract",
                            "method": "POST",
                            "href": (
                                f"/knowledge/publications/{publication_id}/relationships"
                            ),
                            "relation_type": "retracts",
                            "requires_confirmation": True,
                            "audit_workflow": "publication_relationship",
                        }
        return queue

    def get_project_graph(self, project_id: str, **options):
        return self._required("graph reads").get_project_graph(project_id, **options)

    def get_discovery_workflow_state(self, project_id: str, record_ids):
        return self._required("workflow reads").get_discovery_workflow_state(
            project_id, tuple(record_ids)
        )
