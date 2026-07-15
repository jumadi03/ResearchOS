"""Severity vocabulary for architecture laws."""

from enum import StrEnum


class LawSeverity(StrEnum):
    """Release impact of an architecture-law violation."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
