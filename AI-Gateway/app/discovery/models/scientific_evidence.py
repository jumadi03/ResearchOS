"""
ResearchOS Discovery Domain Model.

SDC-002

Canonical Evidence Domain Model.

Represents extracted scientific evidence.

This model contains no business logic.
"""

from dataclasses import dataclass, field
from typing import Any

from .scientific_observation_record import (
    ScientificObservationRecord,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ScientificEvidence:
    """
    Canonical Evidence Domain Model.

    Represents scientific evidence extracted
    from one ScientificObservationRecord.

    Validation is represented as state,
    not as another domain model.
    """

    #
    # Stable identifier.
    #
    evidence_id: str

    #
    # Evidence content.
    #
    content: str

    #
    # Source observation.
    #
    observation: ScientificObservationRecord

    #
    # Validation state.
    #
    validated: bool = False

    #
    # Optional metadata.
    #
    metadata: dict[str, Any] = field(
        default_factory=dict
    )