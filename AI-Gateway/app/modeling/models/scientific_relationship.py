"""
ResearchOS Modeling Domain Model.

Sprint-003A.2

Canonical Scientific Relationship Domain Model.

Represents an explicit scientific relationship
between two ScientificConstruct instances.

Contains no business logic.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.modeling.models.scientific_construct import (
    ScientificConstruct,
)


class RelationshipType(str, Enum):
    """
    Canonical relationship types.
    """

    CAUSAL = "causal"
    CORRELATIONAL = "correlational"
    HIERARCHICAL = "hierarchical"
    FUNCTIONAL = "functional"
    TEMPORAL = "temporal"
    ASSOCIATIVE = "associative"


@dataclass(
    frozen=True,
    slots=True,
)
class ScientificRelationship:
    """
    Canonical Scientific Relationship.
    """

    #
    # Stable identifier.
    #
    relationship_id: str

    #
    # Source construct.
    #
    source_construct: ScientificConstruct

    #
    # Target construct.
    #
    target_construct: ScientificConstruct

    #
    # Explicit relationship type.
    #
    relationship_type: RelationshipType

    #
    # Scientific explanation.
    #
    description: str

    #
    # Optional metadata.
    #
    metadata: dict[str, Any] = field(
        default_factory=dict
    )