"""
ResearchOS Runtime Provider Evaluation.

Sprint:
    Sprint-001O

Represents the evaluation result of a provider
candidate during routing.
"""

from dataclasses import dataclass, field
from typing import Mapping

from app.runtime.models.provider_candidate import ProviderCandidate


@dataclass(frozen=True, slots=True)
class ProviderEvaluation:
    """
    Immutable evaluation of a provider candidate.
    """

    candidate: ProviderCandidate

    accepted: bool

    score: float = 0.0

    reason: str = ""

    metadata: Mapping[str, str] = field(
        default_factory=dict
    )