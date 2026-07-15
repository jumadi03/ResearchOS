"""Object-centric product read contracts."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProjectSummary:
    project_id: str
    name: str
    description: str
    status: str
    object_count: int


@dataclass(frozen=True, slots=True)
class ObjectSummary:
    object_id: str
    stable_key: str
    object_type: str
    lifecycle_status: str
    current_version: int
    title: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class ObjectPage:
    items: tuple[ObjectSummary, ...]
    next_cursor: str | None
