"""
Capability Registry.

Sprint:
    Sprint-001N

Stores immutable capability metadata for all registered
providers.

This registry is intentionally separated from ProviderRegistry.
"""

from typing import Dict

from .capability import ProviderCapability


class CapabilityRegistry:
    """
    Registry of provider capabilities.
    """

    def __init__(self) -> None:
        self._capabilities: Dict[str, ProviderCapability] = {}

    def register(
        self,
        capability: ProviderCapability,
    ) -> None:
        """
        Register capability metadata.
        """
        self._capabilities[
            capability.provider_name
        ] = capability

    def get(
        self,
        provider_name: str,
    ) -> ProviderCapability | None:
        """
        Retrieve capability metadata.
        """
        return self._capabilities.get(provider_name)

    def has(
        self,
        provider_name: str,
    ) -> bool:
        """
        Returns True if capability exists.
        """
        return provider_name in self._capabilities

    def all(self) -> tuple[ProviderCapability, ...]:
        """
        Returns all registered capabilities.
        """
        return tuple(self._capabilities.values())

    def clear(self) -> None:
        """
        Remove every registered capability.
        """
        self._capabilities.clear()