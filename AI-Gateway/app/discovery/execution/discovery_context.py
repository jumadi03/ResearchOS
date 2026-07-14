"""
ResearchOS Discovery Execution Model.

DiscoveryContext carries the execution state
for the Discovery pipeline.

It is not part of the scientific domain model.
"""

from dataclasses import dataclass, field
from typing import Any

from app.discovery.models.scientific_observation_record import (
    ScientificObservationRecord,
)


@dataclass(slots=True)
class DiscoveryContext:
    """
    Execution context for the Discovery Capability.

    Initially contains only the canonical
    ScientificObservationRecord.

    Additional execution state will be added
    incrementally following the Evolutionary
    Domain Modeling (EDM) principle.
    """

    observation: ScientificObservationRecord

    metadata: dict[str, Any] = field(
        default_factory=dict
    )