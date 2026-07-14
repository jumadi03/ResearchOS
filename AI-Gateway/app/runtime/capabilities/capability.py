"""
Provider Capability Model.

Sprint:
    Sprint-001N

This module defines the immutable capability metadata
associated with a provider.

The capability model is intentionally independent from
provider implementation so that Runtime remains AI-agnostic.
"""

from dataclasses import dataclass, field
from typing import FrozenSet, Mapping


@dataclass(frozen=True, slots=True)
class ProviderCapability:
    """
    Immutable metadata describing a provider.

    Example
    -------
    ProviderCapability(
        provider_name="ollama",
        capabilities=frozenset({
            "chat",
            "stream",
            "json"
        })
    )
    """

    provider_name: str

    capabilities: FrozenSet[str]

    metadata: Mapping[str, str] = field(default_factory=dict)

    def supports(self, capability: str) -> bool:
        """
        Returns True if the provider supports
        the requested capability.
        """
        return capability in self.capabilities

    def supports_all(self, capabilities: set[str]) -> bool:
        """
        Returns True if all requested capabilities
        are supported.
        """
        return capabilities.issubset(self.capabilities)

    def supports_any(self, capabilities: set[str]) -> bool:
        """
        Returns True if at least one capability
        is supported.
        """
        return any(cap in self.capabilities for cap in capabilities)