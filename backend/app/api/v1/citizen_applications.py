"""Citizen Portal Applications API Router (Phase B & Phase C).

Provides authenticated endpoints for:
- Listing all applications owned by the authenticated citizen
- Retrieving detailed application dossier with claims, evidence, and audit timeline
- Computing dashboard statistics and summary metrics
- Browsing available active canonical schemes (PM_KISAN, SSY)
- Inspecting statutory scheme application requirements (fields and evidence specifications)
- Initiating a new application in DRAFT state bound to the active statutory policy version
- Saving in-progress draft applications
- Formally submitting applications with citizen-declared facts and documentary evidence

Strict Security Invariants:
- All endpoints require an authenticated citizen JWT (HTTPBearer via get_current_citizen)
- IDOR Protection: Queries strictly filter by the authenticated citizen's database ID
- Cross-citizen application lookup returns 404 (Not Found) without leaking presence
- Historical Policy Immutability: Application binds to the resolved PolicyVersion at creation
  and never silently mutates to future policy versions.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_citizen
from app.api.v1.journeys import (
    to_journey_claim_response,
    to_journey_evidence_response,
)
from app.core.database import get_db
from app.models.citizen import Citizen, Claim, Evidence, VerificationRecord
from app.models.clarification import ClarificationRequest
from app.models.enums import (
    ClaimStatus,
    ClarificationStatus,
    EligibilityResult,
    EvidenceStatus,
    JourneyState,
    SchemeStatus,
    VerificationCompleteness,
)
from app.models.evaluation import EvaluationTrace
from app.models.journey import EvaluationJourney, JourneyTransitionRecord
from app.models.scheme import PolicyVersion, Scheme
from app.schemas.api import ErrorResponse, SchemeSummaryResponse
from app.schemas.citizen_application import (
    CitizenApplicationCreateRequest,
    CitizenApplicationDetail,
    CitizenApplicationDraftUpdateRequest,
    CitizenApplicationSubmitRequest,
    CitizenApplicationSummary,
    CitizenDashboardStats,
    CitizenDecisionResponse,
    EvaluationSummary,
    SchemeRequirementsResponse,
)
from app.services.evaluation_service import EvaluationService
from app.schemas.clarification import (
    CitizenClarificationItemResponse,
    CitizenClarificationListResponse,
    CitizenClarificationRespondRequest,
    CitizenVerificationStatusResponse,
)
from app.schemas.journey import JourneyTransitionRecordResponse
from app.services.citizen_scheme_requirements import get_scheme_requirements
from app.services.form_metadata_service import (
    SchemeFormNotSupportedError,
    get_policy_form_metadata,
)
from app.services.form_metadata_validator import validate_citizen_form_submission
from app.services.policy_loader import SchemeNotFoundError
from app.services.policy_selector import PolicyVersionNotFoundError, get_policy_version
from app.services.verification_service import (
    compute_verification_status,
    get_citizen_clarifications,
    respond_to_clarification,
)

router = APIRouter(prefix="/citizen", tags=["Citizen Applications"])

STATE_LABELS: Dict[JourneyState, tuple[str, str]] = {
    JourneyState.DRAFT: ("Draft Application", "प्रारूप आवेदन"),
    JourneyState.FACTS_COLLECTED: ("Submitted", "जमा किया गया"),
    JourneyState.EVIDENCE_PENDING: ("Under Review / Evidence Submitted", "समीक्षाधीन / साक्ष्य प्रस्तुत"),
    JourneyState.VERIFICATION_IN_PROGRESS: ("Under Verification", "सत्यापन प्रगति पर"),
    JourneyState.READY_FOR_EVALUATION: ("Ready for Evaluation", "मूल्यांकन के लिए तैयार"),
    JourneyState.EVALUATED: ("Evaluated", "मूल्यांकित"),
    JourneyState.ACTION_REQUIRED: ("Action Required", "कार्रवाई आवश्यक"),
    JourneyState.COMPLETED: ("Completed", "पूर्ण"),
}


def build_application_ref(journey_id: uuid.UUID, created_at: Optional[datetime]) -> str:
    """Format canonical human-readable application reference string."""
    year = created_at.year if created_at else datetime.now(timezone.utc).year
    hex_id = str(journey_id).replace("-", "")[:8].upper()
    return f"APP-{year}-{hex_id}"


def journey_to_summary(
    journey: EvaluationJourney,
    scheme: Optional[Scheme] = None,
    evaluation: Optional[EvaluationTrace] = None,
    policy_version: Optional[PolicyVersion] = None,
) -> CitizenApplicationSummary:
    """Transform an EvaluationJourney entity into CitizenApplicationSummary."""
    s = scheme or journey.scheme
    eval_trace = evaluation or journey.latest_evaluation
    labels = STATE_LABELS.get(journey.state, (journey.state.value, journey.state.value))

    pv_id = None
    pv_code = None
    rule_hash = None
    eval_outcome = None

    # Priority 1: Direct bound policy_version on journey (Phase C)
    if "policy_version" in journey.__dict__ and journey.policy_version:
        pv_id = journey.policy_version.id
        pv_code = journey.policy_version.version_code
        rule_hash = journey.policy_version.rule_definition_hash
    elif journey.policy_version_id:
        pv_id = journey.policy_version_id
        if policy_version and policy_version.id == journey.policy_version_id:
            pv_code = policy_version.version_code
            rule_hash = policy_version.rule_definition_hash

    # Priority 2: Fallback to evaluation trace if evaluation was recorded
    if eval_trace:
        eval_outcome = eval_trace.result_state
        if not pv_id:
            pv_id = eval_trace.policy_version_id
        if not pv_code:
            if eval_trace.policy_version:
                pv_code = eval_trace.policy_version.version_code
            elif policy_version:
                pv_code = policy_version.version_code
        if not rule_hash:
            rule_hash = eval_trace.rule_definition_hash

    claims_count = 0
    evidence_count = 0
    if "claims" in journey.__dict__ and journey.__dict__["claims"]:
        claims_list = journey.__dict__["claims"]
        claims_count = len(claims_list)
        for c in claims_list:
            if "evidence_items" in c.__dict__ and c.__dict__["evidence_items"]:
                evidence_count += len(c.__dict__["evidence_items"])

    return CitizenApplicationSummary(
        id=journey.id,
        application_ref=build_application_ref(journey.id, journey.created_at),
        scheme_id=journey.scheme_id,
        scheme_code=s.scheme_code if s else "UNKNOWN",
        scheme_name=s.name_en if s else "Government Scheme",
        scheme_name_hi=s.name_hi if s else None,
        ministry=s.ministry if s else None,
        state=journey.state,
        status_label_en=labels[0],
        status_label_hi=labels[1],
        created_at=journey.created_at,
        updated_at=journey.updated_at,
        submitted_at=journey.submitted_at,
        policy_version_id=pv_id,
        policy_version_code=pv_code,
        rule_definition_hash=rule_hash,
        evaluation_outcome=eval_outcome,
        claims_count=claims_count,
        evidence_count=evidence_count,
    )


async def _resolve_db_citizen(
    current_citizen: Dict[str, Any], db: AsyncSession
) -> Optional[Citizen]:
    """Resolve database Citizen record by synthetic reference in JWT, creating if needed."""
    synthetic_ref = current_citizen.get("citizen_ref")
    if not synthetic_ref:
        return None

    stmt = select(Citizen).where(Citizen.synthetic_reference == synthetic_ref)
    result = await db.execute(stmt)
    db_citizen = result.scalar_one_or_none()
    if not db_citizen:
        db_citizen = Citizen(
            synthetic_reference=synthetic_ref,
            display_name=current_citizen.get("name") or "Citizen",
            state=current_citizen.get("state"),
            district=current_citizen.get("district"),
        )
        db.add(db_citizen)
        await db.commit()
        await db.refresh(db_citizen)
    return db_citizen


# ==============================================================================
# Schemes Catalog & Requirements (Phase C)
# ==============================================================================

CANONICAL_SCHEME_CODES = (
    "PM_KISAN",
    "SSY",
    "PM_KMY",
    "PMUY",
    "PM_VISHWAKARMA",
    "PMAY_G",
    "PMAY_U_2_0",
    "PM_SVANIDHI",
    "PMMVY",
    "IGNOAPS",
)


@router.get(
    "/schemes",
    response_model=List[SchemeSummaryResponse],
    status_code=status.HTTP_200_OK,
    summary="List Canonical Available Schemes for Citizen Portal",
    description="Returns all active schemes available for application filing in the citizen portal.",
    responses={
        200: {"description": "List of available schemes returned successfully."},
        401: {"model": ErrorResponse, "description": "Unauthenticated or invalid token."},
    },
)
async def list_available_schemes(
    current_citizen: Dict[str, Any] = Depends(get_current_citizen),
    db: AsyncSession = Depends(get_db),
) -> List[SchemeSummaryResponse]:
    """List operational canonical schemes available for citizen application."""
    stmt = (
        select(Scheme)
        .where(
            Scheme.status == SchemeStatus.ACTIVE,
            Scheme.scheme_code.in_(CANONICAL_SCHEME_CODES),
        )
        .order_by(Scheme.name_en.asc())
    )
    res = await db.execute(stmt)
    schemes = res.scalars().all()
    return [SchemeSummaryResponse.model_validate(s) for s in schemes]


@router.get(
    "/schemes/{scheme_code}/requirements",
    response_model=SchemeRequirementsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Scheme Application Requirements",
    description="Returns the structured statutory input fields, grouping sections, and evidence requirements for a scheme.",
    responses={
        200: {"description": "Scheme requirements specification returned successfully."},
        400: {"model": ErrorResponse, "description": "Scheme form metadata not configured or available."},
        401: {"model": ErrorResponse, "description": "Unauthenticated or invalid token."},
        404: {"model": ErrorResponse, "description": "Scheme not found or no active policy version."},
    },
)
async def get_requirements(
    scheme_code: str,
    evaluation_date: Optional[date] = None,
    policy_version_id: Optional[uuid.UUID] = None,
    current_citizen: Dict[str, Any] = Depends(get_current_citizen),
    db: AsyncSession = Depends(get_db),
) -> SchemeRequirementsResponse:
    """Retrieve structured data-entry field and evidence specifications for application creation."""
    try:
        return await get_scheme_requirements(
            db,
            scheme_code,
            evaluation_date=evaluation_date,
            policy_version_id=policy_version_id,
        )
    except SchemeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except PolicyVersionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except SchemeFormNotSupportedError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ==============================================================================
# Applications Listing & Dashboard
# ==============================================================================

@router.get(
    "/applications",
    response_model=List[CitizenApplicationSummary],
    status_code=status.HTTP_200_OK,
    summary="List Citizen Welfare Applications",
    description="Returns all welfare applications filed by the authenticated citizen across all schemes.",
    responses={
        200: {"description": "List of citizen applications returned successfully."},
        401: {"model": ErrorResponse, "description": "Unauthenticated or invalid token."},
    },
)
async def list_citizen_applications(
    current_citizen: Dict[str, Any] = Depends(get_current_citizen),
    db: AsyncSession = Depends(get_db),
) -> List[CitizenApplicationSummary]:
    """Retrieve all applications for the authenticated citizen with strict IDOR isolation."""
    db_citizen = await _resolve_db_citizen(current_citizen, db)
    if not db_citizen:
        return []

    stmt = (
        select(EvaluationJourney)
        .where(EvaluationJourney.citizen_id == db_citizen.id)
        .options(
            selectinload(EvaluationJourney.scheme),
            selectinload(EvaluationJourney.policy_version),
            selectinload(EvaluationJourney.latest_evaluation).selectinload(EvaluationTrace.policy_version),
            selectinload(EvaluationJourney.claims).selectinload(Claim.evidence_items),
        )
        .order_by(EvaluationJourney.created_at.desc())
    )
    result = await db.execute(stmt)
    journeys = result.scalars().all()

    return [journey_to_summary(j) for j in journeys]


@router.get(
    "/dashboard/stats",
    response_model=CitizenDashboardStats,
    status_code=status.HTTP_200_OK,
    summary="Citizen Dashboard Statistics",
    description="Computes high-level application metrics and recent applications for the citizen dashboard.",
    responses={
        200: {"description": "Dashboard statistics returned successfully."},
        401: {"model": ErrorResponse, "description": "Unauthenticated or invalid token."},
    },
)
async def get_citizen_dashboard_stats(
    current_citizen: Dict[str, Any] = Depends(get_current_citizen),
    db: AsyncSession = Depends(get_db),
) -> CitizenDashboardStats:
    """Compute dashboard aggregates for the authenticated citizen."""
    db_citizen = await _resolve_db_citizen(current_citizen, db)
    if not db_citizen:
        return CitizenDashboardStats(
            total_applications=0,
            in_progress_count=0,
            evaluated_count=0,
            action_required_count=0,
            recent_applications=[],
        )

    stmt = (
        select(EvaluationJourney)
        .where(EvaluationJourney.citizen_id == db_citizen.id)
        .options(
            selectinload(EvaluationJourney.scheme),
            selectinload(EvaluationJourney.policy_version),
            selectinload(EvaluationJourney.latest_evaluation).selectinload(EvaluationTrace.policy_version),
            selectinload(EvaluationJourney.claims).selectinload(Claim.evidence_items),
        )
        .order_by(EvaluationJourney.created_at.desc())
    )
    result = await db.execute(stmt)
    journeys = result.scalars().all()

    total = len(journeys)
    in_progress = 0
    evaluated = 0
    action_req = 0

    in_progress_states = {
        JourneyState.DRAFT,
        JourneyState.FACTS_COLLECTED,
        JourneyState.EVIDENCE_PENDING,
        JourneyState.VERIFICATION_IN_PROGRESS,
        JourneyState.READY_FOR_EVALUATION,
    }
    evaluated_states = {
        JourneyState.EVALUATED,
        JourneyState.COMPLETED,
    }

    for j in journeys:
        if j.state == JourneyState.ACTION_REQUIRED:
            action_req += 1
        elif j.state in evaluated_states:
            evaluated += 1
        elif j.state in in_progress_states:
            in_progress += 1

    summaries = [journey_to_summary(j) for j in journeys[:5]]

    return CitizenDashboardStats(
        total_applications=total,
        in_progress_count=in_progress,
        evaluated_count=evaluated,
        action_required_count=action_req,
        recent_applications=summaries,
    )


@router.get(
    "/applications/{application_id}",
    response_model=CitizenApplicationDetail,
    status_code=status.HTTP_200_OK,
    summary="Get Application Dossier by ID",
    description="Fetches full details of a specific application including asserted facts, evidence status, and evaluation trace. Strictly IDOR-protected.",
    responses={
        200: {"description": "Application details returned successfully."},
        401: {"model": ErrorResponse, "description": "Unauthenticated or invalid token."},
        404: {"model": ErrorResponse, "description": "Application not found or access denied."},
    },
)
async def get_citizen_application_detail(
    application_id: uuid.UUID,
    current_citizen: Dict[str, Any] = Depends(get_current_citizen),
    db: AsyncSession = Depends(get_db),
) -> CitizenApplicationDetail:
    """Retrieve application dossier with strict IDOR verification."""
    db_citizen = await _resolve_db_citizen(current_citizen, db)
    if not db_citizen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found or does not belong to your account",
        )

    stmt = (
        select(EvaluationJourney)
        .where(
            EvaluationJourney.id == application_id,
            EvaluationJourney.citizen_id == db_citizen.id,
        )
        .options(
            selectinload(EvaluationJourney.scheme),
            selectinload(EvaluationJourney.policy_version),
            selectinload(EvaluationJourney.latest_evaluation).selectinload(EvaluationTrace.policy_version),
            selectinload(EvaluationJourney.claims).selectinload(Claim.evidence_items).selectinload(Evidence.verification_records),
            selectinload(EvaluationJourney.transitions),
            selectinload(EvaluationJourney.clarification_requests).selectinload(ClarificationRequest.replacement_evidence),
        )
    )
    result = await db.execute(stmt)
    journey = result.scalar_one_or_none()

    if not journey:
        # IDOR protection: return 404 to avoid leaking existence of foreign applications
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found or does not belong to your account",
        )

    summary = journey_to_summary(journey)

    # Compute verification readiness and sanitized clarification list
    status_metrics = await compute_verification_status(db, journey.id)
    v_status = status_metrics["verification_status"]

    clarifications_data = []
    has_open_clarification = False
    for cr in (journey.clarification_requests or []):
        if cr.status == ClarificationStatus.OPEN:
            has_open_clarification = True
        repl_name = None
        if cr.replacement_evidence and cr.replacement_evidence.metadata_json:
            repl_name = cr.replacement_evidence.metadata_json.get("document_name")
        clarifications_data.append({
            "id": str(cr.id),
            "round": cr.round,
            "evidence_id": str(cr.evidence_id) if cr.evidence_id else None,
            "claim_id": str(cr.claim_id) if cr.claim_id else None,
            "request_reason": cr.request_reason,
            "status": cr.status.value,
            "requested_at": cr.requested_at.isoformat() if cr.requested_at else None,
            "response_text": cr.response_text,
            "responded_at": cr.responded_at.isoformat() if cr.responded_at else None,
            "has_replacement_evidence": bool(cr.replacement_evidence_id),
            "replacement_evidence_id": str(cr.replacement_evidence_id) if cr.replacement_evidence_id else None,
            "replacement_evidence_name": repl_name,
            "resolved_at": cr.resolved_at.isoformat() if cr.resolved_at else None,
        })

    # Build evaluation summary if available
    eval_summary = None
    if journey.latest_evaluation:
        ev = journey.latest_evaluation
        trace = ev.trace_json or {}
        reasons_en = trace.get("reasons_en", [])
        reasons_hi = trace.get("reasons_hi", [])
        pv_code = ev.policy_version.version_code if ev.policy_version else None

        eval_summary = EvaluationSummary(
            evaluation_id=ev.id,
            result_state=ev.result_state,
            evaluation_date=str(ev.evaluation_date),
            policy_version_code=pv_code,
            rule_definition_hash=ev.rule_definition_hash,
            reasons_en=reasons_en if isinstance(reasons_en, list) else [],
            reasons_hi=reasons_hi if isinstance(reasons_hi, list) else [],
        )

    # Allowed actions based on state
    allowed_actions = ["VIEW_SCHEME"]
    if journey.state == JourneyState.DRAFT:
        allowed_actions.append("UPDATE_DRAFT")
        allowed_actions.append("SUBMIT_APPLICATION")
    elif journey.state == JourneyState.ACTION_REQUIRED:
        allowed_actions.append("UPDATE_FACTS")
        if has_open_clarification:
            allowed_actions.append("RESPOND_CLARIFICATION")
    if journey.state == JourneyState.EVIDENCE_PENDING:
        allowed_actions.append("UPLOAD_EVIDENCE")
    if journey.state in (JourneyState.READY_FOR_EVALUATION, JourneyState.EVALUATED):
        allowed_actions.append("CHECK_ELIGIBILITY")

    return CitizenApplicationDetail(
        **summary.model_dump(),
        citizen_ref=db_citizen.synthetic_reference,
        citizen_name=db_citizen.display_name or current_citizen.get("name"),
        official_url=journey.scheme.official_url if journey.scheme else None,
        claims=[to_journey_claim_response(c) for c in (journey.claims or [])],
        transitions=[
            JourneyTransitionRecordResponse.model_validate(t)
            for t in (journey.transitions or [])
        ],
        latest_evaluation=eval_summary,
        allowed_actions=allowed_actions,
        verification_status=v_status,
        clarifications=clarifications_data,
    )


# ==============================================================================
# Application Creation, Draft Update, and Submission (Phase C)
# ==============================================================================

@router.post(
    "/applications",
    response_model=CitizenApplicationSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate Scheme Application from Citizen Portal",
    description="Initiates a new application under a supported scheme for the authenticated citizen in DRAFT state.",
    responses={
        201: {"description": "Application successfully initiated in DRAFT state."},
        401: {"model": ErrorResponse, "description": "Unauthenticated or invalid token."},
        404: {"model": ErrorResponse, "description": "Specified scheme not found or has no active policy."},
    },
)
async def create_citizen_application(
    payload: CitizenApplicationCreateRequest,
    current_citizen: Dict[str, Any] = Depends(get_current_citizen),
    db: AsyncSession = Depends(get_db),
) -> CitizenApplicationSummary:
    """Initiate a new scheme application in DRAFT state bound to the active policy version."""
    db_citizen = await _resolve_db_citizen(current_citizen, db)
    if not db_citizen:
        db_citizen = Citizen(
            synthetic_reference=current_citizen["citizen_ref"],
            display_name=current_citizen.get("name"),
            state=current_citizen.get("state"),
            district=current_citizen.get("district"),
        )
        db.add(db_citizen)
        await db.commit()
        await db.refresh(db_citizen)

    # Lookup scheme
    stmt = select(Scheme).where(Scheme.scheme_code == payload.scheme_code.strip().upper())
    res = await db.execute(stmt)
    scheme = res.scalar_one_or_none()
    if not scheme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scheme with code {payload.scheme_code!r} was not found.",
        )

    # Resolve active policy version
    try:
        policy_version = await get_policy_version(db, scheme.scheme_code, date.today())
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active statutory policy version available for scheme '{payload.scheme_code}': {str(exc)}",
        )

    initial_state = (
        JourneyState.FACTS_COLLECTED
        if payload.initial_facts
        else JourneyState.DRAFT
    )

    journey = EvaluationJourney(
        citizen_id=db_citizen.id,
        scheme_id=scheme.id,
        policy_version_id=policy_version.id,
        state=initial_state,
    )
    db.add(journey)
    await db.flush()

    # Initial transition
    t = JourneyTransitionRecord(
        journey_id=journey.id,
        from_state=JourneyState.DRAFT,
        to_state=initial_state,
        actor="CITIZEN",
        reason=f"Application initiated by citizen {db_citizen.synthetic_reference} bound to policy {policy_version.version_code}",
    )
    db.add(t)

    # Populate draft claims if initial facts provided
    if payload.initial_facts:
        try:
            form_meta = get_policy_form_metadata(scheme.scheme_code, policy_version.version_code)
            val_errors = validate_citizen_form_submission(payload.initial_facts, form_meta, is_submission=False)
            if val_errors:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid initial facts: {'; '.join(val_errors)}",
                )
        except SchemeFormNotSupportedError:
            pass

        for claim_type, val in payload.initial_facts.items():
            claim = Claim(
                citizen_id=db_citizen.id,
                journey_id=journey.id,
                claim_type=claim_type,
                value_json={"value": val} if not isinstance(val, dict) else val,
                source="CITIZEN_DECLARATION",
                status=ClaimStatus.CLAIMED,
            )
            db.add(claim)

    await db.commit()
    await db.refresh(journey)

    return journey_to_summary(journey, scheme=scheme, policy_version=policy_version)


@router.put(
    "/applications/{application_id}/draft",
    response_model=CitizenApplicationDetail,
    status_code=status.HTTP_200_OK,
    summary="Save Draft Application Progress",
    description="Saves updated draft facts and evidence items without submitting.",
    responses={
        200: {"description": "Draft updated successfully."},
        400: {"model": ErrorResponse, "description": "Application is not in DRAFT state."},
        401: {"model": ErrorResponse, "description": "Unauthenticated or invalid token."},
        404: {"model": ErrorResponse, "description": "Application not found or access denied."},
    },
)
async def update_draft_application(
    application_id: uuid.UUID,
    payload: CitizenApplicationDraftUpdateRequest,
    current_citizen: Dict[str, Any] = Depends(get_current_citizen),
    db: AsyncSession = Depends(get_db),
) -> CitizenApplicationDetail:
    """Save draft progress on an unsubmitted application."""
    db_citizen = await _resolve_db_citizen(current_citizen, db)
    if not db_citizen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found or does not belong to your account",
        )

    stmt = (
        select(EvaluationJourney)
        .where(
            EvaluationJourney.id == application_id,
            EvaluationJourney.citizen_id == db_citizen.id,
        )
        .options(
            selectinload(EvaluationJourney.scheme),
            selectinload(EvaluationJourney.policy_version),
            selectinload(EvaluationJourney.latest_evaluation).selectinload(EvaluationTrace.policy_version),
            selectinload(EvaluationJourney.claims).selectinload(Claim.evidence_items).selectinload(Evidence.verification_records),
            selectinload(EvaluationJourney.transitions),
        )
    )
    res = await db.execute(stmt)
    journey = res.scalar_one_or_none()
    if not journey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found or does not belong to your account",
        )

    if journey.state != JourneyState.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update draft: Application is in {journey.state.value} state, not DRAFT.",
        )

    # Update or add claims
    persisted_claims = list(journey.claims or [])
    if payload.facts:
        scheme_code = journey.scheme.scheme_code if journey.scheme else None
        pv_code = journey.policy_version.version_code if journey.policy_version else None
        if scheme_code and pv_code:
            try:
                form_meta = get_policy_form_metadata(scheme_code, pv_code)
                val_errors = validate_citizen_form_submission(payload.facts, form_meta, is_submission=False)
                if val_errors:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid draft facts: {'; '.join(val_errors)}",
                    )
            except SchemeFormNotSupportedError:
                pass

        existing_claims = {c.claim_type: c for c in (journey.claims or [])}
        for k, v in payload.facts.items():
            val_json = {"value": v} if not isinstance(v, dict) else v
            if k in existing_claims:
                existing_claims[k].value_json = val_json
                existing_claims[k].updated_at = datetime.now(timezone.utc)
            else:
                new_claim = Claim(
                    id=uuid.uuid4(),
                    citizen_id=db_citizen.id,
                    journey_id=journey.id,
                    claim_type=k,
                    value_json=val_json,
                    source="CITIZEN_DECLARATION",
                    status=ClaimStatus.CLAIMED,
                )
                db.add(new_claim)
                persisted_claims.append(new_claim)

    await db.flush()

    # Attach evidence items if provided
    if payload.evidence_items:
        anchor_claim_id = persisted_claims[0].id if persisted_claims else None
        if not anchor_claim_id:
            anchor_claim_id = uuid.uuid4()
            anchor_claim = Claim(
                id=anchor_claim_id,
                citizen_id=db_citizen.id,
                journey_id=journey.id,
                claim_type="application_document_evidence",
                value_json={"attached": True},
                source="CITIZEN_DECLARATION",
                status=ClaimStatus.CLAIMED,
            )
            db.add(anchor_claim)
            await db.flush()

        # Query existing evidence references to avoid lazy loading
        existing_ev_stmt = (
            select(Evidence.storage_reference)
            .join(Claim, Evidence.claim_id == Claim.id)
            .where(Claim.journey_id == journey.id)
        )
        existing_ev_res = await db.execute(existing_ev_stmt)
        existing_refs = set(existing_ev_res.scalars().all())

        for ev_sub in payload.evidence_items:
            if ev_sub.storage_reference not in existing_refs:
                target_claim_id = anchor_claim_id
                for c in persisted_claims:
                    if (ev_sub.evidence_type == "LAND_RECORD" and "land" in c.claim_type) or \
                       (ev_sub.evidence_type == "BIRTH_CERTIFICATE" and ("birth" in c.claim_type or "date_of_birth" in c.claim_type)) or \
                       (ev_sub.evidence_type == "AADHAAR" and ("citizen" in c.claim_type or "guardian" in c.claim_type)):
                        target_claim_id = c.id
                        break

                meta = ev_sub.metadata_json or {}
                if ev_sub.document_name:
                    meta["document_name"] = ev_sub.document_name
                ev = Evidence(
                    id=uuid.uuid4(),
                    claim_id=target_claim_id,
                    evidence_type=ev_sub.evidence_type,
                    storage_reference=ev_sub.storage_reference,
                    metadata_json=meta if meta else None,
                    status=EvidenceStatus.PENDING,
                )
                db.add(ev)
                existing_refs.add(ev_sub.storage_reference)

    journey.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(journey)

    return await get_citizen_application_detail(application_id, current_citizen=current_citizen, db=db)


@router.post(
    "/applications/{application_id}/submit",
    response_model=CitizenApplicationDetail,
    status_code=status.HTTP_200_OK,
    summary="Formally Submit Application",
    description="Submits the completed application with citizen declared facts and evidence references.",
    responses={
        200: {"description": "Application successfully submitted."},
        400: {"model": ErrorResponse, "description": "Validation error or invalid application state."},
        401: {"model": ErrorResponse, "description": "Unauthenticated or invalid token."},
        404: {"model": ErrorResponse, "description": "Application not found or access denied."},
    },
)
async def submit_citizen_application(
    application_id: uuid.UUID,
    payload: CitizenApplicationSubmitRequest,
    current_citizen: Dict[str, Any] = Depends(get_current_citizen),
    db: AsyncSession = Depends(get_db),
) -> CitizenApplicationDetail:
    """Formally commit declared facts and supporting evidence to submit an application."""
    db_citizen = await _resolve_db_citizen(current_citizen, db)
    if not db_citizen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found or does not belong to your account",
        )

    stmt = (
        select(EvaluationJourney)
        .where(
            EvaluationJourney.id == application_id,
            EvaluationJourney.citizen_id == db_citizen.id,
        )
        .options(
            selectinload(EvaluationJourney.scheme),
            selectinload(EvaluationJourney.policy_version),
            selectinload(EvaluationJourney.latest_evaluation).selectinload(EvaluationTrace.policy_version),
            selectinload(EvaluationJourney.claims).selectinload(Claim.evidence_items).selectinload(Evidence.verification_records),
            selectinload(EvaluationJourney.transitions),
        )
    )
    res = await db.execute(stmt)
    journey = res.scalar_one_or_none()
    if not journey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found or does not belong to your account",
        )

    if journey.state != JourneyState.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit application: Current state is {journey.state.value}, not DRAFT.",
        )

    if not payload.facts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot submit application without factual declarations.",
        )

    # Validate against bound policy version form metadata
    scheme_code = journey.scheme.scheme_code if journey.scheme else None
    pv_code = journey.policy_version.version_code if journey.policy_version else None
    if scheme_code and pv_code:
        try:
            form_meta = get_policy_form_metadata(scheme_code, pv_code)
            val_errors = validate_citizen_form_submission(
                payload.facts,
                form_meta,
                evidence_items=payload.evidence_items,
                is_submission=True,
            )
            if val_errors:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Statutory validation failed: {'; '.join(val_errors)}",
                )
        except SchemeFormNotSupportedError:
            pass

    # 1. Persist/update all citizen claims
    existing_claims = {c.claim_type: c for c in (journey.claims or [])}
    persisted_claims = []
    for k, v in payload.facts.items():
        val_json = {"value": v} if not isinstance(v, dict) else v
        if k in existing_claims:
            claim = existing_claims[k]
            claim.value_json = val_json
            claim.updated_at = datetime.now(timezone.utc)
            claim.status = ClaimStatus.CLAIMED
        else:
            claim = Claim(
                id=uuid.uuid4(),
                citizen_id=db_citizen.id,
                journey_id=journey.id,
                claim_type=k,
                value_json=val_json,
                source="CITIZEN_DECLARATION",
                status=ClaimStatus.CLAIMED,
            )
            db.add(claim)
        persisted_claims.append(claim)

    await db.flush()

    # 2. Attach submitted evidence items
    has_evidence = False
    if payload.evidence_items:
        anchor_claim = persisted_claims[0] if persisted_claims else None
        if not anchor_claim:
            anchor_claim = Claim(
                id=uuid.uuid4(),
                citizen_id=db_citizen.id,
                journey_id=journey.id,
                claim_type="application_document_evidence",
                value_json={"attached": True},
                source="CITIZEN_DECLARATION",
                status=ClaimStatus.CLAIMED,
            )
            db.add(anchor_claim)
            await db.flush()

        for ev_sub in payload.evidence_items:
            target_claim = anchor_claim
            for c in persisted_claims:
                if (ev_sub.evidence_type == "LAND_RECORD" and "land" in c.claim_type) or \
                   (ev_sub.evidence_type == "BIRTH_CERTIFICATE" and ("birth" in c.claim_type or "date_of_birth" in c.claim_type)) or \
                   (ev_sub.evidence_type == "AADHAAR" and ("citizen" in c.claim_type or "guardian" in c.claim_type)):
                    target_claim = c
                    break

            meta = ev_sub.metadata_json or {}
            if ev_sub.document_name:
                meta["document_name"] = ev_sub.document_name

            ev = Evidence(
                id=uuid.uuid4(),
                claim_id=target_claim.id,
                evidence_type=ev_sub.evidence_type,
                storage_reference=ev_sub.storage_reference,
                metadata_json=meta if meta else None,
                status=EvidenceStatus.PENDING,
            )
            db.add(ev)
            has_evidence = True

    # 3. Determine target submitted state
    target_state = JourneyState.EVIDENCE_PENDING if has_evidence else JourneyState.FACTS_COLLECTED

    # 4. Record transition audit records
    t1 = JourneyTransitionRecord(
        journey_id=journey.id,
        from_state=JourneyState.DRAFT,
        to_state=JourneyState.FACTS_COLLECTED,
        actor="CITIZEN",
        reason="Factual claims declared and submitted by citizen",
    )
    db.add(t1)

    if target_state == JourneyState.EVIDENCE_PENDING:
        t2 = JourneyTransitionRecord(
            journey_id=journey.id,
            from_state=JourneyState.FACTS_COLLECTED,
            to_state=JourneyState.EVIDENCE_PENDING,
            actor="CITIZEN",
            reason="Corroborating documentary evidence attached; awaiting welfare officer verification",
        )
        db.add(t2)

    # 5. Update Journey state, timestamps, submitted_at
    journey.state = target_state
    now = datetime.now(timezone.utc)
    journey.submitted_at = now
    journey.updated_at = now

    await db.commit()
    await db.refresh(journey)

    return await get_citizen_application_detail(application_id, current_citizen=current_citizen, db=db)


# ==============================================================================
# Evidence Clarification Workflow Endpoints (Phase E)
# ==============================================================================

@router.get(
    "/applications/{application_id}/clarifications",
    response_model=CitizenClarificationListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Application Clarification Requests",
    description="Retrieve sanitized, citizen-safe clarification requests for an application.",
    responses={
        200: {"description": "Clarifications retrieved successfully."},
        401: {"model": ErrorResponse, "description": "Unauthenticated or invalid token."},
        404: {"model": ErrorResponse, "description": "Application not found or access denied."},
    },
)
async def list_citizen_application_clarifications(
    application_id: uuid.UUID,
    current_citizen: Dict[str, Any] = Depends(get_current_citizen),
    db: AsyncSession = Depends(get_db),
) -> CitizenClarificationListResponse:
    db_citizen = await _resolve_db_citizen(current_citizen, db)
    if not db_citizen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found or does not belong to your account",
        )
    return await get_citizen_clarifications(
        session=db,
        journey_id=application_id,
        citizen_db_id=db_citizen.id,
    )


@router.post(
    "/applications/{application_id}/clarifications/{clarification_id}/respond",
    response_model=CitizenClarificationItemResponse,
    status_code=status.HTTP_200_OK,
    summary="Respond to Clarification Request",
    description="Submit citizen factual clarification statement and optional replacement documentary evidence.",
    responses={
        200: {"description": "Clarification response recorded successfully."},
        400: {"model": ErrorResponse, "description": "Clarification is not open for response."},
        401: {"model": ErrorResponse, "description": "Unauthenticated or invalid token."},
        404: {"model": ErrorResponse, "description": "Clarification or application not found or access denied."},
    },
)
async def respond_citizen_clarification(
    application_id: uuid.UUID,
    clarification_id: uuid.UUID,
    payload: CitizenClarificationRespondRequest,
    current_citizen: Dict[str, Any] = Depends(get_current_citizen),
    db: AsyncSession = Depends(get_db),
) -> CitizenClarificationItemResponse:
    db_citizen = await _resolve_db_citizen(current_citizen, db)
    if not db_citizen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found or does not belong to your account",
        )

    citizen_ref = db_citizen.synthetic_reference
    updated_cr = await respond_to_clarification(
        session=db,
        journey_id=application_id,
        clarification_id=clarification_id,
        citizen_db_id=db_citizen.id,
        response_text=payload.response_text,
        replacement_evidence=payload.replacement_evidence,
        citizen_identity=citizen_ref,
    )

    repl_name = None
    if payload.replacement_evidence:
        repl_name = payload.replacement_evidence.document_name

    return CitizenClarificationItemResponse(
        id=updated_cr.id,
        round=updated_cr.round,
        evidence_id=updated_cr.evidence_id,
        claim_id=updated_cr.claim_id,
        request_reason=updated_cr.request_reason,
        status=updated_cr.status.value,
        requested_at=updated_cr.requested_at,
        response_text=updated_cr.response_text,
        responded_at=updated_cr.responded_at,
        has_replacement_evidence=bool(updated_cr.replacement_evidence_id),
        replacement_evidence_id=updated_cr.replacement_evidence_id,
        replacement_evidence_name=repl_name,
        resolved_at=updated_cr.resolved_at,
    )


@router.get(
    "/applications/{application_id}/verification-status",
    response_model=CitizenVerificationStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Application Verification Status",
    description="Retrieve backend-authoritative verification readiness metrics for an application.",
    responses={
        200: {"description": "Verification status returned successfully."},
        401: {"model": ErrorResponse, "description": "Unauthenticated or invalid token."},
        404: {"model": ErrorResponse, "description": "Application not found or access denied."},
    },
)
async def get_citizen_application_verification_status(
    application_id: uuid.UUID,
    current_citizen: Dict[str, Any] = Depends(get_current_citizen),
    db: AsyncSession = Depends(get_db),
) -> CitizenVerificationStatusResponse:
    db_citizen = await _resolve_db_citizen(current_citizen, db)
    if not db_citizen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found or does not belong to your account",
        )

    # Check ownership
    j_stmt = select(EvaluationJourney).where(
        EvaluationJourney.id == application_id,
        EvaluationJourney.citizen_id == db_citizen.id,
    )
    j = (await db.execute(j_stmt)).scalars().first()
    if not j:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found or does not belong to your account",
        )

    metrics = await compute_verification_status(db, application_id)
    return CitizenVerificationStatusResponse(
        application_id=application_id,
        application_ref=build_application_ref(application_id, j.created_at),
        scheme_code=metrics["scheme_code"],
        scheme_name=metrics["scheme_name"],
        verification_status=metrics["verification_status"],
        total_evidence_count=metrics["total_evidence_count"],
        verified_evidence_count=metrics["verified_evidence_count"],
        pending_evidence_count=metrics["pending_evidence_count"],
        clarification_required_count=metrics["clarification_required_count"],
        rejected_evidence_count=metrics["rejected_evidence_count"],
        open_clarification_count=metrics["open_clarification_count"],
    )


@router.get(
    "/applications/{application_id}/decision",
    response_model=CitizenDecisionResponse,
    status_code=status.HTTP_200_OK,
    summary="Application Statutory Decision",
    description="Retrieve the citizen-facing statutory eligibility decision and plain-language explanation.",
    responses={
        200: {"description": "Decision returned successfully."},
        401: {"model": ErrorResponse, "description": "Unauthenticated or invalid token."},
        404: {"model": ErrorResponse, "description": "Application not found or access denied."},
    },
)
async def get_citizen_application_decision(
    application_id: uuid.UUID,
    current_citizen: Dict[str, Any] = Depends(get_current_citizen),
    db: AsyncSession = Depends(get_db),
) -> CitizenDecisionResponse:
    db_citizen = await _resolve_db_citizen(current_citizen, db)
    if not db_citizen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found or does not belong to your account",
        )

    eval_service = EvaluationService(db)
    return await eval_service.get_citizen_decision(
        journey_id=application_id,
        citizen_id=db_citizen.id,
    )
