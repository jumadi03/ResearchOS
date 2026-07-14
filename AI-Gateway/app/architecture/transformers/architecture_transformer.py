"""
ResearchOS Architecture Contract.

ARCH-001B.1

Canonical Architecture Transformer Contract.

Defines the canonical transformer
implemented by all Architecture
Transformers.

Contains no implementation.
"""

from typing import Protocol

from app.kernel.transformers.transformer import (
    Transformer,
)

from app.architecture.models.architecture_inventory import (
    ArchitectureInventory,
)


class ArchitectureTransformer(
    Transformer[
        object,
        ArchitectureInventory,
    ],
    Protocol,
):
    """
    Canonical Architecture Transformer.

    Every Architecture Transformer
    transforms raw architectural
    information into a canonical
    ArchitectureInventory.
    """

    ...