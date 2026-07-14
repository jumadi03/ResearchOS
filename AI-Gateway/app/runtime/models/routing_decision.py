"""
ResearchOS Runtime Routing Decision.

Sprint:
    Sprint-001N

Represents the immutable output produced by
RoutingPolicy.
"""

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    """
    Immutable routing result.

    The decision contains both the selected provider
    and metadata explaining why the decision was made.

    Future versions may enrich this model without
    changing the public RoutingPolicy API.
    """

    #
    # Selected provider
    #

    provider: str

    #
    # Decision metadata
    #

    reason: str = "Configured active provider"

    metadata: Mapping[str, str] = field(
        default_factory=dict
    )