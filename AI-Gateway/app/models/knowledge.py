"""HTTP request models for Scientific Knowledge discovery."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ScientificQuestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    phenomenon_id: str | None = None


class SearchPlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    providers: list[str] = Field(min_length=1)
    limit_per_provider: int = Field(default=25, ge=1, le=1000)
    year_from: int | None = Field(default=None, ge=1000, le=9999)
    year_to: int | None = Field(default=None, ge=1000, le=9999)


class LiteratureDiscoveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: ScientificQuestionRequest
    search_plan: SearchPlanRequest


class DocumentAcquisitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    record_id: str = Field(min_length=1)
    url: str | None = None
    access_status: str
    license: str | None = None
    source_provider: str = Field(min_length=1)
    source_response_hash: str = Field(min_length=1)


class TheoryBuildRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    graph_ids: list[str] = Field(min_length=1)


class TheoryReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    theory_id: str = Field(min_length=1)
    decision: str
    rationale: str = Field(min_length=1)
    occurred_at: str = Field(min_length=1)


class TheoryAlignmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    theory_ids: list[str] = Field(min_length=2)
    statement: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    occurred_at: str = Field(min_length=1)


class TheoryAlignmentDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    theory_ids: list[str] = Field(min_length=2, max_length=2)
    decision: Literal["keep_separate"]
    rationale: str = Field(min_length=1)
    occurred_at: str = Field(min_length=1)


class AlignmentCalibrationProposalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    threshold: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(min_length=12)
    proposed_at: str = Field(min_length=1)


class AlignmentCalibrationApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approved_at: str = Field(min_length=1)


class AlignmentCalibrationRollbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rationale: str = Field(min_length=12)
    occurred_at: str = Field(min_length=1)


class EvidenceReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: str
    rationale: str = Field(min_length=1)
    occurred_at: str = Field(min_length=1)


class ArtifactTransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    to_status: str
    rationale: str = Field(min_length=1)
    occurred_at: str = Field(min_length=1)


class SemanticIndexRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    object_type: str
    object_id: str = Field(min_length=1)
    model: str = Field(min_length=1)
    embedding: list[float] = Field(min_length=1536, max_length=1536)
    metadata: dict = Field(default_factory=dict)


class SemanticSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str = Field(min_length=1)
    query_embedding: list[float] = Field(min_length=1536, max_length=1536)
    limit: int = Field(default=10, ge=1, le=100)
    object_types: list[str] = Field(default_factory=lambda: ["evidence", "artifact"], min_length=1)


class TheoryValidationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assessed_at: str = Field(min_length=1)
    search_completed_at: str = Field(min_length=1)
    max_age_days: int = Field(default=180, ge=1)
    triggered_by_decision_id: str | None = Field(default=None, min_length=1)
    risk_of_bias_by_theory: dict[
        str, Literal["low", "some_concerns", "high", "unknown"]
    ] = Field(
        description=(
            "Reviewer assessment for each theory: low, some_concerns, high, or unknown"
        )
    )


class PublicationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    validation_report_id: str = Field(min_length=1)
    kind: Literal[
        "literature_review", "scoping_review", "systematic_review_support",
        "research_proposal", "evidence_brief",
    ]
    generated_at: str = Field(min_length=1)


class PublicationPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    validation_report_id: str | None = Field(default=None, min_length=1)
    kind: Literal[
        "literature_review", "scoping_review", "systematic_review_support",
        "research_proposal", "evidence_brief",
    ]
