"""Auditable result models for architecture-law resolution."""

from dataclasses import dataclass

from .architecture_law import ArchitectureLaw


@dataclass(frozen=True, slots=True)
class ResolutionContext:
    """Target information used to decide architecture-law applicability."""

    category: str | None = None
    node_type: str | None = None
    source_path: str | None = None
    as_of: str | None = None


@dataclass(frozen=True, slots=True)
class LawResolutionTrace:
    """One explainable include/exclude decision."""

    law_id: str
    applicable: bool
    reason: str


@dataclass(frozen=True, slots=True)
class ResolvedLawSet:
    """Applicable laws and the complete decision trace for one target."""

    bundle_id: str
    bundle_version: str
    bundle_hash: str
    context: ResolutionContext
    applicable_laws: tuple[ArchitectureLaw, ...] = ()
    excluded_laws: tuple[ArchitectureLaw, ...] = ()
    trace: tuple[LawResolutionTrace, ...] = ()
