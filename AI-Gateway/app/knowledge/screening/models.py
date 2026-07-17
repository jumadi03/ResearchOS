"""Immutable contracts for pre-extraction document screening."""

from dataclasses import asdict, dataclass
from enum import StrEnum
from hashlib import sha256
import json


class ScreeningStatus(StrEnum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    HUMAN_REVIEW_REQUIRED = "human_review_required"


class ScreeningDimension(StrEnum):
    TECHNICAL = "technical"
    SCOPE = "scope"
    EVIDENCE = "evidence"
    QUALITY = "quality"


@dataclass(frozen=True, slots=True)
class ScreeningReason:
    dimension: ScreeningDimension
    code: str
    passed: bool
    explanation: str


@dataclass(frozen=True, slots=True)
class ScreeningDecision:
    decision_id: str
    document_id: str
    canonical_record_id: str
    discovery_contract_id: str
    document_content_hash: str
    inspection_manifest_hash: str
    status: ScreeningStatus
    reasons: tuple[ScreeningReason, ...]
    screener_name: str
    screener_version: str
    decided_at: str
    decision_hash: str = ""
    schema_version: str = "1.0"

    def __post_init__(self) -> None:
        object.__setattr__(self, "reasons", tuple(self.reasons))

    def expected_hash(self) -> str:
        payload = asdict(self)
        payload["decision_hash"] = ""
        return sha256(json.dumps(
            payload, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"),
        ).encode()).hexdigest()

    def finalized(self):
        from dataclasses import replace
        return replace(self, decision_hash=self.expected_hash())

    def verify(self) -> bool:
        return bool(
            self.decision_hash == self.expected_hash()
            and self.document_id and self.canonical_record_id
            and self.discovery_contract_id
            and len(self.document_content_hash) == 64
            and len(self.inspection_manifest_hash) == 64
            and self.reasons
            and {item.dimension for item in self.reasons}
            == set(ScreeningDimension)
            and (
                self.status is ScreeningStatus.ELIGIBLE
                and all(item.passed for item in self.reasons)
                or self.status is not ScreeningStatus.ELIGIBLE
                and any(not item.passed for item in self.reasons)
            )
        )

    def require_eligible(
        self, *, document_id: str, content_hash: str,
        inspection_manifest_hash: str,
    ) -> None:
        if not self.verify():
            raise ValueError("Screening decision integrity verification failed")
        if (
            self.document_id != document_id
            or self.document_content_hash != content_hash
            or self.inspection_manifest_hash != inspection_manifest_hash
        ):
            raise ValueError("Screening decision provenance does not match document")
        if self.status is not ScreeningStatus.ELIGIBLE:
            failed = ", ".join(item.code for item in self.reasons if not item.passed)
            raise ValueError(
                f"Document is not eligible for evidence extraction: {failed}"
            )

