"""
ResearchOS Runtime Provider Candidate.

Sprint:
    Sprint-001O

Represents a provider being evaluated by the
routing engine.

The candidate is immutable and carries metadata
required during provider selection.
"""

from dataclasses import dataclass

from app.infrastructure.ai.provider_profile import ProviderProfile
from app.infrastructure.ai.interfaces import AIProvider


@dataclass(frozen=True, slots=True)
class ProviderCandidate:
    """
    Provider candidate evaluated during routing.
    """

    name: str

    provider: AIProvider

    profile: ProviderProfile