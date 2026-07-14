"""
ResearchOS Modeling Domain Model.

Sprint-003A.3

Canonical Scientific Model Domain Model.

Represents an integrated scientific model
consisting of constructs and relationships.

Contains no business logic.
"""

from dataclasses import dataclass, field
from typing import Any

from app.modeling.models.scientific_construct import (
    ScientificConstruct,
)

from app.modeling.models.scientific_relationship import (
    ScientificRelationship,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ScientificModel:
    """
    Canonical Scientific Model.
    """

    #
    # Stable identifier.
    #
    model_id: str

    #
    # Canonical model name.
    #
    name: str

    #
    # Scientific explanation.
    #
    description: str

    #
    # Member constructs.
    #
    constructs: tuple[
        ScientificConstruct,
        ...
    ]

    #
    # Relationships connecting constructs.
    #
    relationships: tuple[
        ScientificRelationship,
        ...
    ]

    #
    # Optional metadata.
    #
    metadata: dict[str, Any] = field(
        default_factory=dict
    )