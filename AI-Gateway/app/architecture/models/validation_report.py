"""
ResearchOS Architecture Domain Model.

Canonical Validation Report.

Represents the complete result of an
architecture validation execution.

Contains no business logic.
"""

from dataclasses import dataclass
from typing import Any

from app.architecture.models.architecture_validation_result import (
    ArchitectureValidationResult,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ValidationReport:
    """
    Canonical Validation Report.

    Aggregate root for an architecture
    validation execution.
    """

    validation_results: tuple[
        ArchitectureValidationResult,
        ...
    ] = ()

    metadata: dict[str, Any] | None = None