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
    OfficerAssessmentResponse,
    OfficerAssignmentRequest,
    OfficerAssignmentResponse,
    OfficerAuditEventResponse,
    OfficerCaseDetailResponse,
    OfficerCaseEvaluationExecuteRequest,
    OfficerCaseReviewRequest,
    OfficerDashboardStatsResponse,
    OfficerEvidenceResponse,
    OfficerEvidenceVerifyRequest,
    OfficerLoginRequest,
    OfficerLoginResponse,
    OfficerQueueListResponse,
    OfficerReassignmentRequest,
)
from app.schemas.clarification import (
    OfficerClarificationItemResponse,
    OfficerClarificationRequestPayload,
    OfficerVerificationHistoryResponse,
)
from app.services.evaluation_service import EvaluationService
from app.services.assignment_service import (
    assign_journey_auto,
    assign_journey_manual,
    compute_sla_status,
    get_assignment_history,
    get_officer_workload_metrics,
    reassign_journey,
)
from app.services.officer_service import (
    get_case_detail,
    get_officer_queue,
    record_case_review,
    verify_evidence_item,
)
from app.services.verification_service import (
    get_verification_history,
    request_clarification,
    verify_evidence,
    verify_officer_case_access,
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
# Operational Dashboard & Workload
# ==============================================================================

@router.get(
    "/dashboard/stats",
    response_model=OfficerDashboardStatsResponse,
    summary="Officer Operational Dashboard Metrics",
    description="Returns real database-backed workload and SLA counters for the authenticated officer.",
)
async def get_dashboard_stats(
    session: AsyncSession = Depends(get_db),
    current_officer: Dict[str, Any] = Depends(get_current_officer),
) -> OfficerDashboardStatsResponse:
    metrics = await get_officer_workload_metrics(
        session=session,
        officer_identity=current_officer.get("sub") or current_officer.get("email"),
    )
    return OfficerDashboardStatsResponse(**metrics)


# ==============================================================================
# Verification Queue
# ==============================================================================

@router.get(
    "/queue",
    response_model=OfficerQueueListResponse,
    summary="Verification Queue",
    description="List cases pending verification, in review, or escalated with assignment and SLA filter options.",
)
async def list_verification_queue(
    status: Optional[str] = Query(None, description="Filter by status: PENDING, IN_REVIEW, ESCALATED, COMPLETED, ALL"),
    scheme: Optional[str] = Query(None, description="Filter by scheme: PM_KISAN, SSY, ALL"),
    sla: Optional[str] = Query(None, description="Filter by SLA status: NOT_DUE, DUE_SOON, OVERDUE, COMPLETED, ALL"),
    assigned_to_me: Optional[bool] = Query(None, description="Filter to cases actively assigned to current officer"),
    unassigned: Optional[bool] = Query(None, description="Filter to cases with no active officer assignment"),
    session: AsyncSession = Depends(get_db),
    current_officer: Dict[str, Any] = Depends(get_current_officer),
) -> OfficerQueueListResponse:
    officer_email = current_officer.get("sub") or current_officer.get("email")
    return await get_officer_queue(
        session=session,
        status_filter=status,
        scheme_filter=scheme,
        sla_filter=sla,
        assigned_to_me=assigned_to_me,
        unassigned_only=unassigned,
        current_officer_identity=officer_email,
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
# Evidence Verification & Clarification Endpoints (Phase E)
# ==============================================================================

@router.get(
    "/cases/{journey_id}/evidence",
    response_model=List[OfficerEvidenceResponse],
    summary="Case Evidence List",
    description="Retrieve list of submitted evidence items with verification findings and clarification status.",
)
async def get_case_evidence(
    journey_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_officer: Dict[str, Any] = Depends(get_current_officer),
) -> List[OfficerEvidenceResponse]:
    detail = await get_case_detail(session=session, journey_id=journey_id)
    return detail.evidence_items


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
    # Enforce object-level case assignment authorization
    await verify_officer_case_access(session, journey_id, current_officer)

    action_upper = payload.action.upper().strip()
    if action_upper == "REQUEST_CLARIFICATION":
        clean_reason = payload.reason.strip() if payload.reason else ""
        if not clean_reason:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="A mandatory justification reason is required when requesting clarification.",
            )
        await request_clarification(
            session=session,
            journey_id=journey_id,
            evidence_id=evidence_id,
            reason=clean_reason,
            notes=payload.notes,
            current_officer=current_officer,
        )
        detail = await get_case_detail(session=session, journey_id=journey_id)
        for ev in detail.evidence_items:
            if ev.id == evidence_id:
                return ev
        raise HTTPException(status_code=404, detail="Evidence item not found")
    else:
        return await verify_evidence(
            session=session,
            journey_id=journey_id,
            evidence_id=evidence_id,
            action=payload.action,
            reason=payload.reason,
            notes=payload.notes,
            current_officer=current_officer,
        )


@router.post(
    "/cases/{journey_id}/evidence/{evidence_id}/clarification",
    response_model=OfficerClarificationItemResponse,
    summary="Request Evidence Clarification",
    description="Officer initiates a formal clarification request on a submitted evidence item.",
)
async def request_evidence_clarification(
    journey_id: uuid.UUID,
    evidence_id: uuid.UUID,
    payload: OfficerClarificationRequestPayload,
    session: AsyncSession = Depends(get_db),
    current_officer: Dict[str, Any] = Depends(get_current_officer),
) -> OfficerClarificationItemResponse:
    # Enforce object-level case assignment authorization
    await verify_officer_case_access(session, journey_id, current_officer)

    cr = await request_clarification(
        session=session,
        journey_id=journey_id,
        evidence_id=evidence_id,
        reason=payload.reason,
        notes=payload.notes,
        current_officer=current_officer,
    )
    return OfficerClarificationItemResponse(
        id=cr.id,
        journey_id=cr.journey_id,
        evidence_id=cr.evidence_id,
        claim_id=cr.claim_id,
        round=cr.round,
        requesting_officer=cr.requesting_officer,
        requesting_officer_role=cr.requesting_officer_role,
        request_reason=cr.request_reason,
        notes=cr.notes,
        status=cr.status.value,
        requested_at=cr.requested_at,
        response_text=cr.response_text,
        responded_at=cr.responded_at,
        replacement_evidence_id=cr.replacement_evidence_id,
        resolution_notes=cr.resolution_notes,
        resolved_at=cr.resolved_at,
        resolved_by=cr.resolved_by,
        created_at=cr.created_at,
    )


@router.get(
    "/cases/{journey_id}/verification-history",
    response_model=OfficerVerificationHistoryResponse,
    summary="Case Verification History & Rounds",
    description="Returns complete multi-round verification history, clarification requests, and audit trail.",
)
async def get_case_verification_history(
    journey_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_officer: Dict[str, Any] = Depends(get_current_officer),
) -> OfficerVerificationHistoryResponse:
    return await get_verification_history(session=session, journey_id=journey_id)


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
    # Enforce object-level case assignment authorization
    await verify_officer_case_access(session, journey_id, current_officer)

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


# ==============================================================================
# Officer Assignment & SLA Management (Phase D)
# ==============================================================================

def _format_assignment_response(assign) -> OfficerAssignmentResponse:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    sla_st = compute_sla_status(assign.due_at, assign.status, now)
    return OfficerAssignmentResponse(
        id=assign.id,
        journey_id=assign.journey_id,
        officer_identity=assign.officer_identity,
        officer_name=assign.officer_name,
        assigned_by=assign.assigned_by,
        assigned_at=assign.assigned_at,
        due_at=assign.due_at,
        sla_duration_hours=assign.sla_duration_hours,
        status=assign.status.value,
        is_active=assign.is_active,
        reassigned_to_id=assign.reassigned_to_id,
        reassignment_reason=assign.reassignment_reason,
        sla_status=sla_st.value,
        created_at=assign.created_at,
        updated_at=assign.updated_at,
    )


@router.post(
    "/cases/{journey_id}/assign",
    response_model=OfficerAssignmentResponse,
    summary="Manual Officer Assignment",
    description="Manually assigns an evaluation journey to a specific verified officer.",
)
async def assign_case_manually(
    journey_id: uuid.UUID,
    payload: OfficerAssignmentRequest,
    session: AsyncSession = Depends(get_db),
    current_officer: Dict[str, Any] = Depends(get_current_officer),
) -> OfficerAssignmentResponse:
    actor_email = current_officer.get("sub") or current_officer.get("email") or "OFFICER"
    actor_role = current_officer.get("role", "OFFICER")
    assignment = await assign_journey_manual(
        session=session,
        journey_id=journey_id,
        officer_identity=payload.officer_identity,
        assigned_by=actor_email,
        assigned_by_role=actor_role,
        sla_hours=payload.sla_hours,
        reason=payload.reason,
    )
    return _format_assignment_response(assignment)


@router.post(
    "/cases/{journey_id}/reassign",
    response_model=OfficerAssignmentResponse,
    summary="Auditable Case Reassignment",
    description="Reassigns an active case to a new officer with mandatory justification, preserving historical records.",
)
async def reassign_case(
    journey_id: uuid.UUID,
    payload: OfficerReassignmentRequest,
    session: AsyncSession = Depends(get_db),
    current_officer: Dict[str, Any] = Depends(get_current_officer),
) -> OfficerAssignmentResponse:
    actor_email = current_officer.get("sub") or current_officer.get("email") or "OFFICER"
    actor_role = current_officer.get("role", "OFFICER")
    assignment = await reassign_journey(
        session=session,
        journey_id=journey_id,
        new_officer_identity=payload.new_officer_identity,
        reassigned_by=actor_email,
        reassigned_by_role=actor_role,
        reason=payload.reason,
        sla_hours=payload.sla_hours,
    )
    return _format_assignment_response(assignment)


@router.post(
    "/cases/{journey_id}/auto-assign",
    response_model=OfficerAssignmentResponse,
    summary="Deterministic Least-Loaded Auto-Assignment",
    description="Assigns an unassigned journey using deterministic least-loaded workload balancing.",
)
async def auto_assign_case(
    journey_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_officer: Dict[str, Any] = Depends(get_current_officer),
) -> OfficerAssignmentResponse:
    assignment = await assign_journey_auto(session=session, journey_id=journey_id)
    return _format_assignment_response(assignment)


@router.get(
    "/cases/{journey_id}/assignments",
    response_model=List[OfficerAssignmentResponse],
    summary="Case Assignment History",
    description="Returns complete historical trail of assignments and reassignments for a case.",
)
async def list_case_assignments(
    journey_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_officer: Dict[str, Any] = Depends(get_current_officer),
) -> List[OfficerAssignmentResponse]:
    history = await get_assignment_history(session=session, journey_id=journey_id)
    return [_format_assignment_response(a) for a in history]


# ==============================================================================
# Statutory Evaluation & Decision Engine Endpoints (Phase F)
# ==============================================================================

@router.post(
    "/cases/{journey_id}/evaluate",
    response_model=OfficerAssessmentResponse,
    summary="Execute Statutory Evaluation",
    description="Executes deterministic rule-based evaluation against the case's bound policy version.",
)
async def evaluate_case_endpoint(
    journey_id: uuid.UUID,
    payload: Optional[OfficerCaseEvaluationExecuteRequest] = None,
    session: AsyncSession = Depends(get_db),
    current_officer: Dict[str, Any] = Depends(get_current_officer),
) -> OfficerAssessmentResponse:
    # Enforce Phase D & E object-level case assignment authorization
    await verify_officer_case_access(session, journey_id, current_officer)

    actor_email = current_officer.get("sub") or current_officer.get("email") or "OFFICER"
    actor_role = current_officer.get("role", "OFFICER")
    notes = payload.notes if payload else None

    eval_service = EvaluationService(session)
    return await eval_service.evaluate_case(
        journey_id=journey_id,
        actor_identity=actor_email,
        actor_role=actor_role,
        notes=notes,
    )


@router.get(
    "/cases/{journey_id}/evaluation",
    response_model=OfficerAssessmentResponse,
    summary="Latest Case Evaluation",
    description="Retrieve the latest statutory evaluation determination and rule-by-rule trace for a case.",
)
async def get_case_evaluation_endpoint(
    journey_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_officer: Dict[str, Any] = Depends(get_current_officer),
) -> OfficerAssessmentResponse:
    await verify_officer_case_access(session, journey_id, current_officer)
    eval_service = EvaluationService(session)
    return await eval_service.get_case_evaluation(journey_id)


@router.get(
    "/cases/{journey_id}/evaluation/history",
    response_model=List[OfficerAssessmentResponse],
    summary="Case Evaluation History",
    description="Retrieve the complete historical audit log of statutory evaluations for a case.",
)
async def get_case_evaluation_history_endpoint(
    journey_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_officer: Dict[str, Any] = Depends(get_current_officer),
) -> List[OfficerAssessmentResponse]:
    await verify_officer_case_access(session, journey_id, current_officer)
    eval_service = EvaluationService(session)
    return await eval_service.get_case_evaluation_history(journey_id)
