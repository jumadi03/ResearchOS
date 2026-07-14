"""
ResearchOS Discovery Domain Model.

SDC-002

Canonical Discovery Input Model.

Represents a single scientific observation
before evidence extraction.

This model contains no business logic.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(
    frozen=True,
    slots=True,
)
class ScientificObservationRecord:
    """
    Canonical Discovery Input Model.

    Represents one scientific observation
    extracted from any scientific source.

    This model remains descriptive only.

    Validation, integration, and discovery
    are performed by downstream transformers.
    """

    #
    # Stable observation identifier.
    #
    observation_id: str

    #
    # Human-readable observation.
    #
    content: str

    #
    # Identifier of the originating source.
    #
    source_id: str

    #
    # Optional metadata.
    #
    metadata: dict[str, Any] = field(
        default_factory=dict
    )