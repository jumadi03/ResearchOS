"""Canonical structured scientific extraction contracts."""

from dataclasses import dataclass
from enum import StrEnum


class ScientificObjectType(StrEnum):
    CLAIM = "claim"
    METHOD = "method"
    VARIABLE = "variable"
    DATASET = "dataset"
    RESULT = "result"
    LIMITATION = "limitation"
    CONCLUSION = "conclusion"


class ExtractionReviewState(StrEnum):
    PROVISIONAL = "provisional"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class EvidenceReviewEvent:
    review_id: str
    evidence_object_id: str
    decision: ExtractionReviewState
    reviewer: str
    rationale: str
    occurred_at: str
    provenance_id: str
    previous_state: str


@dataclass(frozen=True, slots=True)
class DocumentCoordinates:
    page: int
    start_char: int
    end_char: int
    quote_hash: str


@dataclass(frozen=True, slots=True)
class ExtractedScientificObject:
    object_id: str
    object_type: ScientificObjectType
    content: str
    coordinates: DocumentCoordinates
    confidence: float
    review_state: ExtractionReviewState
    extraction_method: str
    parser_version: str


@dataclass(frozen=True, slots=True)
class ExtractionManifest:
    extraction_id: str
    document_id: str
    document_content_hash: str
    created_at: str
    parser_name: str
    parser_version: str
    objects: tuple[ExtractedScientificObject, ...]
    schema_version: str = "1.0"
