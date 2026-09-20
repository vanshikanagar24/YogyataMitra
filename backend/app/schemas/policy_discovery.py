"""Pydantic request and response schemas for AI Policy Discovery and Review."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CandidateDiscoverRequest(BaseModel):
    """Request payload to initiate candidate policy discovery for a statutory scheme."""
    scheme_code: str = Field(..., description="Scheme identifier code (e.g. PM_KISAN or SSY)")


class CandidateReviewRequest(BaseModel):
    """Request payload to record an officer determination on a policy candidate."""
    action: str = Field(
        ...,
        description="Review determination: START_REVIEW, APPROVE, REJECT, REQUEST_CLARIFICATION, ARCHIVE",
    )
    reason: Optional[str] = Field(
        default=None,
        description="Mandatory justification reason for APPROVE, REJECT, or REQUEST_CLARIFICATION",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Optional supervisory notes or review remarks",
    )


class PolicyDiscoveryReviewEventResponse(BaseModel):
    """Schema for an immutable append-only review event in the audit trail."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_id: uuid.UUID
    actor_identity: str
    actor_role: str
    previous_status: Optional[str] = None
    new_status: str
    action: str
    reason: Optional[str] = None
    details_json: Optional[Dict[str, Any]] = None
    created_at: datetime


class PolicyDiscoveryCandidateResponse(BaseModel):
    """Schema for a discovered policy candidate dossier."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scheme_id: uuid.UUID
    scheme_code: Optional[str] = None
    scheme_name: Optional[str] = None
    title: str
    candidate_type: str
    candidate_text_en: str
    candidate_text_hi: str
    normalized_concept: str
    source_url: str
    source_title: str
    source_publisher: str
    source_document_identifier: Optional[str] = None
    source_publication_date: Optional[datetime] = None
    source_effective_date: Optional[datetime] = None
    source_excerpt: str
    discovered_at: datetime
    retrieved_at: Optional[datetime] = None
    adversarial_flag_detected: bool = False
    discovered_by: str
    ai_provider: str
    ai_model: str
    ai_run_id: str
    extraction_confidence: float
    confidence_explanation: Optional[str] = None
    uncertainty_notes: Optional[str] = None
    questions_for_reviewer: Optional[List[str]] = None
    provenance_status: str
    effective_date_status: str
    conflict_detected: bool
    conflict_details_json: Optional[Dict[str, Any]] = None
    duplicate_status: str
    duplicate_of_id: Optional[uuid.UUID] = None
    review_status: str
    reviewer_id: Optional[str] = None
    reviewer_role: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    reviewer_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    review_events: Optional[List[PolicyDiscoveryReviewEventResponse]] = None


class PolicyDiscoveryQueueResponse(BaseModel):
    """Schema for the paginated candidate queue with operational metrics."""
    candidates: List[PolicyDiscoveryCandidateResponse]
    total: int
    metrics: Dict[str, int]
