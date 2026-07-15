"""Versioned scientific assessment and validation contracts."""

from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from hashlib import sha256
import json


class RiskOfBias(StrEnum):
    LOW = "low"
    SOME_CONCERNS = "some_concerns"
    HIGH = "high"
    UNKNOWN = "unknown"


class ValidationStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    INCOMPLETE = "incomplete"
    STALE = "stale"


@dataclass(frozen=True, slots=True)
class AssessmentMethod:
    method_id: str
    version: str
    minimum_replications: int
    bias_factors: tuple[tuple[RiskOfBias, float], ...]
    contradiction_penalty: float


@dataclass(frozen=True, slots=True)
class TheoryAssessment:
    theory_id: str
    status: ValidationStatus
    confidence_score: float
    support_assertions: int
    independent_graphs: int
    contradiction_assertions: int
    risk_of_bias: RiskOfBias
    reasons: tuple[str, ...]
    evidence_edge_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ValidationReport:
    report_id: str
    theory_bundle_id: str
    assessed_at: str
    search_completed_at: str
    max_age_days: int
    reviewer: str
    method: AssessmentMethod
    assessments: tuple[TheoryAssessment, ...]
    status: ValidationStatus
    content_hash: str = ""
    schema_version: str = "1.0"

    def finalized(self):
        payload = asdict(replace(self, content_hash=""))
        digest = sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return replace(self, content_hash=digest)

    def verify(self) -> bool:
        return bool(self.content_hash) and self.finalized().content_hash == self.content_hash
