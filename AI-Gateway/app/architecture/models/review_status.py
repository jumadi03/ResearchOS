"""Review workflow vocabularies."""

from enum import StrEnum


class ReviewStatus(StrEnum):
    OPEN = "OPEN"
    APPROVED = "APPROVED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    REJECTED = "REJECTED"
    STALE = "STALE"


class ReviewDecisionType(StrEnum):
    ACCEPT = "ACCEPT"
    WAIVE = "WAIVE"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    REQUEST_CHANGE = "REQUEST_CHANGE"
    REJECT = "REJECT"
