"""
ResearchOS Architecture Domain Model.

ARCH-001A.8

Canonical Architecture Symbol.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(
    frozen=True,
    slots=True,
)
class ArchitectureSymbol:
    """
    Canonical Architecture Symbol.

    Represents one symbol discovered
    inside an ArchitectureArtifact.
    """

    #
    # Symbol name.
    #
    name: str

    #
    # Symbol kind.
    #
    symbol_type: str

    #
    # Source line.
    #
    line: int

    #
    # Optional metadata.
    #
    metadata: dict[str, Any] = field(
        default_factory=dict
    )