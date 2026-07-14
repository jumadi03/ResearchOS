"""
ResearchOS Discovery Domain Model.

SDC-002

Canonical Phenomenon Domain Model.

Represents a scientific phenomenon
identified through evidence integration.

This model contains no business logic.
"""

from dataclasses import dataclass, field
from typing import Any

from .scientific_evidence import ScientificEvidence


@dataclass(
    frozen=True,
    slots=True,
)
class ScientificPhenomenon:
    """
    Canonical Phenomenon Domain Model.

    Represents a scientific phenomenon
    synthesized from validated evidence.
    """

    #
    # Stable identifier.
    #
    phenomenon_id: str

    #
    # Human-readable description.
    #
    description: str

    #
    # Supporting evidence.
    #
    evidences: tuple[
        ScientificEvidence,
        ...
    ]

    #
    # Optional metadata.
    #
    metadata: dict[str, Any] = field(
        default_factory=dict
    )