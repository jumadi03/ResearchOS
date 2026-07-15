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
from app.architecture.models.validation_status import ValidationStatus


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

    #
    # Explicit execution outcome. Kept after the pre-existing fields to retain
    # compatibility with callers that construct results positionally.
    #
    status: ValidationStatus = ValidationStatus.NOT_RUN
