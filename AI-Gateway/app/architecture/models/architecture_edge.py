"""Canonical relationship in a ResearchOS Architecture Graph."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ArchitectureEdge:
    """One directed relationship between two architecture nodes."""

    edge_id: str
    source_id: str
    target_id: str
    relation_type: str
    metadata: dict[str, Any] = field(default_factory=dict)
