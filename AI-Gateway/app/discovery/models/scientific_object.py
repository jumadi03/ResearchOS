"""
ResearchOS Discovery Domain Model.

SDC-002

Canonical Scientific Object Domain Model.

Represents a scientific object discovered
from one or more scientific phenomena.

This model contains no business logic.
"""

from dataclasses import dataclass, field
from typing import Any

from .scientific_phenomenon import ScientificPhenomenon


@dataclass(
    frozen=True,
    slots=True,
)
class ScientificObject:
    """
    Canonical Scientific Object Domain Model.

    Represents a scientific object identified
    from one or more scientific phenomena.

    This is the final output of the
    Discovery Capability.
    """

    #
    # Stable identifier.
    #
    object_id: str

    #
    # Human-readable name.
    #
    name: str

    #
    # Scientific description.
    #
    description: str

    #
    # Supporting phenomena.
    #
    phenomena: tuple[
        ScientificPhenomenon,
        ...
    ]

    #
    # Optional metadata.
    #
    metadata: dict[str, Any] = field(
        default_factory=dict
    )