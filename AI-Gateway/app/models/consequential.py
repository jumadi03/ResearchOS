"""Strict HTTP contracts for the SGF-020C control plane."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConsequentialProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile_key: str = Field(min_length=1)
    version: int = Field(ge=1)
    name: str = Field(min_length=1)
    risk_class: Literal[
        "medical", "legal", "safety_critical", "human_subject",
        "regulatory", "other_consequential",
    ]
    jurisdiction: str = Field(min_length=1)
    required_reviewer_quorum: int = Field(default=2, ge=2)
    required_qualification_kind: str = Field(min_length=1)
    require_unanimous_review: bool = True
    require_ethics_reference: bool = True
    require_distinct_release_authority: bool = True
    decision_validity_days: int = Field(gt=0)
    policy_document_id: str = Field(min_length=1)
    policy_document_hash: str
    effective_from: datetime

    @field_validator("policy_document_hash")
    @classmethod
    def valid_hash(cls, value: str) -> str:
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            raise ValueError("policy_document_hash must be lowercase SHA-256")
        return value


class HumanAuthorityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workspace_user_id: UUID | None = None
    stable_subject_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    identity_verified_at: datetime


class ProfileActivationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile_id: UUID
    rationale: str = Field(min_length=12)
    activated_at: datetime


class AuthorityQualificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    qualification_kind: str = Field(min_length=1)
    issuing_body: str = Field(min_length=1)
    jurisdiction: str = Field(min_length=1)
    scope: dict
    credential_reference: str = Field(min_length=1)
    credential_hash: str
    valid_from: datetime
    valid_until: datetime
    verified_at: datetime

    @field_validator("credential_hash")
    @classmethod
    def credential_sha256(cls, value: str) -> str:
        return ConsequentialProfileRequest.valid_hash(value)


class EthicsApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: str = Field(min_length=1)
    protocol_identifier: str = Field(min_length=1)
    issuing_body: str = Field(min_length=1)
    jurisdiction: str = Field(min_length=1)
    decision: Literal["approved", "waived"]
    scope: dict
    document_reference: str = Field(min_length=1)
    document_hash: str
    valid_from: datetime
    valid_until: datetime
    recorded_at: datetime
    supersedes_ethics_approval_id: UUID | None = None

    @field_validator("document_hash")
    @classmethod
    def document_sha256(cls, value: str) -> str:
        return ConsequentialProfileRequest.valid_hash(value)


class ScientificDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: str = Field(min_length=1)
    profile_id: UUID
    decision_type: Literal[
        "evidence", "theory", "validation", "artifact_transition",
        "publication_release", "governance",
    ]
    target_type: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    target_version: str = Field(min_length=1)
    target_content_hash: str
    proposed_decision: str = Field(min_length=1)
    release_authority_id: UUID | None = None
    rationale: str = Field(min_length=12)
    policy_snapshot_hash: str
    opened_at: datetime
    review_due_at: datetime
    valid_until: datetime
    ethics_approval_ids: list[UUID] = Field(default_factory=list)

    @field_validator("target_content_hash", "policy_snapshot_hash")
    @classmethod
    def decision_sha256(cls, value: str) -> str:
        return ConsequentialProfileRequest.valid_hash(value)


class ConflictDeclarationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    declaration: Literal[
        "no_conflict", "managed_conflict", "unresolved_conflict"
    ]
    details: str
    mitigation: str | None = None
    declared_at: datetime


class DecisionVoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vote: Literal["approve", "reject", "abstain"]
    rationale: str = Field(min_length=12)
    reviewed_target_hash: str
    occurred_at: datetime

    @field_validator("reviewed_target_hash")
    @classmethod
    def reviewed_sha256(cls, value: str) -> str:
        return ConsequentialProfileRequest.valid_hash(value)


class QuorumEvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evaluated_at: datetime


class DecisionAppealRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    grounds: str = Field(min_length=12)
    requested_remedy: str = Field(min_length=12)
    supporting_evidence: list[dict] = Field(default_factory=list)
    filed_at: datetime


class AppealEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_type: Literal[
        "accepted_for_review", "rejected", "resolved_upheld",
        "resolved_overturned", "resolved_remanded",
    ]
    rationale: str = Field(min_length=12)
    resulting_decision_id: UUID | None = None
    occurred_at: datetime
