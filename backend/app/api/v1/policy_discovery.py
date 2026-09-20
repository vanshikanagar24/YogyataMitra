"""API Router for AI Policy Discovery and Human Approval (Phase 15).

Provides internal officer endpoints for:
- Initiating AI candidate discovery from official government sources
- Querying the candidate queue with filtering and status metrics
- Inspecting candidate dossiers (AI statements, official sources, provenance, conflict analysis)
- Recording human reviewer determinations (APPROVE, REJECT, REQUEST_CLARIFICATION)
- Querying chronological review audit trail events

Strictly protected by internal officer RBAC (OFFICER and SUPERVISOR roles only).
Citizen access is unconditionally rejected with HTTP 403.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_officer, require_role
from app.core.database import get_db
from app.models.policy_discovery import CandidateReviewStatus, CandidateType, PolicyDiscoveryCandidate
from app.schemas.policy_discovery import (
    CandidateDiscoverRequest,
    CandidateReviewRequest,
    PolicyDiscoveryCandidateResponse,
    PolicyDiscoveryQueueResponse,
    PolicyDiscoveryReviewEventResponse,
)
from app.services.policy_discovery_service import (
    discover_candidates_for_scheme,
    get_candidate_detail,
    get_candidate_history,
    get_candidates_queue,
    record_candidate_review,
)

router = APIRouter(prefix="/officer/policy-discovery", tags=["AI Policy Discovery & Review"])


def _serialize_candidate(c: PolicyDiscoveryCandidate) -> PolicyDiscoveryCandidateResponse:
    """Helper to convert ORM model to API response with serialized enums."""
    c_type = c.candidate_type.value if hasattr(c.candidate_type, "value") else str(c.candidate_type)
    prov_status = c.provenance_status.value if hasattr(c.provenance_status, "value") else str(c.provenance_status)
    eff_status = c.effective_date_status.value if hasattr(c.effective_date_status, "value") else str(c.effective_date_status)
    dup_status = c.duplicate_status.value if hasattr(c.duplicate_status, "value") else str(c.duplicate_status)
    rev_status = c.review_status.value if hasattr(c.review_status, "value") else str(c.review_status)

    events_resp = None
    if "review_events" in c.__dict__ and c.__dict__["review_events"] is not None:
        events_resp = [
            PolicyDiscoveryReviewEventResponse(
                id=ev.id,
                candidate_id=ev.candidate_id,
                actor_identity=ev.actor_identity,
                actor_role=ev.actor_role,
                previous_status=ev.previous_status,
                new_status=ev.new_status,
                action=ev.action,
                reason=ev.reason,
                details_json=ev.details_json,
                created_at=ev.created_at,
            )
            for ev in c.__dict__["review_events"]
        ]

    scheme_code = None
    scheme_name = None
    if "scheme" in c.__dict__ and c.__dict__["scheme"] is not None:
        scheme_code = c.__dict__["scheme"].scheme_code
        scheme_name = c.__dict__["scheme"].name_en

    return PolicyDiscoveryCandidateResponse(
        id=c.id,
        scheme_id=c.scheme_id,
        scheme_code=scheme_code,
        scheme_name=scheme_name,
        title=c.title,
        candidate_type=c_type,
        candidate_text_en=c.candidate_text_en,
        candidate_text_hi=c.candidate_text_hi,
        normalized_concept=c.normalized_concept,
        source_url=c.source_url,
        source_title=c.source_title,
        source_publisher=c.source_publisher,
        source_document_identifier=c.source_document_identifier,
        source_publication_date=c.source_publication_date,
        source_effective_date=c.source_effective_date,
        source_excerpt=c.source_excerpt,
        discovered_at=c.discovered_at,
        retrieved_at=getattr(c, "retrieved_at", c.discovered_at),
        adversarial_flag_detected=getattr(c, "adversarial_flag_detected", False),
        discovered_by=c.discovered_by,
        ai_provider=c.ai_provider,
        ai_model=c.ai_model,
        ai_run_id=c.ai_run_id,
        extraction_confidence=c.extraction_confidence,
        confidence_explanation=c.confidence_explanation,
        uncertainty_notes=c.uncertainty_notes,
        questions_for_reviewer=c.questions_for_reviewer,
        provenance_status=prov_status,
        effective_date_status=eff_status,
        conflict_detected=c.conflict_detected,
        conflict_details_json=c.conflict_details_json,
        duplicate_status=dup_status,
        duplicate_of_id=c.duplicate_of_id,
        review_status=rev_status,
        reviewer_id=c.reviewer_id,
        reviewer_role=c.reviewer_role,
        reviewed_at=c.reviewed_at,
        reviewer_reason=c.reviewer_reason,
        created_at=c.created_at,
        updated_at=c.updated_at,
        review_events=events_resp,
    )


# ==============================================================================
# Discovery Trigger Endpoint
# ==============================================================================

@router.post(
    "/discover",
    response_model=List[PolicyDiscoveryCandidateResponse],
    summary="Trigger AI Policy Discovery",
    description="Discovers official candidate policy statements for a specified scheme.",
)
async def trigger_policy_discovery(
    payload: CandidateDiscoverRequest,
    session: AsyncSession = Depends(get_db),
    officer: Dict[str, Any] = Depends(get_current_officer),
) -> List[PolicyDiscoveryCandidateResponse]:
    candidates = await discover_candidates_for_scheme(
        session=session,
        scheme_code=payload.scheme_code,
        actor_email=officer["email"],
        actor_role=officer["role"],
    )
    return [_serialize_candidate(c) for c in candidates]


# ==============================================================================
# Candidate Queue Inspection
# ==============================================================================

@router.get(
    "/candidates",
    response_model=PolicyDiscoveryQueueResponse,
    summary="Query Policy Discovery Queue",
    description="Retrieve paginated candidate queue with filters and status metrics.",
)
async def list_candidates_queue(
    status_filter: Optional[str] = Query(None, alias="status"),
    scheme_filter: Optional[str] = Query(None, alias="scheme"),
    candidate_type: Optional[str] = Query(None, alias="type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    officer: Dict[str, Any] = Depends(get_current_officer),
) -> PolicyDiscoveryQueueResponse:
    items, total, metrics = await get_candidates_queue(
        session=session,
        status_filter=status_filter,
        scheme_filter=scheme_filter,
        candidate_type=candidate_type,
        skip=skip,
        limit=limit,
    )
    serialized = [_serialize_candidate(c) for c in items]
    return PolicyDiscoveryQueueResponse(
        candidates=serialized,
        total=total,
        metrics=metrics,
    )


# ==============================================================================
# Candidate Dossier Detail
# ==============================================================================

@router.get(
    "/candidates/{candidate_id}",
    response_model=PolicyDiscoveryCandidateResponse,
    summary="Get Candidate Dossier Detail",
    description="Retrieve complete candidate policy intelligence and review history.",
)
async def get_candidate_by_id(
    candidate_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    officer: Dict[str, Any] = Depends(get_current_officer),
) -> PolicyDiscoveryCandidateResponse:
    candidate = await get_candidate_detail(session, candidate_id)
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy discovery candidate '{candidate_id}' not found",
        )
    return _serialize_candidate(candidate)


# ==============================================================================
# Candidate Review Determination
# ==============================================================================

@router.post(
    "/candidates/{candidate_id}/review",
    response_model=PolicyDiscoveryCandidateResponse,
    summary="Record Officer Candidate Review Determination",
    description="Approve, reject, request clarification, or transition candidate lifecycle state.",
)
async def review_candidate(
    candidate_id: uuid.UUID,
    payload: CandidateReviewRequest,
    session: AsyncSession = Depends(get_db),
    officer: Dict[str, Any] = Depends(get_current_officer),
) -> PolicyDiscoveryCandidateResponse:
    updated_candidate = await record_candidate_review(
        session=session,
        candidate_id=candidate_id,
        action=payload.action,
        reason=payload.reason or payload.notes or "",
        actor_email=officer["email"],
        actor_role=officer["role"],
        notes=payload.notes,
    )
    return _serialize_candidate(updated_candidate)


# ==============================================================================
# Candidate Audit History
# ==============================================================================

@router.get(
    "/candidates/{candidate_id}/history",
    response_model=List[PolicyDiscoveryReviewEventResponse],
    summary="Get Candidate Review Audit History",
    description="Retrieve chronological append-only audit events for a policy candidate.",
)
async def list_candidate_audit_history(
    candidate_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    officer: Dict[str, Any] = Depends(get_current_officer),
) -> List[PolicyDiscoveryReviewEventResponse]:
    candidate = await get_candidate_detail(session, candidate_id)
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy discovery candidate '{candidate_id}' not found",
        )
    events = await get_candidate_history(session, candidate_id)
    return [
        PolicyDiscoveryReviewEventResponse(
            id=ev.id,
            candidate_id=ev.candidate_id,
            actor_identity=ev.actor_identity,
            actor_role=ev.actor_role,
            previous_status=ev.previous_status,
            new_status=ev.new_status,
            action=ev.action,
            reason=ev.reason,
            details_json=ev.details_json,
            created_at=ev.created_at,
        )
        for ev in events
    ]
