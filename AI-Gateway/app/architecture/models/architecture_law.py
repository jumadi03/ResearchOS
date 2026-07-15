"""
ResearchOS Architecture Domain Model.

ARCH-001A.6

Canonical Architecture Law Domain Model.

Represents a canonical architecture law
used by the Architecture Engine.

Contains no business logic.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from .law_scope import LawScope
from .law_severity import LawSeverity


@dataclass(
    frozen=True,
    slots=True,
)
class ArchitectureLaw:
    """
    Canonical Architecture Law.

    Represents one immutable architecture
    law used during validation.
    """

    #
    # Stable law identifier.
    #
    law_id: str

    #
    # Canonical law title.
    #
    title: str

    #
    # Human-readable description.
    #
    description: str

    #
    # Architecture law version.
    #
    version: str

    #
    # Optional metadata.
    #
    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    # Executable-law attributes. They follow the legacy fields so existing
    # positional construction remains compatible.
    category: str | None = None
    severity: LawSeverity = LawSeverity.ERROR
    scope: LawScope = field(default_factory=LawScope)
    condition: dict[str, Any] = field(default_factory=dict)
    remediation: str | None = None
    effective_from: str | None = None
    effective_until: str | None = None
    enabled: bool = True

    def __post_init__(self) -> None:
        """Reject invalid effective-date ranges at the domain boundary."""
        start = date.fromisoformat(self.effective_from) if self.effective_from else None
        end = date.fromisoformat(self.effective_until) if self.effective_until else None
        if start and end and start > end:
            raise ValueError("effective_from must not be after effective_until")

    @property
    def resolved_category(self) -> str | None:
        """Return the explicit category or its legacy metadata equivalent."""
        return self.category or self.metadata.get("category")

    @classmethod
    def from_dict(cls, item: dict[str, Any]) -> "ArchitectureLaw":
        """Reconstruct a law from a persisted canonical representation."""
        return cls(
            law_id=item["law_id"],
            title=item["title"],
            description=item["description"],
            version=item["version"],
            metadata=item.get("metadata", {}),
            category=item.get("category"),
            severity=LawSeverity(item.get("severity", LawSeverity.ERROR)),
            scope=LawScope(
                node_types=tuple(item.get("scope", {}).get("node_types", ())),
                path_patterns=tuple(item.get("scope", {}).get("path_patterns", ())),
            ),
            condition=item.get("condition", {}),
            remediation=item.get("remediation"),
            effective_from=item.get("effective_from"),
            effective_until=item.get("effective_until"),
            enabled=item.get("enabled", True),
        )
