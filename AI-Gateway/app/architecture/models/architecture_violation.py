"""
ResearchOS Architecture Domain Model.

ARCH-001A.4

Canonical Architecture Violation Domain Model.

Represents a violation of an
Architecture Law discovered
during validation.

Contains no business logic.
"""

from dataclasses import dataclass, field
from typing import Any

from app.architecture.models.architecture_fact import (
    ArchitectureFact,
)

from app.architecture.models.architecture_law import (
    ArchitectureLaw,
)

@dataclass(
    frozen=True,
    slots=True,
)
class ArchitectureViolation:
    """
    Canonical Architecture Violation.

    Represents a violation produced
    from validating an architectural
    fact against an Architecture Law.
    """

    #
    # Stable violation identifier.
    #
    violation_id: str

    #
    # Related architecture law.
    #
    law: ArchitectureLaw

    #
    # Violated architecture fact.
    #
    fact: ArchitectureFact

    #
    # Human-readable explanation.
    #
    message: str

    #
    # Optional metadata.
    #
    metadata: dict[str, Any] = field(
        default_factory=dict)

    @classmethod
    def from_dict(cls, item: dict[str, Any]) -> "ArchitectureViolation":
        return cls(
            violation_id=item["violation_id"],
            law=ArchitectureLaw.from_dict(item["law"]),
            fact=ArchitectureFact.from_dict(item["fact"]),
            message=item["message"],
            metadata=item.get("metadata", {}),
        )
