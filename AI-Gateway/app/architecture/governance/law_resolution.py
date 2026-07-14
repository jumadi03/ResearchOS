"""
ResearchOS Law Resolution.

Determines the applicable
ArchitectureLaw objects for a target.
"""

from dataclasses import dataclass

from .law_registry import LawRegistry

from ..models import (
    ArchitectureLaw,
)


@dataclass(
    frozen=True,
    slots=True,
)
class LawResolution:
    """
    Immutable Law Resolution.

    Resolves applicable ArchitectureLaw
    objects from the Law Registry.
    """

    registry: LawRegistry

    def resolve_all(self) -> tuple[ArchitectureLaw, ...]:
        """
        Return every registered law.

        Foundation implementation.
        """
        return self.registry.get_all()

    def resolve(
        self,
        *,
        category: str,
    ) -> tuple[ArchitectureLaw, ...]:
        """
        Return every applicable law
        for a category.

        Foundation implementation.
        """

        return self.registry.get_by_category(
            category,
        )