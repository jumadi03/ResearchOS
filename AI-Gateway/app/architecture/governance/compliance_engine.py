"""
ResearchOS Architecture Compliance Engine.

Coordinates architecture validators.
"""

from dataclasses import dataclass

from .validator_registry import ValidatorRegistry

from ..models import (
    ArchitectureValidationResult,
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
    ) -> ValidationReport:
        """
        Execute every registered validator.

        Foundation implementation.
        """

        results: list[
            ArchitectureValidationResult
        ] = []

        for validator in self.registry.get_all():
            results.append(
                validator.validate()
            )

        return ValidationReport(
            validation_results=tuple(results),
        )