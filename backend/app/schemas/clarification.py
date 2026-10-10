"""Pydantic v2 schemas for Evidence Clarification and Verification Workflow (Phase E)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.officer import OfficerAuditEventResponse


# ==============================================================================
# Citizen-Facing Clarification Schemas (Safe, Sanitized)
# ==============================================================================

class CitizenReplacementEvidenceInput(BaseModel):
    """Corroborating documentary evidence submitted by citizen in response to clarification."""
    document_name: str = Field(..., min_length=1, max_length=255, description="Document display title")
    storage_reference: str = Field(..., min_length=1, max_length=512, description="Local or cloud storage URI")
    evidence_type: Optional[str] = Field(None, max_length=128, description="Type of evidence (e.g. LAND_RECORD, AADHAAR)")
    file_size_bytes: Optional[int] = Field(None, ge=1, description="Size in bytes")
    mime_type: Optional[str] = Field(None, max_length=128, description="MIME content type")
    metadata_json: Optional[Dict[str, Any]] = Field(None, description="Extensible file metadata")

    model_config = ConfigDict(extra="forbid")


class CitizenClarificationRespondRequest(BaseModel):
    """Payload submitted by citizen to address an open clarification request."""
    response_text: str = Field(
        ...,
        min_length=3,
        max_length=4000,
        description="Factual clarification or explanation addressing officer's query",
    )
    replacement_evidence: Optional[CitizenReplacementEvidenceInput] = Field(
        None,
        description="Optional replacement or newly uploaded corroborating document",
    )

    model_config = ConfigDict(extra="forbid")


class CitizenClarificationItemResponse(BaseModel):
    """Sanitized, citizen-safe representation of a clarification request."""
    id: uuid.UUID
    round: int
    evidence_id: Optional[uuid.UUID] = None
    claim_id: Optional[uuid.UUID] = None
    request_reason: str
    status: str  # OPEN, RESPONDED, UNDER_REVIEW, RESOLVED, CLOSED
    requested_at: datetime
    response_text: Optional[str] = None
    responded_at: Optional[datetime] = None
    has_replacement_evidence: bool = False
    replacement_evidence_id: Optional[uuid.UUID] = None
    replacement_evidence_name: Optional[str] = None
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CitizenClarificationListResponse(BaseModel):
    """All clarification requests and overarching verification status for citizen application."""
    application_id: uuid.UUID
    application_ref: str
    scheme_code: str
    scheme_name: str
    verification_status: str  # VERIFICATION_IN_PROGRESS, CLARIFICATION_REQUIRED, VERIFICATION_COMPLETE, VERIFICATION_BLOCKED
    clarifications: List[CitizenClarificationItemResponse]


class CitizenVerificationStatusResponse(BaseModel):
    """Backend-authoritative verification readiness metrics for citizen application."""
    application_id: uuid.UUID
    application_ref: str
    scheme_code: str
    scheme_name: str
    verification_status: str
    total_evidence_count: int
    verified_evidence_count: int
    pending_evidence_count: int
    clarification_required_count: int
    rejected_evidence_count: int
    open_clarification_count: int


# ==============================================================================
# Officer-Facing Clarification & History Schemas
# ==============================================================================

class OfficerClarificationRequestPayload(BaseModel):
    """Payload sent by an officer to demand clarification on an evidence item."""
    reason: str = Field(
        ...,
        min_length=3,
        max_length=4000,
        description="Mandatory clear explanation of the defect or missing details required from the citizen",
    )
    notes: Optional[str] = Field(
        None,
        max_length=4000,
        description="Optional internal notes for administrative review",
    )

    model_config = ConfigDict(extra="forbid")


class OfficerClarificationItemResponse(BaseModel):
    """Full operational view of a clarification request for officer inspection."""
    id: uuid.UUID
    journey_id: uuid.UUID
    evidence_id: Optional[uuid.UUID] = None
    claim_id: Optional[uuid.UUID] = None
    round: int
    requesting_officer: str
    requesting_officer_role: str
    request_reason: str
    notes: Optional[str] = None
    status: str
    requested_at: datetime
    response_text: Optional[str] = None
    responded_at: Optional[datetime] = None
    replacement_evidence_id: Optional[uuid.UUID] = None
    resolution_notes: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OfficerVerificationRecordResponse(BaseModel):
    """Historical audit-preserving verification finding record."""
    id: uuid.UUID
    evidence_id: Optional[uuid.UUID] = None
    claim_id: Optional[uuid.UUID] = None
    round: int = 1
    verification_method: str
    status: str
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    details: Optional[Dict[str, Any]] = None
    clarification_request_id: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OfficerVerificationHistoryResponse(BaseModel):
    """Comprehensive multi-round verification history and audit trail."""
    journey_id: uuid.UUID
    verification_status: str
    current_round: int
    verification_records: List[OfficerVerificationRecordResponse]
    clarification_requests: List[OfficerClarificationItemResponse]
    audit_events: List[OfficerAuditEventResponse]
