"""Canonical gap and hypothesis contracts."""

from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from hashlib import sha256
import json


class GapType(StrEnum):
    EVIDENCE_ABSENCE = "evidence_absence"
    LIMITED_COVERAGE = "limited_coverage"
    UNRESOLVED_CONTRADICTION = "unresolved_contradiction"


class GapSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class ResearchGap:
    gap_id: str
    gap_type: GapType
    severity: GapSeverity
    theory_ids: tuple[str, ...]
    evidence_edge_ids: tuple[str, ...]
    rule_id: str
    explanation: str


@dataclass(frozen=True, slots=True)
class HypothesisProposal:
    hypothesis_id: str
    gap_id: str
    statement: str
    rationale: str
    advisory: bool = True


@dataclass(frozen=True, slots=True)
class GapAnalysis:
    analysis_id: str
    theory_bundle_id: str
    created_at: str
    gaps: tuple[ResearchGap, ...]
    hypotheses: tuple[HypothesisProposal, ...]
    ruleset_version: str = "1.0.0"
    content_hash: str = ""
    schema_version: str = "1.0"

    def finalized(self):
        payload = asdict(replace(self, content_hash=""))
        digest = sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return replace(self, content_hash=digest)

    def verify(self) -> bool:
        return bool(self.content_hash) and self.finalized().content_hash == self.content_hash
