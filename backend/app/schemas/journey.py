"""Pydantic v2 schemas for Citizen Journey, Evaluation State, and Evidence Workflow.

Strict contract-first schemas enforcing extra="forbid" on requests,
well-defined response models, and complete state machine audit structures.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    ClaimStatus,
    EligibilityResult,
    EvidenceStatus,
    JourneyState,
    VerificationStatus,
)


# ==============================================================================
# Journey Request & Response Schemas
# ==============================================================================

class JourneyCreateRequest(BaseModel):
    """Payload to initiate a new citizen evaluation journey."""
    citizen_ref: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Synthetic or external citizen identifier e.g. SYN-CIT-12345",
    )
    scheme_code: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Scheme code e.g. PM_KISAN or SSY",
    )
    initial_facts: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional initial facts payload to populate claims upon creation",
    )

    model_config = ConfigDict(extra="forbid")


class JourneyTransitionRequest(BaseModel):
    """Payload to advance or move the journey state."""
    target_state: JourneyState = Field(
        ...,
        description="Target lifecycle state to transition into",
    )
    actor: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="System agent, officer ID, or citizen actor triggering transition",
    )
    reason: Optional[str] = Field(
        None,
        max_length=512,
        description="Optional operational justification or audit context",
    )

    model_config = ConfigDict(extra="forbid")


class JourneyTransitionRecordResponse(BaseModel):
    """Immutable audit record of a journey state transition."""
    id: uuid.UUID
    journey_id: uuid.UUID
    from_state: JourneyState
    to_state: JourneyState
    actor: str
    reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class JourneyVerificationRecordResponse(BaseModel):
    """Verification log record for an evidence item."""
    id: uuid.UUID
    evidence_id: Optional[uuid.UUID] = None
    claim_id: Optional[uuid.UUID] = None
    verification_method: str
    status: VerificationStatus
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    details_json: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class JourneyEvidenceResponse(BaseModel):
    """Evidence submission record attached to a claim."""
    id: uuid.UUID
    claim_id: uuid.UUID
    evidence_type: str
    storage_reference: str
    metadata_json: Optional[Dict[str, Any]] = None
    status: EvidenceStatus
    rejection_reason: Optional[str] = None
    submitted_at: datetime
    verified_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    verification_records: List[JourneyVerificationRecordResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class JourneyClaimResponse(BaseModel):
    """Claim record attached to an evaluation journey."""
    id: uuid.UUID
    journey_id: Optional[uuid.UUID] = None
    citizen_id: uuid.UUID
    claim_type: str
    value_json: Dict[str, Any]
    source: str
    status: ClaimStatus
    claimed_at: datetime
    updated_at: datetime
    evidence_items: List[JourneyEvidenceResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class JourneyResponse(BaseModel):
    """Summary response for an evaluation journey."""
    id: uuid.UUID
    citizen_id: uuid.UUID
    citizen_ref: str = Field(..., description="Synthetic citizen reference identifier")
    scheme_id: uuid.UUID
    scheme_code: str = Field(..., description="Target scheme code e.g. PM_KISAN")
    state: JourneyState = Field(..., description="Current journey lifecycle state")
    latest_evaluation_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class JourneyDetailResponse(JourneyResponse):
    """Detailed response for an evaluation journey including claims and history."""
    claims: List[JourneyClaimResponse] = Field(default_factory=list)
    transitions: List[JourneyTransitionRecordResponse] = Field(default_factory=list)


# ==============================================================================
# Claim & Evidence Request Schemas
# ==============================================================================

class JourneyClaimCreateRequest(BaseModel):
    """Payload to register a factual claim under a journey."""
    claim_type: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Factual claim key / path e.g. 'family.owns_cultivable_land'",
    )
    value_json: Dict[str, Any] = Field(
        ...,
        description="Asserted value payload e.g. {'value': true}",
    )
    source: str = Field(
        default="SELF_DECLARATION",
        max_length=64,
        description="Source of claim e.g. SELF_DECLARATION, AGRI_STACK",
    )

    model_config = ConfigDict(extra="forbid")


class JourneyEvidenceCreateRequest(BaseModel):
    """Payload to submit evidence supporting a claim."""
    evidence_type: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Type of evidence e.g. LAND_RECORD_7_12, BIRTH_CERTIFICATE",
    )
    storage_reference: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="Document pointer or storage URI e.g. doc-ref://vault/land-01.pdf",
    )
    metadata_json: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional metadata such as issuer, issue_date, file_hash",
    )

    model_config = ConfigDict(extra="forbid")


class EvidenceVerificationRequest(BaseModel):
    """Payload to transition evidence status (VERIFIED or REJECTED) with audit trail."""
    status: EvidenceStatus = Field(
        ...,
        description="New evidence status: must be VERIFIED or REJECTED",
    )
    verification_method: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Verification technique e.g. MANUAL_OFFICER_REVIEW, REVENUE_PORTAL_API",
    )
    verified_by: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Officer ID or verification service identifier",
    )
    details_json: Optional[Dict[str, Any]] = Field(
        None,
        description="Verification details or verification signature payload",
    )
    rejection_reason: Optional[str] = Field(
        None,
        max_length=512,
        description="Reason for rejection (required when status is REJECTED)",
    )

    model_config = ConfigDict(extra="forbid")


# ==============================================================================
# Journey Evaluation Trigger Schemas
# ==============================================================================

class JourneyEvaluateRequest(BaseModel):
    """Payload to trigger deterministic evaluation from a journey."""
    evaluation_date: Optional[date] = Field(
        None,
        description="Evaluation date; defaults to current date if omitted",
    )
    policy_version_code: Optional[str] = Field(
        None,
        description="Explicit policy version code; if omitted, resolved from evaluation_date",
    )
    facts_override: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional facts override to supplement or test journey claims",
    )

    model_config = ConfigDict(extra="forbid")


class JourneyEvaluationResponse(BaseModel):
    """Complete evaluation outcome response in the context of a citizen journey."""
    journey_id: uuid.UUID
    journey_state: JourneyState
    evaluation_id: uuid.UUID
    result_state: EligibilityResult
    is_eligible: Optional[bool] = None
    scheme_code: str
    policy_version_code: str
    evaluation_date: date
    missing_facts: List[str] = Field(default_factory=list)
    disqualifying_factors: List[Dict[str, Any]] = Field(default_factory=list)
    pending_evidence_count: int
    unverified_evidence_count: int
    action_items: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")
