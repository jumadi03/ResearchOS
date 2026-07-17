"""Canonical repository operations and product read-model orchestration."""

from app.knowledge.authentication import KnowledgeRole


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

    def acknowledge_scientific_change(self, change_id, **options):
        return self._required(
            "scientific change acknowledgement"
        ).acknowledge_scientific_change(change_id, **options)

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
        if (
            evidence and evidence.get("review_status") == "pending"
            and principal.has_role(KnowledgeRole.REVIEWER)
        ):
            href = f"/knowledge/evidence/{result['identity']['object_id']}/reviews"
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
            transitions = {
                "draft": "validated", "validated": "ratified", "ratified": "published",
            }
            next_status = transitions.get(artifact.get("status"))
            if next_status and principal.has_role(KnowledgeRole.REVIEWER):
                actions.append({
                    "action": "artifact:transition", "method": "POST",
                    "href": f"/knowledge/artifacts/{result['identity']['object_id']}/transitions",
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
            "roles": sorted(role.value for role in principal.roles),
        }
        return queue

    def get_project_graph(self, project_id: str, **options):
        return self._required("graph reads").get_project_graph(project_id, **options)
