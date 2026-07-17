"""Fail-closed projection of canonical repository artifacts for FMA-007."""

from __future__ import annotations

from collections import Counter

from app.architecture.models import ArchitectureGraph

from .dashboard_models import (
    RepositoryDashboardFile,
    RepositoryDashboardHealth,
    RepositoryDashboardSnapshot,
)
from .file_registry_models import RepositoryFileRegistry
from .health_models import RepositoryHealthReport
from .verification_models import RepositoryVerificationReport


class RepositoryDashboardProjector:
    """Build a read-only view without recomputing canonical decisions."""

    @staticmethod
    def _validate(
        registry: RepositoryFileRegistry,
        verification: RepositoryVerificationReport,
        graph: ArchitectureGraph,
        health: RepositoryHealthReport,
    ) -> None:
        if not registry.verify():
            raise ValueError("Repository dashboard requires a valid file registry")
        if not verification.verify():
            raise ValueError(
                "Repository dashboard requires a valid verification report"
            )
        if not graph.verify():
            raise ValueError("Repository dashboard requires a valid architecture graph")
        if not health.verify():
            raise ValueError("Repository dashboard requires a valid health report")

        project_names = {
            registry.project_name,
            verification.project_name,
            graph.project_name,
            health.project_name,
        }
        revisions = {
            registry.source_revision,
            verification.source_revision,
            graph.source_revision,
            health.source_revision,
        }
        if len(project_names) != 1:
            raise ValueError("Repository dashboard source project mismatch")
        if len(revisions) != 1 or None in revisions:
            raise ValueError("Repository dashboard source revision mismatch")
        if (
            verification.registry_id != registry.registry_id
            or verification.registry_hash != registry.content_hash
            or health.registry_id != registry.registry_id
            or health.registry_hash != registry.content_hash
            or health.verification_report_id != verification.report_id
            or health.verification_report_hash != verification.content_hash
            or health.graph_id != graph.graph_id
            or health.graph_hash != graph.content_hash
        ):
            raise ValueError("Repository dashboard source provenance mismatch")

        project_nodes = [
            node for node in graph.nodes
            if node.node_id == f"project:{registry.project_name}"
        ]
        if len(project_nodes) != 1:
            raise ValueError(
                "Repository dashboard requires one canonical project node"
            )
        trace = project_nodes[0].metadata.get("repository_traceability", {})
        if (
            trace.get("registry_id") != registry.registry_id
            or trace.get("registry_hash") != registry.content_hash
            or trace.get("verification_report_id") != verification.report_id
            or trace.get("verification_report_hash") != verification.content_hash
        ):
            raise ValueError("Repository dashboard graph provenance mismatch")

    def project(
        self,
        registry: RepositoryFileRegistry,
        verification: RepositoryVerificationReport,
        graph: ArchitectureGraph,
        health: RepositoryHealthReport,
    ) -> RepositoryDashboardSnapshot:
        self._validate(registry, verification, graph, health)
        files = tuple(
            RepositoryDashboardFile(
                file_id=item.file_id,
                path=item.current_path,
                content_hash=item.content_hash,
                classification=item.classification,
                size=item.size,
                owner=item.owner,
                subsystem=item.subsystem,
                engine=item.engine,
                capability=item.capability,
                lifecycle=item.lifecycle.value if item.lifecycle else None,
                governance_state=item.governance_state,
                policy_ids=item.policy_ids,
                exception_ids=item.exception_ids,
            )
            for item in registry.entries
        )
        checks = tuple(
            RepositoryDashboardHealth(
                check_id=item.check_id,
                category=item.category,
                outcome=item.outcome,
                summary=item.summary,
                affected_count=len(item.affected_file_ids),
                evidence_hash=item.evidence_hash,
            )
            for item in health.checks
        )
        snapshot = RepositoryDashboardSnapshot(
            snapshot_id="",
            project_name=registry.project_name,
            source_revision=registry.source_revision,
            registry_id=registry.registry_id,
            registry_hash=registry.content_hash,
            verification_report_id=verification.report_id,
            verification_report_hash=verification.content_hash,
            graph_id=graph.graph_id,
            graph_hash=graph.content_hash,
            health_report_id=health.report_id,
            health_report_hash=health.content_hash,
            health_as_of=health.as_of,
            files=files,
            health=checks,
            inventory_counts=tuple(sorted(Counter(
                item.classification.value for item in registry.entries
            ).items())),
            governance_counts=registry.governance_counts,
            verification_counts=verification.outcome_counts,
            health_counts=health.outcome_counts,
            architecture_node_counts=tuple(sorted(Counter(
                item.node_type for item in graph.nodes
            ).items())),
            architecture_edge_counts=tuple(sorted(Counter(
                item.relation_type for item in graph.edges
            ).items())),
        ).finalized()
        if not snapshot.verify():
            raise ValueError("Repository dashboard projection is invalid")
        return snapshot
