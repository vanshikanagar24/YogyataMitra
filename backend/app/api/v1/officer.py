"""Officer / Human Verification Portal API Router (Phase 14).

Provides authenticated endpoints for:
- Development officer login and profile retrieval
- Verification queue inspection with scheme and status filters
- Full case dossier inspection (claims, evidence, assessment, policy provenance)
- Evidence verification determinations (verify, reject, request clarification)
- Human review decisions (verified, clarification required, rejected, escalated, completed)
- Immutable append-only audit trail logging
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_officer, require_role
from app.core.database import get_db
from app.core.security import authenticate_user, create_access_token
from app.schemas.officer import (
    OfficerAuditEventResponse,
    OfficerCaseDetailResponse,
    OfficerCaseReviewRequest,
    OfficerEvidenceResponse,
    OfficerEvidenceVerifyRequest,
    OfficerLoginRequest,
    OfficerLoginResponse,
    OfficerQueueListResponse,
)
from app.services.officer_service import (
    get_case_detail,
    get_officer_queue,
    record_case_review,
    verify_evidence_item,
)

router = APIRouter(prefix="/officer", tags=["Officer Verification Portal"])


# ==============================================================================
# Authentication Endpoints
# ==============================================================================

@router.post(
    "/auth/login",
    response_model=OfficerLoginResponse,
    summary="Development Officer Login",
    description="Development-only authentication endpoint with pre-seeded demo officer accounts.",
)
async def officer_login(credentials: OfficerLoginRequest) -> OfficerLoginResponse:
    user = authenticate_user(credentials.email, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password for officer portal",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user["role"] not in ("OFFICER", "SUPERVISOR", "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Citizen accounts cannot access internal verification portal",
        )

    token_data = {
        "sub": user["email"],
        "role": user["role"],
        "name": user["name"],
        "designation": user["designation"],
        "department": user["department"],
    }
    access_token = create_access_token(data=token_data)

    return OfficerLoginResponse(
        access_token=access_token,
        token_type="bearer",
        officer_name=user["name"],
        officer_role=user["role"],
        designation=user["designation"],
        department=user["department"],
        demo_environment=True,
    )


@router.get(
    "/auth/me",
    summary="Current Officer Profile",
    description="Returns authenticated officer profile from Bearer JWT.",
)
async def get_my_profile(
    current_officer: Dict[str, Any] = Depends(get_current_officer),
) -> Dict[str, Any]:
    return current_officer


# ==============================================================================
# Verification Queue
# ==============================================================================

@router.get(
    "/queue",
    response_model=OfficerQueueListResponse,
    summary="Verification Queue",
    description="List cases pending verification, in review, or escalated with filter options.",
)
async def list_verification_queue(
    status: Optional[str] = Query(None, description="Filter by status: PENDING, IN_REVIEW, ESCALATED, COMPLETED, ALL"),
    scheme: Optional[str] = Query(None, description="Filter by scheme: PM_KISAN, SSY, ALL"),
    session: AsyncSession = Depends(get_db),
    current_officer: Dict[str, Any] = Depends(get_current_officer),
) -> OfficerQueueListResponse:
    return await get_officer_queue(
        session=session,
        status_filter=status,
        scheme_filter=scheme,
    )


# ==============================================================================
# Case Dossier & Inspection
# ==============================================================================

@router.get(
    "/cases/{journey_id}",
    response_model=OfficerCaseDetailResponse,
    summary="Case Inspection Dossier",
    description="Retrieve comprehensive dossier including claims, evidence, assessment, and policy provenance.",
)
async def get_case_dossier(
    journey_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_officer: Dict[str, Any] = Depends(get_current_officer),
) -> OfficerCaseDetailResponse:
    return await get_case_detail(session=session, journey_id=journey_id)


# ==============================================================================
# Evidence Verification Determination
# ==============================================================================

@router.post(
    "/cases/{journey_id}/evidence/{evidence_id}/verify",
    response_model=OfficerEvidenceResponse,
    summary="Evidence Verification Determination",
    description="Verify, reject, or request clarification on an individual evidence item.",
)
async def verify_case_evidence(
    journey_id: uuid.UUID,
    evidence_id: uuid.UUID,
    payload: OfficerEvidenceVerifyRequest,
    session: AsyncSession = Depends(get_db),
    current_officer: Dict[str, Any] = Depends(get_current_officer),
) -> OfficerEvidenceResponse:
    return await verify_evidence_item(
        session=session,
        journey_id=journey_id,
        evidence_id=evidence_id,
        request=payload,
        current_officer=current_officer,
    )


# ==============================================================================
# Human Review Decision
# ==============================================================================

@router.post(
    "/cases/{journey_id}/review",
    response_model=OfficerCaseDetailResponse,
    summary="Record Human Review Decision",
    description="Record overall determination (VERIFIED, CLARIFICATION_REQUIRED, REJECTED, ESCALATED, COMPLETED).",
)
async def review_case(
    journey_id: uuid.UUID,
    payload: OfficerCaseReviewRequest,
    session: AsyncSession = Depends(get_db),
    current_officer: Dict[str, Any] = Depends(get_current_officer),
) -> OfficerCaseDetailResponse:
    return await record_case_review(
        session=session,
        journey_id=journey_id,
        request=payload,
        current_officer=current_officer,
    )


# ==============================================================================
# Audit History
# ==============================================================================

@router.get(
    "/cases/{journey_id}/audit-trail",
    response_model=List[OfficerAuditEventResponse],
    summary="Case Audit Trail",
    description="Retrieve immutable append-only audit trail records for this case.",
)
async def get_case_audit_trail(
    journey_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_officer: Dict[str, Any] = Depends(get_current_officer),
) -> List[OfficerAuditEventResponse]:
    detail = await get_case_detail(session=session, journey_id=journey_id)
    return detail.audit_history
