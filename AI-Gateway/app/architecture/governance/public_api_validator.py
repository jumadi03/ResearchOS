"""
ResearchOS Public API Validator.

Architecture Law:

ALA-API-001

Every package exposing canonical
contracts must provide a package-level
public namespace.
"""

from dataclasses import dataclass

from .validator import Validator

from ..models import (
    ArchitectureValidationResult,
    ArchitectureArtifact,
    ArchitectureFact,
    ArchitectureViolation,
    ResolutionContext,
    ValidationStatus,
)
from hashlib import sha256


@dataclass(
    frozen=True,
    slots=True,
)
class PublicAPIValidator(Validator):
    """
    Foundation implementation for
    ALA-API-001.

    Filesystem inspection will be
    introduced in a later sprint.
    """

    def validate(
        self,
    ) -> ArchitectureValidationResult:
        """
        Validate ALA-API-001.

        Foundation implementation.
        """

        if self.graph is None:
            return ArchitectureValidationResult(
                validation_id="PUBLIC-API",
                artifact_name="PublicAPIValidator",
                status=ValidationStatus.NOT_RUN,
                metadata={"reason": "ARCHITECTURE_GRAPH_REQUIRED"},
            )

        modules = {
            node.canonical_name: node
            for node in self.graph.nodes
            if node.node_type == "Module" and not node.metadata.get("external")
        }
        packages: dict[str, object] = {}
        laws_by_package: dict[tuple[str, str], object] = {}
        errors: list[str] = []

        for module in modules.values():
            resolved = self.resolution.resolve_context(
                ResolutionContext(
                    category="PublicAPI",
                    node_type="Module",
                    source_path=module.source_path,
                    as_of=self.as_of,
                )
            )
            package = module.canonical_name.rpartition(".")[0]
            if not package:
                continue
            packages.setdefault(package, module)
            for law in resolved.applicable_laws:
                if law.condition.get("type") != "REQUIRE_PACKAGE_INIT":
                    errors.append(f"{law.law_id}:UNSUPPORTED_CONDITION")
                    continue
                laws_by_package[(law.law_id, package)] = law

        violations: list[ArchitectureViolation] = []
        for (law_id, package), law in sorted(laws_by_package.items()):
            required_module = f"{package}.__init__"
            if required_module in modules:
                continue
            source = packages[package]
            fingerprint = sha256(
                f"{law_id}:{package}:missing-init".encode("utf-8")
            ).hexdigest()[:16]
            artifact = ArchitectureArtifact(
                artifact_id=source.node_id,
                name=package,
                artifact_type="Package",
                module=package,
                source="",
                metadata={"path": source.source_path},
            )
            fact = ArchitectureFact(
                fact_id=f"fact:{fingerprint}",
                artifact=artifact,
                fact_name="PUBLIC_NAMESPACE_MODULE",
                fact_value=required_module,
            )
            violations.append(
                ArchitectureViolation(
                    violation_id=f"violation:{fingerprint}",
                    law=law,
                    fact=fact,
                    message=f"Package {package} does not provide {required_module}.",
                    metadata={
                        "package": package,
                        "required_module": required_module,
                        "source_path": source.source_path,
                        "remediation": law.remediation,
                    },
                )
            )

        evaluated_ids = sorted({key[0] for key in laws_by_package})
        status = ValidationStatus.FAIL if violations else ValidationStatus.PASS
        if errors:
            status = ValidationStatus.ERROR
        elif not evaluated_ids:
            status = ValidationStatus.NOT_APPLICABLE
        return ArchitectureValidationResult(
            validation_id="PUBLIC-API",
            artifact_name=self.graph.graph_id,
            status=status,
            violations=tuple(sorted(violations, key=lambda item: item.violation_id)),
            metadata={
                "resolved_laws": len(evaluated_ids),
                "evaluated_law_ids": evaluated_ids,
                "errors": sorted(set(errors)),
                "graph_hash": self.graph.content_hash,
            },
        )
