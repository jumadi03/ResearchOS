"""
ResearchOS Architecture Compliance Engine.

Coordinates architecture validators.
"""

from dataclasses import dataclass, replace

from .validator_registry import ValidatorRegistry

from ..models import (
    ArchitectureValidationResult,
    ArchitectureGraph,
    ValidationReport,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ComplianceEngine:
    """
    Foundation Compliance Engine.

    Coordinates validator execution.

    Validator management is delegated
    to ValidatorRegistry.
    """

    registry: ValidatorRegistry

    def validator_count(self) -> int:
        """
        Return the number of registered
        validators.
        """
        return self.registry.count()

    def validate(
        self,
        graph: ArchitectureGraph | None = None,
        *,
        as_of: str | None = None,
    ) -> ValidationReport:
        """
        Execute every registered validator.

        Foundation implementation.
        """

        results: list[
            ArchitectureValidationResult
        ] = []

        for validator in self.registry.get_all():
            active_validator = validator
            if graph is not None or as_of is not None:
                active_validator = replace(validator, graph=graph, as_of=as_of)
            results.append(
                active_validator.validate()
            )

        return ValidationReport(
            validation_results=tuple(results),
            metadata={
                "graph_id": graph.graph_id if graph else None,
                "graph_hash": graph.content_hash if graph else None,
                "as_of": as_of,
            },
        )
