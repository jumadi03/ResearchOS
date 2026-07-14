"""
ResearchOS Modeling Domain Model.

Sprint-003A.1

Canonical Scientific Construct Domain Model.

Represents a scientific construct derived
from one or more ScientificObject instances.

Contains no business logic.
"""

from dataclasses import dataclass, field
from typing import Any

from app.discovery.models.scientific_object import (
    ScientificObject,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ScientificConstruct:
    """
    Canonical Scientific Construct.

    Represents an abstract scientific
    construct supported by empirical
    scientific objects.
    """

    #
    # Stable identifier.
    #
    construct_id: str

    #
    # Canonical construct name.
    #
    name: str

    #
    # Scientific definition.
    #
    definition: str

    #
    # Supporting Scientific Objects.
    #
    supporting_objects: tuple[
        ScientificObject,
        ...
    ]

    #
    # Explicit scientific assumptions.
    #
    assumptions: tuple[
        str,
        ...
    ] = ()

    #
    # Optional metadata.
    #
    metadata: dict[str, Any] = field(
        default_factory=dict
    )