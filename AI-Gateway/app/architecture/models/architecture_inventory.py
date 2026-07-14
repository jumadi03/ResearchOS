"""
ResearchOS Architecture Domain Model.

ARCH-001A.2

Canonical Architecture Inventory Domain Model.

Represents a canonical snapshot of the
architectural artifacts discovered within
a ResearchOS project.

Contains no business logic.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(
    frozen=True,
    slots=True,
)
class ArchitectureInventory:
    """
    Canonical Architecture Inventory.

    Represents a snapshot of architectural
    artifacts discovered within a project.
    """

    #
    # Stable inventory identifier.
    #
    inventory_id: str

    #
    # Canonical project name.
    #
    project_name: str

    #
    # Registered subsystem names.
    #
    subsystems: tuple[
        str,
        ...
    ] = ()

    #
    # Registered engine names.
    #
    engines: tuple[
        str,
        ...
    ] = ()

    #
    # Registered capability names.
    #
    capabilities: tuple[
        str,
        ...
    ] = ()

    #
    # Optional metadata.
    #
    metadata: dict[str, Any] = field(
        default_factory=dict
    )