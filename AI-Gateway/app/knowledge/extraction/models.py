"""Canonical structured provisional scientific extraction contracts."""

from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from hashlib import sha256
import json


class ScientificObjectType(StrEnum):
    CLAIM = "claim"
    METHOD = "method"
    VARIABLE = "variable"
    DATASET = "dataset"
    RESULT = "result"
    LIMITATION = "limitation"
    CONCLUSION = "conclusion"
    POPULATION = "population"
    OBSERVATION = "observation"
    MEASUREMENT = "measurement"


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
class EvidenceAdmission:
    evidence_object_id: str
    review_state: ExtractionReviewState | None
    review_event: EvidenceReviewEvent | None


@dataclass(frozen=True, slots=True)
class DocumentCoordinates:
    page: int
    start_char: int
    end_char: int
    quote_hash: str
    section: str | None = None
    paragraph: int | None = None
    table_id: str | None = None
    figure_id: str | None = None
    page_text_hash: str | None = None


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
    verbatim_text: str | None = None
    extraction_rule: str | None = None


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
    inspection_manifest_hash: str = ""
    screening_decision_id: str = ""
    screening_decision_hash: str = ""
    configuration_hash: str = ""
    manifest_hash: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "objects", tuple(self.objects))

    def expected_hash(self) -> str:
        payload = asdict(self)
        payload["manifest_hash"] = ""
        return sha256(json.dumps(
            payload, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"),
        ).encode()).hexdigest()

    def finalized(self) -> "ExtractionManifest":
        return replace(self, manifest_hash=self.expected_hash())

    def verify(self) -> bool:
        if self.schema_version == "1.0":
            return not self.manifest_hash
        return bool(
            self.schema_version == "1.1"
            and self.manifest_hash == self.expected_hash()
            and len(self.document_content_hash) == 64
            and len(self.inspection_manifest_hash) == 64
            and self.screening_decision_id
            and len(self.screening_decision_hash) == 64
            and len(self.configuration_hash) == 64
            and all(
                item.review_state is ExtractionReviewState.PROVISIONAL
                and item.content
                and item.verbatim_text
                and item.content == item.verbatim_text
                and item.coordinates.page > 0
                and item.coordinates.start_char >= 0
                and item.coordinates.end_char > item.coordinates.start_char
                and item.coordinates.quote_hash
                == sha256(item.verbatim_text.encode("utf-8")).hexdigest()
                and item.coordinates.page_text_hash
                and item.extraction_rule
                and 0 <= item.confidence <= 1
                for item in self.objects
            )
        )
