"""Integrate repository traceability into the canonical Architecture Graph."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath

from app.architecture.graph_builder import ArchitectureGraphBuilder
from app.architecture.models import (
    ArchitectureEdge,
    ArchitectureGraph,
    ArchitectureNode,
)

from .file_registry_models import RepositoryFileRegistry
from .models import RepositoryFileClassification
from .policy_registry import RepositoryPolicyRegistry
from .verification_models import RepositoryVerificationReport


@dataclass(frozen=True, slots=True)
class RepositoryTraceabilityGraphBuilder:
    root: Path
    graph_source_prefix: str

    def _prefix(self) -> PurePosixPath:
        normalized = self.graph_source_prefix.replace("\\", "/").rstrip("/")
        prefix = PurePosixPath(normalized)
        if (
            not normalized
            or prefix.is_absolute()
            or any(part in {"", ".", ".."} for part in prefix.parts)
        ):
            raise ValueError("Graph source prefix must be repository-relative")
        return prefix

    @staticmethod
    def _identity(kind: str, value: str) -> str:
        digest = sha256(
            json.dumps(
                {"kind": kind, "value": value},
                separators=(",", ":"), sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()[:24]
        return f"{kind.lower()}:{digest}"

    @staticmethod
    def _edge(
        source_id: str,
        target_id: str,
        relation_type: str,
        metadata: dict[str, object] | None = None,
    ) -> ArchitectureEdge:
        payload = json.dumps(
            {
                "source_id": source_id,
                "target_id": target_id,
                "relation_type": relation_type,
            },
            separators=(",", ":"), sort_keys=True,
        )
        return ArchitectureEdge(
            edge_id=f"trace:{sha256(payload.encode('utf-8')).hexdigest()[:24]}",
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            metadata=metadata or {},
        )

    @staticmethod
    def _validate_inputs(
        registry: RepositoryFileRegistry,
        policies: RepositoryPolicyRegistry,
        verification: RepositoryVerificationReport,
    ) -> None:
        if not registry.verify():
            raise ValueError("Repository file registry integrity verification failed")
        if not policies.bundle.verify():
            raise ValueError("Repository policy integrity verification failed")
        if not verification.verify():
            raise ValueError(
                "Repository verification report integrity verification failed"
            )
        if len({
            registry.project_name,
            policies.bundle.project_name,
            verification.project_name,
        }) != 1:
            raise ValueError("Traceability inputs do not describe one project")
        if registry.source_revision != verification.source_revision:
            raise ValueError("Traceability source revisions do not match")
        if (
            registry.policy_bundle_id != policies.bundle.bundle_id
            or registry.policy_bundle_hash != policies.bundle.content_hash
            or verification.registry_id != registry.registry_id
            or verification.registry_hash != registry.content_hash
            or verification.policy_bundle_id != policies.bundle.bundle_id
            or verification.policy_bundle_hash != policies.bundle.content_hash
        ):
            raise ValueError("Traceability input provenance does not match")

    def build(
        self,
        registry: RepositoryFileRegistry,
        policies: RepositoryPolicyRegistry,
        verification: RepositoryVerificationReport,
    ) -> ArchitectureGraph:
        self._validate_inputs(registry, policies, verification)
        prefix = self._prefix()
        prefix_text = prefix.as_posix() + "/"
        python_entries = tuple(
            item for item in registry.entries
            if item.current_path.startswith(prefix_text)
            and item.extension == ".py"
            and item.classification in {
                RepositoryFileClassification.CODE,
                RepositoryFileClassification.TEST,
            }
        )
        if not python_entries:
            raise ValueError("No canonical Python sources match graph prefix")
        relative_to_entry = {
            item.current_path[len(prefix_text):]: item
            for item in python_entries
        }
        graph = ArchitectureGraphBuilder(
            root=self.root,
            project_name=registry.project_name,
            source_revision=registry.source_revision,
            source_paths=tuple(sorted(relative_to_entry)),
            schema_version="1.1",
        ).build()

        nodes = {item.node_id: item for item in graph.nodes}
        edges = {item.edge_id: item for item in graph.edges}
        project_id = f"project:{registry.project_name}"
        project = nodes[project_id]
        nodes[project_id] = replace(
            project,
            metadata={
                **project.metadata,
                "repository_traceability": {
                    "registry_id": registry.registry_id,
                    "registry_hash": registry.content_hash,
                    "policy_bundle_id": policies.bundle.bundle_id,
                    "policy_bundle_hash": policies.bundle.content_hash,
                    "verification_report_id": verification.report_id,
                    "verification_report_hash": verification.content_hash,
                    "verification_as_of": verification.as_of,
                },
            },
        )

        def add_node(node: ArchitectureNode) -> None:
            existing = nodes.get(node.node_id)
            if existing is not None and existing != node:
                raise ValueError(f"Traceability node identity conflict: {node.node_id}")
            nodes[node.node_id] = node

        def add_edge(edge: ArchitectureEdge) -> None:
            existing = edges.get(edge.edge_id)
            if existing is not None and existing != edge:
                raise ValueError(f"Traceability edge identity conflict: {edge.edge_id}")
            edges[edge.edge_id] = edge

        for entry in registry.entries:
            add_node(ArchitectureNode(
                node_id=entry.file_id,
                node_type="File",
                canonical_name=entry.current_path,
                source_path=entry.current_path,
                metadata={
                    **asdict(entry),
                    "classification": entry.classification.value,
                    "lifecycle": (
                        entry.lifecycle.value if entry.lifecycle else None
                    ),
                    "governance_state": entry.governance_state.value,
                },
            ))
            add_edge(self._edge(project_id, entry.file_id, "CONTAINS"))

        policy_node_ids = {}
        for policy in policies.bundle.policies:
            node_id = f"repository-policy-declaration:{policy.policy_id}"
            policy_node_ids[policy.policy_id] = node_id
            add_node(ArchitectureNode(
                node_id=node_id,
                node_type="RepositoryPolicy",
                canonical_name=policy.policy_id,
                metadata={
                    **asdict(policy),
                    "policy_type": type(policy).__name__,
                },
            ))
        for entry in registry.entries:
            for policy_id in entry.policy_ids:
                try:
                    policy_node_id = policy_node_ids[policy_id]
                except KeyError as exc:
                    raise ValueError(
                        f"File references unknown repository policy: {policy_id}"
                    ) from exc
                add_edge(self._edge(
                    entry.file_id, policy_node_id, "GOVERNED_BY",
                ))

        engine_to_subsystem: dict[str, str] = {}
        capability_to_engine: dict[str, str] = {}
        for entry in registry.entries:
            if not all((
                entry.subsystem, entry.engine, entry.capability, entry.owner,
            )):
                continue
            subsystem_id = self._identity("subsystem", entry.subsystem)
            engine_id = self._identity("engine", entry.engine)
            capability_id = self._identity("capability", entry.capability)
            if (
                engine_id in engine_to_subsystem
                and engine_to_subsystem[engine_id] != subsystem_id
            ):
                raise ValueError("Engine has ambiguous subsystem provenance")
            if (
                capability_id in capability_to_engine
                and capability_to_engine[capability_id] != engine_id
            ):
                raise ValueError("Capability has ambiguous engine provenance")
            engine_to_subsystem[engine_id] = subsystem_id
            capability_to_engine[capability_id] = engine_id
            add_node(ArchitectureNode(
                subsystem_id, "Subsystem", entry.subsystem,
            ))
            add_node(ArchitectureNode(engine_id, "Engine", entry.engine))
            add_node(ArchitectureNode(
                capability_id, "Capability", entry.capability,
                metadata={"owner": entry.owner},
            ))
            add_edge(self._edge(
                project_id, subsystem_id, "HAS_SUBSYSTEM",
            ))
            add_edge(self._edge(
                subsystem_id, engine_id, "HAS_ENGINE",
            ))
            add_edge(self._edge(
                engine_id, capability_id, "HAS_CAPABILITY",
            ))
            add_edge(self._edge(
                capability_id, entry.file_id, "OWNS",
            ))

        for node in tuple(nodes.values()):
            if (
                node.node_type != "Module"
                or node.metadata.get("external")
            ):
                continue
            entry = relative_to_entry.get(node.source_path or "")
            if entry is None:
                raise ValueError(
                    f"Canonical module has no exact file identity: {node.node_id}"
                )
            add_edge(self._edge(
                node.node_id, entry.file_id, "REPRESENTED_BY",
                {"exact_path": node.source_path},
            ))

        registered_file_ids = {item.file_id for item in registry.entries}
        for evaluation in verification.evaluations:
            if evaluation.file_id not in registered_file_ids:
                raise ValueError(
                    "Repository evaluation references an unknown file identity"
                )
            add_node(ArchitectureNode(
                node_id=evaluation.evaluation_id,
                node_type="RepositoryEvaluation",
                canonical_name=evaluation.evaluation_id,
                source_path=evaluation.path,
                metadata={
                    **asdict(evaluation),
                    "domain": evaluation.domain.value,
                    "outcome": evaluation.outcome.value,
                },
            ))
            add_edge(self._edge(
                evaluation.evaluation_id,
                evaluation.file_id,
                "EVALUATES",
            ))
            if evaluation.policy_id is not None:
                if evaluation.policy_id not in policy_node_ids:
                    raise ValueError(
                        "Repository evaluation references an unknown policy"
                    )
                add_edge(self._edge(
                    evaluation.evaluation_id,
                    policy_node_ids[evaluation.policy_id],
                    "APPLIES_POLICY",
                ))

        enriched = ArchitectureGraph(
            graph_id="",
            project_name=graph.project_name,
            nodes=tuple(nodes.values()),
            edges=tuple(edges.values()),
            source_revision=graph.source_revision,
            schema_version="1.1",
        ).finalized()
        if not enriched.verify():
            raise ValueError("Traceability Architecture Graph is invalid")
        return enriched
