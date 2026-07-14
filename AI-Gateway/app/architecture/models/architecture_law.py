"""
ResearchOS Architecture Domain Model.

ARCH-001A.6

Canonical Architecture Law Domain Model.

Represents a canonical architecture law
used by the Architecture Engine.

Contains no business logic.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(
    frozen=True,
    slots=True,
)
class ArchitectureLaw:
    """
    Canonical Architecture Law.

    Represents one immutable architecture
    law used during validation.
    """

    #
    # Stable law identifier.
    #
    law_id: str

    #
    # Canonical law title.
    #
    title: str

    #
    # Human-readable description.
    #
    description: str

    #
    # Architecture law version.
    #
    version: str

    #
    # Optional metadata.
    #
    metadata: dict[str, Any] = field(
        default_factory=dict
    )