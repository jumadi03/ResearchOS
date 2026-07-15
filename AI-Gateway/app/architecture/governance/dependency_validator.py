"""
ResearchOS Dependency Validator.

Foundation implementation of the
Architecture Validator Framework.
"""

from dataclasses import dataclass
from fnmatch import fnmatch
from hashlib import sha256

from app.architecture.governance.validator import Validator
from app.architecture.models.architecture_validation_result import (
    ArchitectureValidationResult,
)
from app.architecture.models.architecture_artifact import ArchitectureArtifact
from app.architecture.models.architecture_fact import ArchitectureFact
from app.architecture.models.architecture_violation import ArchitectureViolation
from app.architecture.models.law_resolution_result import ResolutionContext
from app.architecture.models.validation_status import ValidationStatus


@dataclass(frozen=True, slots=True)
class DependencyValidator(Validator):
    """
    Foundation Dependency Validator.

    Currently verifies that the validator
    can obtain applicable laws from the
    Law Resolution pipeline.
    """

    def validate(self) -> ArchitectureValidationResult:
        """
        Foundation implementation.

        Verifies that the Law Resolution
        pipeline is operational.
        """

        if self.graph is None:
            return ArchitectureValidationResult(
                validation_id="DEPENDENCY",
                artifact_name="DependencyValidator",
                status=ValidationStatus.NOT_RUN,
                metadata={"reason": "ARCHITECTURE_GRAPH_REQUIRED"},
            )

        node_by_id = {node.node_id: node for node in self.graph.nodes}
        import_edges = tuple(
            edge for edge in self.graph.edges if edge.relation_type == "IMPORTS"
        )
        violations: list[ArchitectureViolation] = []
        evaluated_laws: set[str] = set()
        errors: list[str] = []

        for source in self.graph.nodes:
            if source.node_type != "Module" or source.metadata.get("external"):
                continue
            resolved = self.resolution.resolve_context(
                ResolutionContext(
                    category="Dependency",
                    node_type=source.node_type,
                    source_path=source.source_path,
                    as_of=self.as_of,
                )
            )
            for law in resolved.applicable_laws:
                relation = law.condition.get("relation")
                forbidden_target = law.condition.get("forbidden_target")
                if relation != "IMPORTS" or not isinstance(forbidden_target, str):
                    errors.append(f"{law.law_id}:UNSUPPORTED_CONDITION")
                    continue
                evaluated_laws.add(law.law_id)
                for edge in import_edges:
                    if edge.source_id != source.node_id:
                        continue
                    target = node_by_id[edge.target_id]
                    if not fnmatch(target.canonical_name, forbidden_target):
                        continue
                    fingerprint = sha256(
                        f"{law.law_id}:{edge.edge_id}".encode("utf-8")
                    ).hexdigest()[:16]
                    artifact = ArchitectureArtifact(
                        artifact_id=source.node_id,
                        name=source.canonical_name,
                        artifact_type="Module",
                        module=source.canonical_name,
                        source="",
                        metadata={"path": source.source_path},
                    )
                    fact = ArchitectureFact(
                        fact_id=f"fact:{fingerprint}",
                        artifact=artifact,
                        fact_name="IMPORTS",
                        fact_value=target.canonical_name,
                        metadata={
                            "edge_id": edge.edge_id,
                            "lines": edge.metadata.get("lines", []),
                        },
                    )
                    violations.append(
                        ArchitectureViolation(
                            violation_id=f"violation:{fingerprint}",
                            law=law,
                            fact=fact,
                            message=(
                                f"{source.canonical_name} imports forbidden target "
                                f"{target.canonical_name}."
                            ),
                            metadata={
                                "source_node_id": source.node_id,
                                "target_node_id": target.node_id,
                                "source_path": source.source_path,
                                "lines": edge.metadata.get("lines", []),
                                "remediation": law.remediation,
                            },
                        )
                    )

        status = ValidationStatus.FAIL if violations else ValidationStatus.PASS
        if errors:
            status = ValidationStatus.ERROR
        elif not evaluated_laws:
            status = ValidationStatus.NOT_APPLICABLE
        return ArchitectureValidationResult(
            validation_id="DEPENDENCY",
            artifact_name=self.graph.graph_id,
            status=status,
            violations=tuple(sorted(violations, key=lambda item: item.violation_id)),
            metadata={
                "resolved_laws": len(evaluated_laws),
                "evaluated_law_ids": sorted(evaluated_laws),
                "errors": sorted(set(errors)),
                "graph_hash": self.graph.content_hash,
            },
        )
