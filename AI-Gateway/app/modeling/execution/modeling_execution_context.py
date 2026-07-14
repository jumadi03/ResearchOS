"""
ResearchOS Modeling Execution Layer.

Sprint-003B.1R

Canonical Modeling Execution Context.

Represents execution state for the Modeling
capability.

Contains no business logic.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(
    frozen=True,
    slots=True,
)
class ModelingExecutionContext:
    """
    Canonical Modeling Execution Context.
    """

    #
    # Stable execution identifier.
    #
    execution_id: str

    #
    # Current execution stage.
    #
    stage: str

    #
    # Current execution status.
    #
    status: str

    #
    # Optional execution trace.
    #
    trace: tuple[str, ...] = ()

    #
    # Optional execution metadata.
    #
    metadata: dict[str, Any] = field(
        default_factory=dict
    )