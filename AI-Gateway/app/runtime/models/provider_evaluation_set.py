"""
ResearchOS Runtime Provider Evaluation Set.

Sprint:
    Sprint-001O

Represents an immutable collection of provider
evaluations produced by the capability matcher.
"""

from dataclasses import dataclass
from typing import Tuple

from .provider_evaluation import ProviderEvaluation


@dataclass(frozen=True, slots=True)
class ProviderEvaluationSet:
    """
    Immutable collection of provider evaluations.
    """

    evaluations: Tuple[ProviderEvaluation, ...] = ()