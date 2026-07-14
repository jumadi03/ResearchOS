"""
ResearchOS Modeling Domain Model.

Sprint-003A.4

Canonical Scientific Theory Domain Model.

Represents an integrated scientific theory
supported by one or more ScientificModel
instances.

Contains no business logic.
"""

from dataclasses import dataclass, field
from typing import Any

from app.modeling.models.scientific_model import (
    ScientificModel,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ScientificTheory:
    """
    Canonical Scientific Theory.
    """

    #
    # Stable identifier.
    #
    theory_id: str

    #
    # Canonical theory name.
    #
    name: str

    #
    # Scientific explanation.
    #
    explanation: str

    #
    # Supporting scientific models.
    #
    models: tuple[
        ScientificModel,
        ...
    ]

    #
    # Theory scope.
    #
    scope: str

    #
    # Optional metadata.
    #
    metadata: dict[str, Any] = field(
        default_factory=dict
    )