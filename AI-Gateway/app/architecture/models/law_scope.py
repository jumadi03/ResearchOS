"""Declarative applicability scope for an architecture law."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LawScope:
    """Targets to which an architecture law may apply."""

    node_types: tuple[str, ...] = ()
    path_patterns: tuple[str, ...] = ()
