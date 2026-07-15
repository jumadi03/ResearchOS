"""
ResearchOS Law Registry.

Immutable repository of ratified
ArchitectureLaw objects.
"""

from dataclasses import dataclass

from app.architecture.models.architecture_law import (
    ArchitectureLaw,
)
from app.architecture.models.architecture_law_bundle import ArchitectureLawBundle


@dataclass(frozen=True, slots=True)
class LawRegistry:
    """
    Immutable Law Registry.

    Stores the canonical collection of
    ArchitectureLaw objects.

    Read-only during an execution cycle.
    """

    laws: tuple[ArchitectureLaw, ...] = ()
    bundle_id: str = "law-bundle:unversioned"
    bundle_version: str = "unversioned"
    bundle_hash: str = ""

    @classmethod
    def from_bundle(cls, bundle: ArchitectureLawBundle) -> "LawRegistry":
        """Create a read-only registry from a finalized law bundle."""
        finalized = bundle if bundle.content_hash else bundle.finalized()
        return cls(
            laws=finalized.laws,
            bundle_id=finalized.bundle_id,
            bundle_version=finalized.version,
            bundle_hash=finalized.content_hash,
        )

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
            if law.resolved_category == category
        )
