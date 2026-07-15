"""
ResearchOS Architecture Domain Model.

ARCH-001A.7

Canonical Architecture Artifact
Domain Model.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(
    frozen=True,
    slots=True,
)
class ArchitectureArtifact:
    """
    Canonical Architecture Artifact.

    Represents one architectural
    artifact discovered by the
    Architecture Engine.
    """

    #
    # Stable artifact identifier.
    #
    artifact_id: str

    #
    # Canonical artifact name.
    #
    name: str

    #
    # Artifact category.
    #
    artifact_type: str

    #
    # Fully-qualified module path.
    #
    module: str

    #
    # Canonical source representation.
    #
    source: str

    #
    # Optional metadata.
    #
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    @classmethod
    def from_dict(cls, item: dict[str, Any]) -> "ArchitectureArtifact":
        return cls(**item)
