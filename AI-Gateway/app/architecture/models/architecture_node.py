"""Canonical node in a ResearchOS Architecture Graph."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ArchitectureNode:
    """One uniquely identified architectural entity."""

    node_id: str
    node_type: str
    canonical_name: str
    source_path: str | None = None
    source_line: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
