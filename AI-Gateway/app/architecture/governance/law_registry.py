"""
ResearchOS Law Registry.

Immutable repository of ratified
ArchitectureLaw objects.
"""

from dataclasses import dataclass

from app.architecture.models.architecture_law import (
    ArchitectureLaw,
)


@dataclass(frozen=True, slots=True)
class LawRegistry:
    """
    Immutable Law Registry.

    Stores the canonical collection of
    ArchitectureLaw objects.

    Read-only during an execution cycle.
    """

    laws: tuple[ArchitectureLaw, ...] = ()

    def get_all(self) -> tuple[ArchitectureLaw, ...]:
        """
        Return all registered laws.
        """
        return self.laws

    def get_by_id(self, law_id: str) -> ArchitectureLaw | None:
        """
        Return a law by its identifier.
        """
        for law in self.laws:
            if law.law_id == law_id:
                return law

        return None

    def get_by_category(
        self,
        category: str,
    ) -> tuple[ArchitectureLaw, ...]:
        """
        Return all laws belonging to a category.
        """
        return tuple(
            law
            for law in self.laws
            if law.metadata.get("category") == category
        )