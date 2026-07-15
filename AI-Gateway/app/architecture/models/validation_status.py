"""Status vocabulary for deterministic architecture validation."""

from enum import StrEnum


class ValidationStatus(StrEnum):
    """Explicit outcome of one architecture validation."""

    PASS = "PASS"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    NOT_RUN = "NOT_RUN"
    ERROR = "ERROR"
