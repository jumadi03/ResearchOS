"""
ResearchOS Law Resolution.

Determines the applicable
ArchitectureLaw objects for a target.
"""

from dataclasses import dataclass
from fnmatch import fnmatch

from .law_registry import LawRegistry

from ..models import (
    ArchitectureLaw,
    LawResolutionTrace,
    ResolutionContext,
    ResolvedLawSet,
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

    def resolve_context(self, context: ResolutionContext) -> ResolvedLawSet:
        """Resolve laws for a target and retain every inclusion decision."""
        applicable: list[ArchitectureLaw] = []
        excluded: list[ArchitectureLaw] = []
        trace: list[LawResolutionTrace] = []

        for law in sorted(self.registry.get_all(), key=lambda item: item.law_id):
            reason = self._exclusion_reason(law, context)
            is_applicable = reason is None
            (applicable if is_applicable else excluded).append(law)
            trace.append(
                LawResolutionTrace(
                    law_id=law.law_id,
                    applicable=is_applicable,
                    reason=reason or "APPLICABLE",
                )
            )

        return ResolvedLawSet(
            bundle_id=self.registry.bundle_id,
            bundle_version=self.registry.bundle_version,
            bundle_hash=self.registry.bundle_hash,
            context=context,
            applicable_laws=tuple(applicable),
            excluded_laws=tuple(excluded),
            trace=tuple(trace),
        )

    @staticmethod
    def _exclusion_reason(
        law: ArchitectureLaw,
        context: ResolutionContext,
    ) -> str | None:
        if not law.enabled:
            return "DISABLED"
        if context.category and law.resolved_category != context.category:
            return "CATEGORY_MISMATCH"
        if law.scope.node_types and context.node_type not in law.scope.node_types:
            return "NODE_TYPE_MISMATCH"
        if law.scope.path_patterns:
            if not context.source_path or not any(
                fnmatch(context.source_path, pattern)
                for pattern in law.scope.path_patterns
            ):
                return "PATH_MISMATCH"
        if context.as_of and law.effective_from and context.as_of < law.effective_from:
            return "NOT_YET_EFFECTIVE"
        if context.as_of and law.effective_until and context.as_of > law.effective_until:
            return "EXPIRED"
        return None
