"""
ResearchOS Architecture Domain Model.

ARCH-001A.5

Canonical Architecture Validation Result
Domain Model.

Represents the validation result for a
single architectural artifact.

Contains no business logic.
"""

from dataclasses import dataclass, field
from typing import Any

from app.architecture.models.architecture_violation import (
    ArchitectureViolation,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ArchitectureValidationResult:
    """
    Canonical Architecture Validation Result.

    Represents the complete validation
    outcome for one architectural artifact.
    """

    #
    # Stable validation identifier.
    #
    validation_id: str

    #
    # Validated artifact name.
    #
    artifact_name: str

    #
    # Violations discovered during validation.
    #
    violations: tuple[
        ArchitectureViolation,
        ...
    ] = ()

    #
    # Optional metadata.
    #
    metadata: dict[str, Any] = field(
        default_factory=dict
    )