"""HTTP contracts for the architecture governance workflow."""

from pydantic import BaseModel, ConfigDict, Field

from app.architecture.models import LawSeverity, ReviewDecisionType


class ArchitectureRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ScanRequest(ArchitectureRequest):
    project_name: str = Field(min_length=1, max_length=120)
    source_revision: str = Field(min_length=1, max_length=200)


class LawScopeRequest(ArchitectureRequest):
    node_types: list[str] = Field(default_factory=list)
    path_patterns: list[str] = Field(default_factory=list)


class LawRequest(ArchitectureRequest):
    law_id: str
    title: str
    description: str
    version: str
    category: str | None = None
    severity: LawSeverity = LawSeverity.ERROR
    scope: LawScopeRequest = Field(default_factory=LawScopeRequest)
    condition: dict[str, object] = Field(default_factory=dict)
    remediation: str | None = None
    effective_from: str | None = None
    effective_until: str | None = None
    enabled: bool = True


class LawBundleRequest(ArchitectureRequest):
    version: str
    laws: list[LawRequest] = Field(default_factory=list)


class ComplianceRequest(ArchitectureRequest):
    as_of: str


class OpenReviewRequest(ArchitectureRequest):
    opened_at: str


class ReviewDecisionRequest(ArchitectureRequest):
    finding_id: str
    decision_type: ReviewDecisionType
    rationale: str
    decided_at: str
    expires_at: str | None = None


class FinalizeReviewRequest(ArchitectureRequest):
    occurred_at: str
    as_of: str


class ARCRequest(ArchitectureRequest):
    generated_at: str
    publish: bool = True
