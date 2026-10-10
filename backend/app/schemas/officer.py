"""Pydantic v2 schemas for Officer / Human Verification Portal.

Defines schemas for officer authentication, verification queue, case details,
plain-language claim inspection, evidence verification, human review decisions,
policy provenance viewing, and append-only audit trail.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import HumanReviewStatus


# ==============================================================================
# Authentication Schemas
# ==============================================================================

class OfficerLoginRequest(BaseModel):
    """Credentials for development officer login."""
    email: str = Field(..., description="Officer or Supervisor demo email")
    password: str = Field(..., description="Officer password")

    model_config = ConfigDict(extra="forbid")


class OfficerLoginResponse(BaseModel):
    """Bearer token and officer profile details."""
    access_token: str
    token_type: str = "bearer"
    officer_name: str
    officer_role: str
    designation: str
    department: str
    demo_environment: bool = True
    environment_notice: str = (
        "DEVELOPMENT DEMO ENVIRONMENT ONLY — Production systems must use "
        "official government SSO (e.g. Parichay / e-Pramaan). Real Aadhaar data is not accepted."
    )


# ==============================================================================
# Verification Queue Schemas
# ==============================================================================

class OfficerAssignmentResponse(BaseModel):
    """Detailed representation of an operational officer assignment."""
    id: uuid.UUID
    journey_id: uuid.UUID
    officer_identity: str
    officer_name: Optional[str] = None
    assigned_by: str
    assigned_at: datetime
    due_at: datetime
    sla_duration_hours: int
    status: str
    is_active: bool
    reassigned_to_id: Optional[uuid.UUID] = None
    reassignment_reason: Optional[str] = None
    sla_status: str = "NOT_DUE"  # NOT_DUE, DUE_SOON, OVERDUE, COMPLETED
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OfficerQueueItemResponse(BaseModel):
    """Summary item in the officer verification queue."""
    journey_id: uuid.UUID
    citizen_ref: str
    scheme_code: str
    scheme_name: str
    journey_state: str
    submitted_at: datetime
    review_status: str
    review_decision: Optional[str] = None
    evidence_count: int = 0
    verified_evidence_count: int = 0
    automated_eligibility: Optional[str] = None
    assigned_officer: Optional[str] = None
    assigned_officer_name: Optional[str] = None
    assignment_status: str = "UNASSIGNED"
    assigned_at: Optional[datetime] = None
    due_at: Optional[datetime] = None
    sla_status: str = "NOT_DUE"

    model_config = ConfigDict(from_attributes=True)


class OfficerQueueMetricsResponse(BaseModel):
    """Aggregate queue counters for the officer dashboard."""
    total_cases: int
    pending_cases: int
    in_review_cases: int
    escalated_cases: int
    completed_cases: int


class OfficerDashboardStatsResponse(BaseModel):
    """Operational dashboard statistics backed by real database records."""
    my_active_requests: int
    unassigned_requests: int
    due_soon: int
    overdue: int
    completed: int
    total_active_workload: int
    max_capacity_per_officer: int
    default_sla_duration_hours: int


class OfficerQueueListResponse(BaseModel):
    """Complete response payload for officer queue list."""
    metrics: OfficerQueueMetricsResponse
    items: List[OfficerQueueItemResponse]



# ==============================================================================
# Claims & Evidence Schemas
# ==============================================================================

class OfficerClaimResponse(BaseModel):
    """Citizen-asserted claim rendered in plain, accessible language."""
    id: uuid.UUID
    claim_type: str
    claim_label: str
    value_json: Dict[str, Any]
    value_display: str
    source: str
    status: str
    claimed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OfficerEvidenceResponse(BaseModel):
    """Documentary evidence submitted by citizen."""
    id: uuid.UUID
    claim_id: uuid.UUID
    claim_type: str
    evidence_type: str
    evidence_type_label: str
    storage_reference: str
    metadata_json: Optional[Dict[str, Any]] = None
    status: str
    submitted_at: datetime
    verified_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    verification_records: List[Dict[str, Any]] = []

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# Assessment & Policy Provenance Schemas
# ==============================================================================

class OfficerAssessmentRuleResponse(BaseModel):
    """Evaluated statutory rule pass/fail breakdown."""
    rule_id: str
    rule_name: str
    description: str
    result: str  # PASS, FAIL, UNKNOWN
    details: Optional[str] = None
    operator: Optional[str] = None
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None


class OfficerAssessmentResponse(BaseModel):
    """Automated deterministic eligibility assessment output."""
    evaluation_id: Optional[uuid.UUID] = None
    determination: Optional[str] = None
    evaluated_at: Optional[datetime] = None
    ruleset_version: Optional[str] = None
    ruleset_hash: Optional[str] = None
    rules_evaluated: List[OfficerAssessmentRuleResponse] = []
    missing_facts: List[str] = []
    disqualifiers: List[str] = []
    reasons_en: List[str] = []
    reasons_hi: List[str] = []


class OfficerPolicyProvenanceResponse(BaseModel):
    """Read-only statutory policy version and cryptographic provenance."""
    scheme_code: str
    scheme_name: str
    policy_version: str
    ruleset_version: str
    effective_from: str
    effective_to: Optional[str] = None
    content_sha256: str
    official_citation: str
    gazette_reference: str
    issuing_authority: str
    rule_definitions_count: int
    is_statutory_source_verified: bool = True
    document_title: Optional[str] = None
    document_version: Optional[str] = None
    document_hash: Optional[str] = None
    official_source_url: Optional[str] = None
    provenance_completeness: Optional[str] = "COMPLETE"


# ==============================================================================
# Audit Event Schemas
# ==============================================================================

class OfficerAuditEventResponse(BaseModel):
    """Immutable audit record from human_review_audit_events."""
    id: uuid.UUID
    journey_id: uuid.UUID
    review_id: uuid.UUID
    actor_identity: str
    actor_role: str
    action: str
    previous_status: Optional[str] = None
    new_status: str
    reason: Optional[str] = None
    details_json: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# Case Details Schemas
# ==============================================================================

class OfficerCaseDetailResponse(BaseModel):
    """Full case dossier for officer inspection and verification."""
    journey_id: uuid.UUID
    citizen_ref: str
    scheme_code: str
    scheme_name: str
    journey_state: str
    submitted_at: datetime
    updated_at: datetime
    review_status: str
    review_decision: Optional[str] = None
    review_notes: Optional[str] = None
    reviewer_identity: Optional[str] = None
    reviewer_role: Optional[str] = None
    claims: List[OfficerClaimResponse]
    evidence_items: List[OfficerEvidenceResponse]
    automated_assessment: Optional[OfficerAssessmentResponse] = None
    policy_provenance: Optional[OfficerPolicyProvenanceResponse] = None
    audit_history: List[OfficerAuditEventResponse] = []
    active_assignment: Optional[OfficerAssignmentResponse] = None
    assignment_history: List[OfficerAssignmentResponse] = []
    clarifications: List[Dict[str, Any]] = []
    verification_status: Optional[str] = None


# ==============================================================================
# Action Requests
# ==============================================================================

class OfficerAssignmentRequest(BaseModel):
    """Payload to manually assign a case to an officer."""
    officer_identity: str = Field(..., description="Target officer email / identifier")
    sla_hours: Optional[int] = Field(None, ge=1, le=720, description="Optional custom SLA duration in hours")
    reason: Optional[str] = Field(None, description="Optional administrative justification")

    model_config = ConfigDict(extra="forbid")


class OfficerReassignmentRequest(BaseModel):
    """Payload to reassign an active case to a new officer with auditable justification."""
    new_officer_identity: str = Field(..., description="Target new officer email / identifier")
    reason: str = Field(..., min_length=3, description="Mandatory justification for reassignment")
    sla_hours: Optional[int] = Field(None, ge=1, le=720, description="Optional custom SLA duration in hours")

    model_config = ConfigDict(extra="forbid")


class OfficerEvidenceVerifyRequest(BaseModel):
    """Payload to record an officer determination on an individual evidence item."""
    action: str = Field(
        ...,
        description="Action: VERIFY, REJECT, or REQUEST_CLARIFICATION",
    )
    reason: Optional[str] = Field(
        None,
        description="Mandatory justification when action is REJECT or REQUEST_CLARIFICATION",
    )
    notes: Optional[str] = Field(None, description="Optional administrative notes")

    model_config = ConfigDict(extra="forbid")


class OfficerCaseReviewRequest(BaseModel):
    """Payload to record an overall case determination."""
    decision: str = Field(
        ...,
        description="Decision: VERIFIED, CLARIFICATION_REQUIRED, REJECTED, ESCALATED, or COMPLETED",
    )
    reason: Optional[str] = Field(
        None,
        description="Mandatory reason for CLARIFICATION_REQUIRED, REJECTED, ESCALATED, or supervisor resolution",
    )
    notes: Optional[str] = Field(None, description="Optional case notes")

    model_config = ConfigDict(extra="forbid")


class OfficerCaseEvaluationExecuteRequest(BaseModel):
    """Payload to execute deterministic statutory evaluation on an assigned case."""
    notes: Optional[str] = Field(None, description="Optional officer notes or evaluation justification")

    model_config = ConfigDict(extra="forbid")
