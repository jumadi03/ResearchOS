from __future__ import annotations

"""
ResearchOS Architecture Domain Model.

ARCH-001A.7R

Canonical Architecture Fact Domain Model.

Represents a verified architectural fact
discovered from an architectural artifact.

Contains no business logic.
"""

from dataclasses import dataclass, field
from typing import Any

from app.architecture.models.architecture_artifact import (
    ArchitectureArtifact,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ArchitectureFact:
    """
    Canonical Architecture Fact.

    Represents a factual architectural
    property discovered during inspection.
    """

    #
    # Stable fact identifier.
    #
    fact_id: str

    #
    # Related architectural artifact.
    #
    artifact: ArchitectureArtifact

    #
    # Fact name.
    #
    fact_name: str

    #
    # Fact value.
    #
    fact_value: str

    #
    # Optional metadata.
    #
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    @classmethod
    def from_dict(cls, item: dict[str, Any]) -> "ArchitectureFact":
        return cls(
            fact_id=item["fact_id"],
            artifact=ArchitectureArtifact.from_dict(item["artifact"]),
            fact_name=item["fact_name"],
            fact_value=item["fact_value"],
            metadata=item.get("metadata", {}),
        )
