"""
ResearchOS Runtime Provider Enumerator.

Sprint:
    ASR-001A

Enumerates registered providers and converts
them into ProviderCandidate domain models.
"""

from typing import Tuple

from app.infrastructure.ai.provider_registry import ProviderRegistry
from app.runtime.models import ProviderCandidate


class ProviderEnumerator:
    """
    Enumerates providers from the registry.
    """

    def enumerate(
        self,
        registry: ProviderRegistry,
    ) -> Tuple[ProviderCandidate, ...]:

        candidates = []

        for name, provider in registry.items():

            candidates.append(
                ProviderCandidate(
                    name=name,
                    provider=provider,
                    profile=provider.profile(),
                )
            )

        return tuple(candidates)