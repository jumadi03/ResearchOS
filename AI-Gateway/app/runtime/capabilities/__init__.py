"""
ResearchOS Runtime Capability Package.

This package defines provider capability metadata used by
RoutingPolicy and future Provider Discovery mechanisms.

Sprint:
    Sprint-001N

Status:
    Stable Foundation
"""

from .capability import ProviderCapability
from .registry import CapabilityRegistry

__all__ = [
    "ProviderCapability",
    "CapabilityRegistry",
]