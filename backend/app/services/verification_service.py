"""Operational Evidence Verification & Clarification Service (Phase E).

Implements the authoritative backend service for:
- Evidence and fact verification findings
- Clarification requests and citizen response handling
- Replacement / supplementary evidence attachment
- Verification rounds and multi-round history preservation
- Backend-authoritative verification completeness calculation
- Append-only audit logging via HumanReviewAuditEvent
- Strict IDOR and role-based authorization boundaries
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assignment import OfficerAssignment
from app.models.citizen import Citizen, Claim, Evidence, VerificationRecord
from app.models.clarification import ClarificationRequest
from app.models.enums import (
    ClaimStatus,
    ClarificationStatus,
    EvidenceStatus,
    HumanReviewStatus,
    JourneyState,
    VerificationCompleteness,
    VerificationStatus,
)
from app.models.human_review import HumanReview, HumanReviewAuditEvent
from app.models.journey import EvaluationJourney, JourneyTransitionRecord
from app.models.scheme import PolicyVersion, Scheme
from app.schemas.clarification import (
    CitizenClarificationItemResponse,
    CitizenClarificationListResponse,
    CitizenReplacementEvidenceInput,
    CitizenVerificationStatusResponse,
    OfficerClarificationItemResponse,
    OfficerVerificationHistoryResponse,
    OfficerVerificationRecordResponse,
)
from app.schemas.officer import OfficerAuditEventResponse, OfficerEvidenceResponse
from app.services.assignment_service import get_active_assignment_for_journey
from app.services.citizen_scheme_requirements import get_scheme_requirements


# ------------------------------------------------------------------------------
# Canonical Evidence Mapping & Type Aliases
# ------------------------------------------------------------------------------

EVIDENCE_CANONICAL_TYPE_MAP: Dict[str, str] = {
    # Identity & Demographic
    "AADHAAR": "AADHAAR",
    "AADHAAR_CARD": "AADHAAR",
    "BIRTH_CERTIFICATE": "BIRTH_CERTIFICATE",
    "AGE_PROOF": "AGE_PROOF",

    # Banking & Financial
    "BANK_PASSBOOK": "BANK_PASSBOOK",
    "BANK_STATEMENT": "BANK_PASSBOOK",
    "PASSBOOK": "BANK_PASSBOOK",
    "TAX_RETURN": "TAX_RETURN",
    "PENSION_SLIP": "PENSION_SLIP",
    "INCOME_CERTIFICATE": "INCOME_CERTIFICATE",

    # Land & Property
    "LAND_RECORD": "LAND_RECORD",
    "LAND_REVENUE_RECORD": "LAND_RECORD",
    "KHASRA_KHATAUNI": "LAND_RECORD",
    "PROPERTY_DOCUMENT_OR_AFFIDAVIT": "PROPERTY_DOCUMENT_OR_AFFIDAVIT",
    "LAND_TITLE_DEED": "PROPERTY_DOCUMENT_OR_AFFIDAVIT",
    "NON_OWNERSHIP_AFFIDAVIT": "PROPERTY_DOCUMENT_OR_AFFIDAVIT",

    # Social & Deprivation
    "RATION_CARD": "RATION_CARD",
    "BPL_RATION_CARD": "RATION_CARD",
    "NFSA_RATION_CARD": "RATION_CARD",
    "BPL_CARD_OR_CERTIFICATE": "BPL_CARD_OR_CERTIFICATE",
    "DEPRIVATION_CERTIFICATE": "DEPRIVATION_CERTIFICATE",
    "SECC_DOCUMENT": "DEPRIVATION_CERTIFICATE",
    "ELIGIBILITY_PROOF_DOCUMENT": "ELIGIBILITY_PROOF_DOCUMENT",
    "JOB_CARD": "JOB_CARD",
    "MGNREGA_JOB_CARD": "JOB_CARD",

    # Trade & Livelihood
    "ARTISAN_ID_OR_DECLARATION": "ARTISAN_ID_OR_DECLARATION",
    "ARTISAN_ID": "ARTISAN_ID_OR_DECLARATION",
    "VENDING_PROOF_OR_LOR": "VENDING_PROOF_OR_LOR",
    "VENDING_CERTIFICATE": "VENDING_PROOF_OR_LOR",
    "LETTER_OF_RECOMMENDATION": "VENDING_PROOF_OR_LOR",

    # Housing & Maternal Health
    "HOUSING_VERIFICATION_CERTIFICATE": "HOUSING_VERIFICATION_CERTIFICATE",
    "KUTCHA_HOUSE_CERTIFICATE": "HOUSING_VERIFICATION_CERTIFICATE",
    "MCP_CARD": "MCP_CARD",
    "MOTHER_CHILD_PROTECTION_CARD": "MCP_CARD",
}


def canonicalize_evidence_type(ev_type: Optional[str]) -> Optional[str]:
    """Map raw evidence type string to canonical type code."""
    if not ev_type:
        return None
    norm = ev_type.strip().upper()
    return EVIDENCE_CANONICAL_TYPE_MAP.get(norm, norm)


# ------------------------------------------------------------------------------
# Officer Object-Level Case Assignment Authorization
# ------------------------------------------------------------------------------

async def verify_officer_case_access(
    session: AsyncSession,
    journey_id: uuid.UUID,
    current_officer: Dict[str, Any],
) -> None:
    """Enforce Phase D & E object-level authorization on case operations.

    Invariants:
    - If role in ("SUPERVISOR", "ADMIN"): permitted under elevated authority.
    - If role == "OFFICER": actor identity must match the active case assignee.
    - Otherwise (e.g. CITIZEN, non-assignee officer, unassigned case): HTTP 403 Forbidden.
    """
    role = (current_officer.get("role") or "").strip().upper()
    actor_identity = (current_officer.get("email") or current_officer.get("sub") or "").strip().lower()

    if role in ("SUPERVISOR", "ADMIN"):
        return

    if role == "OFFICER":
        active_assignment = await get_active_assignment_for_journey(session, journey_id)
        if not active_assignment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: Case is not assigned to you. Only the assigned officer or an administrative supervisor can perform this action.",
            )
        current_assignee = (active_assignment.officer_identity or "").strip().lower()
        if actor_identity != current_assignee:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: Case is assigned to another officer. Only the assigned officer or an administrative supervisor can perform this action.",
            )
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access forbidden: Insufficient privileges.",
    )


# ------------------------------------------------------------------------------
# Helper: Retrieve or Initialize HumanReview
# ------------------------------------------------------------------------------

async def get_or_create_human_review(
    session: AsyncSession, journey_id: uuid.UUID, officer_identity: Optional[str] = None
) -> HumanReview:
    """Retrieve existing HumanReview entity for a journey, or initialize PENDING record."""
    stmt = select(HumanReview).where(HumanReview.journey_id == journey_id)
    res = await session.execute(stmt)
    review = res.scalars().first()
    if not review:
        review = HumanReview(
            journey_id=journey_id,
            reviewer_identity=officer_identity or "SYSTEM",
            reviewer_role="OFFICER",
            status=HumanReviewStatus.PENDING,
        )
        session.add(review)
        await session.flush()
    return review


# ------------------------------------------------------------------------------
# Verification Completeness & Readiness Calculation (Finding 1)
# ------------------------------------------------------------------------------

async def compute_verification_status(
    session: AsyncSession, journey_id: uuid.UUID
) -> Dict[str, Any]:
    """Compute backend-authoritative verification readiness metrics for an evaluation journey.

    Strict Invariants:
    - Verification completeness is derived from the application's policy-bound mandatory requirements.
    - Uses the application's already-bound policy_version_id; does not query latest active policy.
    - Missing mandatory evidence prevents READY_FOR_EVALUATION / VERIFICATION_COMPLETE.
    - Pending mandatory evidence prevents READY_FOR_EVALUATION.
    - Rejected mandatory evidence blocks evaluation (VERIFICATION_BLOCKED).
    - Clarification-required mandatory evidence requires clarification (CLARIFICATION_REQUIRED).
    - Optional evidence cannot satisfy an unrelated mandatory requirement.
    - Unknown/unmapped evidence categories cannot satisfy mandatory requirements.
    - All mandatory requirements must be satisfied with VERIFIED evidence.
    """
    stmt = (
        select(EvaluationJourney)
        .options(
            selectinload(EvaluationJourney.scheme),
            selectinload(EvaluationJourney.claims).selectinload(Claim.evidence_items),
            selectinload(EvaluationJourney.clarification_requests),
        )
        .where(EvaluationJourney.id == journey_id)
    )
    res = await session.execute(stmt)
    journey = res.scalars().first()
    if not journey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation journey '{journey_id}' was not found",
        )

    all_evidence: List[Evidence] = []
    for c in journey.claims:
        all_evidence.extend(c.evidence_items)

    total_evidence = len(all_evidence)
    verified_evidence = sum(1 for e in all_evidence if e.status == EvidenceStatus.VERIFIED)
    rejected_evidence = sum(1 for e in all_evidence if e.status == EvidenceStatus.REJECTED)
    clarification_required_evidence = sum(
        1 for e in all_evidence if e.status == EvidenceStatus.CLARIFICATION_REQUIRED
    )
    pending_evidence = sum(1 for e in all_evidence if e.status == EvidenceStatus.PENDING)

    open_clarifications = sum(
        1 for c in journey.clarification_requests if c.status in (ClarificationStatus.OPEN, ClarificationStatus.RESPONDED)
    )

    # 1. Resolve mandatory evidence requirements for the journey's bound policy context
    mandatory_reqs: List[str] = []
    if journey.scheme:
        try:
            reqs = await get_scheme_requirements(
                session=session,
                scheme_code=journey.scheme.scheme_code,
                policy_version_id=journey.policy_version_id,
                evaluation_date=journey.submitted_at.date() if journey.submitted_at else (journey.created_at.date() if journey.created_at else None),
            )
            mandatory_reqs = [r.evidence_type for r in reqs.evidence_types if r.mandatory]
        except Exception:
            mandatory_reqs = []

    # 2. Map attached evidence to canonical types
    attached_by_canonical: Dict[str, List[Evidence]] = {}
    for ev in all_evidence:
        canon = canonicalize_evidence_type(ev.evidence_type)
        if canon:
            attached_by_canonical.setdefault(canon, []).append(ev)

    # 3. Categorize mandatory requirements satisfaction
    missing_mandatory: List[str] = []
    pending_mandatory: List[str] = []
    rejected_mandatory: List[str] = []
    clarification_mandatory: List[str] = []
    verified_mandatory: List[str] = []

    for req in mandatory_reqs:
        canon_req = canonicalize_evidence_type(req) or req.upper()
        matching_items = attached_by_canonical.get(canon_req, [])
        if not matching_items:
            missing_mandatory.append(req)
        else:
            if any(e.status == EvidenceStatus.REJECTED for e in matching_items):
                rejected_mandatory.append(req)
            elif any(e.status == EvidenceStatus.CLARIFICATION_REQUIRED for e in matching_items):
                clarification_mandatory.append(req)
            elif any(e.status == EvidenceStatus.PENDING for e in matching_items):
                pending_mandatory.append(req)
            elif all(e.status == EvidenceStatus.VERIFIED for e in matching_items):
                verified_mandatory.append(req)
            else:
                pending_mandatory.append(req)

    # 4. Derive overall verification readiness
    has_clarification = (
        open_clarifications > 0
        or clarification_required_evidence > 0
        or len(clarification_mandatory) > 0
    )
    has_rejected = (
        rejected_evidence > 0
        or len(rejected_mandatory) > 0
    )
    has_missing = len(missing_mandatory) > 0
    has_pending = (
        pending_evidence > 0
        or len(pending_mandatory) > 0
    )

    all_mandatory_satisfied = (
        len(mandatory_reqs) > 0
        and len(verified_mandatory) == len(mandatory_reqs)
    )
    all_attached_verified = (
        total_evidence > 0
        and verified_evidence == total_evidence
    )

    if has_clarification:
        readiness = VerificationCompleteness.CLARIFICATION_REQUIRED
    elif has_rejected:
        readiness = VerificationCompleteness.VERIFICATION_BLOCKED
    elif has_missing or has_pending:
        readiness = VerificationCompleteness.VERIFICATION_IN_PROGRESS
    elif all_mandatory_satisfied and all_attached_verified:
        readiness = VerificationCompleteness.VERIFICATION_COMPLETE
    elif len(mandatory_reqs) == 0 and all_attached_verified:
        # Fallback for schemes with no mandatory evidence requirements
        readiness = VerificationCompleteness.VERIFICATION_COMPLETE
    else:
        readiness = VerificationCompleteness.VERIFICATION_IN_PROGRESS

    return {
        "journey_id": journey.id,
        "scheme_code": journey.scheme.scheme_code if journey.scheme else "UNKNOWN",
        "scheme_name": journey.scheme.name_en if journey.scheme else "Welfare Scheme",
        "verification_status": readiness.value,
        "total_evidence_count": total_evidence,
        "verified_evidence_count": verified_evidence,
        "pending_evidence_count": pending_evidence,
        "clarification_required_count": clarification_required_evidence,
        "rejected_evidence_count": rejected_evidence,
        "open_clarification_count": open_clarifications,
        "bound_policy_version_id": str(journey.policy_version_id) if journey.policy_version_id else None,
        "mandatory_requirements": mandatory_reqs,
        "satisfied_mandatory_requirements": verified_mandatory,
        "missing_mandatory_requirements": missing_mandatory,
        "pending_mandatory_requirements": pending_mandatory,
        "rejected_mandatory_requirements": rejected_mandatory,
        "clarification_mandatory_requirements": clarification_mandatory,
        "is_ready_for_evaluation": (readiness == VerificationCompleteness.VERIFICATION_COMPLETE),
    }


# ------------------------------------------------------------------------------
# Clarification Request Workflow (Officer Action)
# ------------------------------------------------------------------------------

async def request_clarification(
    session: AsyncSession,
    journey_id: uuid.UUID,
    evidence_id: uuid.UUID,
    reason: str,
    notes: Optional[str],
    current_officer: Dict[str, Any],
) -> ClarificationRequest:
    """Officer initiates a formal clarification request on a submitted evidence item.

    Strict Invariants:
    - Verifies evidence belongs to the specified journey.
    - Determines monotonic verification round for this journey.
    - Transitions Evidence.status to CLARIFICATION_REQUIRED.
    - Appends an audit-preserving VerificationRecord.
    - Appends an immutable HumanReviewAuditEvent.
    - Transitions JourneyState to ACTION_REQUIRED.
    - Transitions HumanReviewStatus to CLARIFICATION_REQUIRED.
    """
    officer_email = current_officer.get("email") or current_officer.get("sub")
    officer_role = current_officer.get("role", "OFFICER")

    clean_reason = reason.strip()
    if not clean_reason:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A substantive reason is required when requesting clarification.",
        )

    # 0. Enforce object-level case assignment authorization
    await verify_officer_case_access(session, journey_id, current_officer)

    # 1. Fetch Journey and Evidence with Claim linkage
    stmt = (
        select(Evidence)
        .join(Claim, Evidence.claim_id == Claim.id)
        .options(selectinload(Evidence.claim))
        .where(Evidence.id == evidence_id, Claim.journey_id == journey_id)
    )
    res = await session.execute(stmt)
    evidence = res.scalars().first()
    if not evidence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence item '{evidence_id}' for case '{journey_id}' was not found",
        )

    # 2. Determine next verification round
    round_stmt = select(func.coalesce(func.max(ClarificationRequest.round), 0)).where(
        ClarificationRequest.journey_id == journey_id
    )
    current_max_round = (await session.execute(round_stmt)).scalar() or 0
    next_round = current_max_round + 1

    # 3. Create ClarificationRequest
    now = datetime.now(timezone.utc)
    clarification = ClarificationRequest(
        id=uuid.uuid4(),
        journey_id=journey_id,
        claim_id=evidence.claim_id,
        evidence_id=evidence.id,
        round=next_round,
        requesting_officer=officer_email,
        requesting_officer_role=officer_role,
        request_reason=clean_reason,
        notes=notes.strip() if notes else None,
        status=ClarificationStatus.OPEN,
        requested_at=now,
    )
    session.add(clarification)
    await session.flush()

    # 4. Update Evidence status
    prev_status = evidence.status.value
    evidence.status = EvidenceStatus.CLARIFICATION_REQUIRED
    evidence.rejection_reason = f"Clarification requested (Round {next_round}): {clean_reason}"

    # 5. Append VerificationRecord
    v_record = VerificationRecord(
        evidence_id=evidence.id,
        claim_id=evidence.claim_id,
        verification_method="OFFICER_CLARIFICATION_REQUEST",
        status=VerificationStatus.MANUAL_REVIEW_REQUIRED,
        verified_by=officer_email,
        verified_at=now,
        round=next_round,
        clarification_request_id=clarification.id,
        details_json={
            "action": "REQUEST_CLARIFICATION",
            "round": next_round,
            "reason": clean_reason,
            "notes": notes,
            "officer_role": officer_role,
        },
    )
    session.add(v_record)

    # 6. Update HumanReview entity
    review = await get_or_create_human_review(session, journey_id, officer_email)
    prev_review_status = review.status.value
    review.status = HumanReviewStatus.CLARIFICATION_REQUIRED
    review.reviewer_identity = officer_email
    review.reviewer_role = officer_role
    review.reason = clean_reason
    review.notes = notes

    # 7. Update Journey State to ACTION_REQUIRED
    j_stmt = select(EvaluationJourney).where(EvaluationJourney.id == journey_id)
    journey = (await session.execute(j_stmt)).scalars().first()
    if journey and journey.state != JourneyState.ACTION_REQUIRED:
        prev_journey_state = journey.state
        journey.state = JourneyState.ACTION_REQUIRED
        journey.updated_at = now

        t_record = JourneyTransitionRecord(
            journey_id=journey.id,
            from_state=prev_journey_state,
            to_state=JourneyState.ACTION_REQUIRED,
            actor="OFFICER",
            reason=f"Clarification required on {evidence.evidence_type} (Round {next_round}): {clean_reason}",
        )
        session.add(t_record)

    # 8. Append HumanReviewAuditEvent
    audit_event = HumanReviewAuditEvent(
        review_id=review.id,
        journey_id=journey_id,
        actor_identity=officer_email,
        actor_role=officer_role,
        action="CLARIFICATION_REQUESTED",
        previous_status=prev_status,
        new_status=evidence.status.value,
        reason=clean_reason,
        details_json={
            "evidence_id": str(evidence.id),
            "evidence_type": evidence.evidence_type,
            "round": next_round,
            "clarification_id": str(clarification.id),
            "notes": notes,
        },
    )
    session.add(audit_event)

    await session.commit()
    await session.refresh(clarification)
    return clarification


# ------------------------------------------------------------------------------
# Clarification Response Workflow (Citizen Action)
# ------------------------------------------------------------------------------

async def respond_to_clarification(
    session: AsyncSession,
    journey_id: uuid.UUID,
    clarification_id: uuid.UUID,
    citizen_db_id: uuid.UUID,
    response_text: str,
    replacement_evidence: Optional[CitizenReplacementEvidenceInput],
    citizen_identity: str,
) -> ClarificationRequest:
    """Citizen responds to an open clarification request with text and optional replacement evidence.

    Strict Invariants:
    - IDOR Protection: Verifies journey belongs to the authenticated citizen.
    - Clarification must belong to this journey and must be in OPEN status.
    - Attaches replacement/supplementary evidence if provided.
    - Transitions ClarificationRequest to RESPONDED.
    - Transitions HumanReview to IN_REVIEW.
    - Transitions JourneyState from ACTION_REQUIRED back to VERIFICATION_IN_PROGRESS.
    - Appends HumanReviewAuditEvent with actor_role='CITIZEN'.
    """
    clean_text = response_text.strip()
    if not clean_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A clarification response statement is required.",
        )

    # 1. Fetch Journey with IDOR verification
    j_stmt = (
        select(EvaluationJourney)
        .options(selectinload(EvaluationJourney.claims))
        .where(EvaluationJourney.id == journey_id, EvaluationJourney.citizen_id == citizen_db_id)
    )
    journey = (await session.execute(j_stmt)).scalars().first()
    if not journey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application dossier not found or does not belong to your account",
        )

    # 2. Fetch ClarificationRequest
    c_stmt = (
        select(ClarificationRequest)
        .options(selectinload(ClarificationRequest.evidence))
        .where(
            ClarificationRequest.id == clarification_id,
            ClarificationRequest.journey_id == journey.id,
        )
    )
    clarification = (await session.execute(c_stmt)).scalars().first()
    if not clarification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clarification request '{clarification_id}' was not found for this application",
        )

    if clarification.status != ClarificationStatus.OPEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Clarification request is already '{clarification.status.value}' and cannot accept further responses.",
        )

    now = datetime.now(timezone.utc)

    # 3. Handle optional replacement or supporting evidence upload
    new_evidence_id: Optional[uuid.UUID] = None
    if replacement_evidence:
        target_claim_id = clarification.claim_id
        if not target_claim_id and clarification.evidence:
            target_claim_id = clarification.evidence.claim_id
        if not target_claim_id and journey.claims:
            target_claim_id = journey.claims[0].id

        ev_type = replacement_evidence.evidence_type
        if not ev_type and clarification.evidence:
            ev_type = clarification.evidence.evidence_type
        if not ev_type:
            ev_type = "REPLACEMENT_DOCUMENT"

        meta = replacement_evidence.metadata_json or {}
        meta["document_name"] = replacement_evidence.document_name
        if replacement_evidence.file_size_bytes:
            meta["file_size_bytes"] = replacement_evidence.file_size_bytes
        if replacement_evidence.mime_type:
            meta["mime_type"] = replacement_evidence.mime_type
        meta["clarification_round"] = clarification.round
        meta["submitted_as_replacement_for"] = str(clarification.evidence_id) if clarification.evidence_id else None

        new_ev = Evidence(
            id=uuid.uuid4(),
            claim_id=target_claim_id,
            evidence_type=ev_type,
            storage_reference=replacement_evidence.storage_reference,
            metadata_json=meta,
            status=EvidenceStatus.PENDING,
            submitted_at=now,
        )
        session.add(new_ev)
        await session.flush()
        new_evidence_id = new_ev.id

    # 4. Update ClarificationRequest
    clarification.response_text = clean_text
    clarification.responded_at = now
    clarification.status = ClarificationStatus.RESPONDED
    if new_evidence_id:
        clarification.replacement_evidence_id = new_evidence_id

    # 5. Transition HumanReview to IN_REVIEW
    review = await get_or_create_human_review(session, journey.id)
    prev_review_status = review.status.value
    review.status = HumanReviewStatus.IN_REVIEW

    # 6. Transition Journey State back to VERIFICATION_IN_PROGRESS
    prev_journey_state = journey.state
    journey.state = JourneyState.VERIFICATION_IN_PROGRESS
    journey.updated_at = now

    t_record = JourneyTransitionRecord(
        journey_id=journey.id,
        from_state=prev_journey_state,
        to_state=JourneyState.VERIFICATION_IN_PROGRESS,
        actor="CITIZEN",
        reason=f"Citizen responded to clarification request (Round {clarification.round})",
    )
    session.add(t_record)

    # 7. Append immutable HumanReviewAuditEvent
    audit_event = HumanReviewAuditEvent(
        review_id=review.id,
        journey_id=journey.id,
        actor_identity=citizen_identity,
        actor_role="CITIZEN",
        action="CLARIFICATION_RESPONDED",
        previous_status=prev_review_status,
        new_status=review.status.value,
        reason="Citizen submitted requested clarification statement",
        details_json={
            "clarification_id": str(clarification.id),
            "round": clarification.round,
            "has_replacement_evidence": bool(new_evidence_id),
            "replacement_evidence_id": str(new_evidence_id) if new_evidence_id else None,
        },
    )
    session.add(audit_event)

    await session.commit()
    stmt_reload = (
        select(ClarificationRequest)
        .options(selectinload(ClarificationRequest.replacement_evidence))
        .where(ClarificationRequest.id == clarification.id)
    )
    return (await session.execute(stmt_reload)).scalar_one()


# ------------------------------------------------------------------------------
# Evidence Verification & Resolution Workflow (Officer Action)
# ------------------------------------------------------------------------------

async def verify_evidence(
    session: AsyncSession,
    journey_id: uuid.UUID,
    evidence_id: uuid.UUID,
    action: str,
    reason: Optional[str],
    notes: Optional[str],
    current_officer: Dict[str, Any],
) -> OfficerEvidenceResponse:
    """Record an authoritative officer finding on an individual evidence item (VERIFY or REJECT).

    Strict Invariants:
    - Never mutates citizen's declared fact Claim.value_json.
    - Updates Claim.status in tandem (Fact Verification).
    - If linked to an open or responded ClarificationRequest, resolves it.
    - Appends a VerificationRecord with round tracking.
    - Appends an immutable HumanReviewAuditEvent.
    - Checks verification completeness: if all required items are verified,
      transitions journey to READY_FOR_EVALUATION.
    """
    valid_actions = ("VERIFY", "REJECT")
    action_upper = action.upper().strip()
    if action_upper not in valid_actions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action '{action}'. For clarification use the clarification endpoint.",
        )

    if action_upper == "REJECT" and (not reason or not reason.strip()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A mandatory justification reason is required when rejecting evidence.",
        )

    officer_email = current_officer.get("email") or current_officer.get("sub")
    officer_role = current_officer.get("role", "OFFICER")

    # 0. Enforce object-level case assignment authorization
    await verify_officer_case_access(session, journey_id, current_officer)

    # 1. Fetch Evidence with Claim
    stmt = (
        select(Evidence)
        .join(Claim, Evidence.claim_id == Claim.id)
        .options(
            selectinload(Evidence.claim),
            selectinload(Evidence.verification_records),
        )
        .where(Evidence.id == evidence_id, Claim.journey_id == journey_id)
    )
    res = await session.execute(stmt)
    evidence = res.scalars().first()
    if not evidence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence item '{evidence_id}' for case '{journey_id}' was not found",
        )

    # 2. Determine verification round
    round_stmt = select(func.coalesce(func.max(ClarificationRequest.round), 0)).where(
        ClarificationRequest.journey_id == journey_id
    )
    current_round = (await session.execute(round_stmt)).scalar() or 1

    now = datetime.now(timezone.utc)
    prev_status = evidence.status.value

    # 3. Resolve any pending/responded clarification request for this evidence
    c_stmt = (
        select(ClarificationRequest)
        .where(
            ClarificationRequest.journey_id == journey_id,
            ClarificationRequest.evidence_id == evidence.id,
            ClarificationRequest.status.in_([ClarificationStatus.OPEN, ClarificationStatus.RESPONDED]),
        )
        .order_by(desc(ClarificationRequest.created_at))
    )
    active_clarification = (await session.execute(c_stmt)).scalars().first()
    if active_clarification:
        active_clarification.status = ClarificationStatus.RESOLVED
        active_clarification.resolved_at = now
        active_clarification.resolved_by = officer_email
        active_clarification.resolution_notes = (
            f"Evidence verified by officer in Round {current_round}"
            if action_upper == "VERIFY"
            else f"Evidence rejected by officer in Round {current_round}: {reason}"
        )

    # 4. Update Evidence & Fact Claim Status
    if action_upper == "VERIFY":
        evidence.status = EvidenceStatus.VERIFIED
        evidence.verified_at = now
        evidence.rejected_at = None
        evidence.rejection_reason = None
        v_status = VerificationStatus.VERIFIED
        if evidence.claim:
            evidence.claim.status = ClaimStatus.VERIFIED
            evidence.claim.updated_at = now
    else:  # REJECT
        evidence.status = EvidenceStatus.REJECTED
        evidence.rejected_at = now
        evidence.rejection_reason = reason.strip() if reason else "Rejected by officer"
        v_status = VerificationStatus.REJECTED
        if evidence.claim:
            evidence.claim.status = ClaimStatus.REJECTED
            evidence.claim.updated_at = now

    # 5. Append VerificationRecord
    v_record = VerificationRecord(
        evidence_id=evidence.id,
        claim_id=evidence.claim_id,
        verification_method="OFFICER_MANUAL_REVIEW",
        status=v_status,
        verified_by=officer_email,
        verified_at=now,
        round=current_round,
        clarification_request_id=active_clarification.id if active_clarification else None,
        details_json={
            "action": action_upper,
            "round": current_round,
            "reason": reason,
            "notes": notes,
            "officer_role": officer_role,
        },
    )
    session.add(v_record)

    # 6. Update HumanReview
    review = await get_or_create_human_review(session, journey_id, officer_email)
    review.reviewer_identity = officer_email
    review.reviewer_role = officer_role

    # 7. Append HumanReviewAuditEvent
    audit_event = HumanReviewAuditEvent(
        review_id=review.id,
        journey_id=journey_id,
        actor_identity=officer_email,
        actor_role=officer_role,
        action="EVIDENCE_VERIFIED" if action_upper == "VERIFY" else "EVIDENCE_REJECTED",
        previous_status=prev_status,
        new_status=evidence.status.value,
        reason=reason,
        details_json={
            "evidence_id": str(evidence.id),
            "evidence_type": evidence.evidence_type,
            "round": current_round,
            "notes": notes,
        },
    )
    session.add(audit_event)

    # Backward compatibility: also append EVIDENCE_VERIFY event if VERIFY
    if action_upper == "VERIFY":
        audit_event_compat = HumanReviewAuditEvent(
            review_id=review.id,
            journey_id=journey_id,
            actor_identity=officer_email,
            actor_role=officer_role,
            action="EVIDENCE_VERIFY",
            previous_status=prev_status,
            new_status=evidence.status.value,
            reason=reason,
            details_json={
                "evidence_id": str(evidence.id),
                "evidence_type": evidence.evidence_type,
                "round": current_round,
                "notes": notes,
            },
        )
        session.add(audit_event_compat)

    # 8. Check completeness: derive readiness from policy-bound mandatory requirements
    verif_status = await compute_verification_status(session, journey_id)
    if verif_status["verification_status"] == VerificationCompleteness.VERIFICATION_COMPLETE.value:
        j_stmt = select(EvaluationJourney).where(EvaluationJourney.id == journey_id)
        journey = (await session.execute(j_stmt)).scalars().first()
        if journey and journey.state != JourneyState.READY_FOR_EVALUATION:
            prev_j_state = journey.state
            journey.state = JourneyState.READY_FOR_EVALUATION
            journey.updated_at = now

            t_record = JourneyTransitionRecord(
                journey_id=journey.id,
                from_state=prev_j_state,
                to_state=JourneyState.READY_FOR_EVALUATION,
                actor="OFFICER",
                reason="All policy-bound mandatory statutory evidence and claims verified by welfare officer. Case ready for statutory evaluation.",
            )
            session.add(t_record)

            review.status = HumanReviewStatus.VERIFIED
            review.decision = "VERIFIED"

            complete_audit = HumanReviewAuditEvent(
                review_id=review.id,
                journey_id=journey.id,
                actor_identity=officer_email,
                actor_role=officer_role,
                action="VERIFICATION_COMPLETED",
                previous_status=prev_j_state.value,
                new_status=JourneyState.READY_FOR_EVALUATION.value,
                reason="Verification complete across all policy mandatory documentary evidence",
                details_json={"verified_items_count": verif_status["verified_evidence_count"]},
            )
            session.add(complete_audit)

    await session.commit()
    await session.refresh(evidence)

    # Build response model
    from app.services.officer_service import format_evidence_label

    v_recs = [
        {
            "id": str(vr.id),
            "method": vr.verification_method,
            "status": vr.status.value,
            "verified_by": vr.verified_by,
            "verified_at": vr.verified_at.isoformat() if vr.verified_at else None,
            "details": vr.details_json,
        }
        for vr in evidence.verification_records
    ]

    return OfficerEvidenceResponse(
        id=evidence.id,
        claim_id=evidence.claim_id,
        claim_type=evidence.claim.claim_type if evidence.claim else "UNKNOWN",
        evidence_type=evidence.evidence_type,
        evidence_type_label=format_evidence_label(evidence.evidence_type),
        storage_reference=evidence.storage_reference,
        metadata_json=evidence.metadata_json,
        status=evidence.status.value,
        submitted_at=evidence.submitted_at,
        verified_at=evidence.verified_at,
        rejected_at=evidence.rejected_at,
        rejection_reason=evidence.rejection_reason,
        verification_records=v_recs,
    )


# ------------------------------------------------------------------------------
# Inspection: Multi-Round Verification History
# ------------------------------------------------------------------------------

async def get_verification_history(
    session: AsyncSession, journey_id: uuid.UUID
) -> OfficerVerificationHistoryResponse:
    """Retrieve complete multi-round verification history, clarification requests, and audit logs."""
    # 1. Fetch Journey with completeness metrics
    status_dict = await compute_verification_status(session, journey_id)

    # 2. Fetch all VerificationRecords for this journey
    vr_stmt = (
        select(VerificationRecord)
        .join(Claim, VerificationRecord.claim_id == Claim.id)
        .where(Claim.journey_id == journey_id)
        .order_by(VerificationRecord.created_at.asc())
    )
    vr_records = (await session.execute(vr_stmt)).scalars().all()

    # 3. Fetch all ClarificationRequests for this journey
    cr_stmt = (
        select(ClarificationRequest)
        .where(ClarificationRequest.journey_id == journey_id)
        .order_by(ClarificationRequest.created_at.asc())
    )
    cr_records = (await session.execute(cr_stmt)).scalars().all()

    # 4. Fetch all HumanReviewAuditEvents
    audit_stmt = (
        select(HumanReviewAuditEvent)
        .where(HumanReviewAuditEvent.journey_id == journey_id)
        .order_by(HumanReviewAuditEvent.created_at.asc())
    )
    audit_events = (await session.execute(audit_stmt)).scalars().all()

    current_round = max([cr.round for cr in cr_records] + [vr.round for vr in vr_records] + [1])

    vr_responses = [
        OfficerVerificationRecordResponse(
            id=vr.id,
            evidence_id=vr.evidence_id,
            claim_id=vr.claim_id,
            round=vr.round,
            verification_method=vr.verification_method,
            status=vr.status.value,
            verified_by=vr.verified_by,
            verified_at=vr.verified_at,
            details=vr.details_json,
            clarification_request_id=vr.clarification_request_id,
            created_at=vr.created_at,
        )
        for vr in vr_records
    ]

    cr_responses = [
        OfficerClarificationItemResponse(
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
        for cr in cr_records
    ]

    audit_responses = [
        OfficerAuditEventResponse(
            id=a.id,
            journey_id=a.journey_id,
            review_id=a.review_id,
            actor_identity=a.actor_identity,
            actor_role=a.actor_role,
            action=a.action,
            previous_status=a.previous_status,
            new_status=a.new_status,
            reason=a.reason,
            details_json=a.details_json,
            created_at=a.created_at,
        )
        for a in audit_events
    ]

    return OfficerVerificationHistoryResponse(
        journey_id=journey_id,
        verification_status=status_dict["verification_status"],
        current_round=current_round,
        verification_records=vr_responses,
        clarification_requests=cr_responses,
        audit_events=audit_responses,
    )


# ------------------------------------------------------------------------------
# Citizen Inspection: Sanitized Clarification Requests (Citizen View)
# ------------------------------------------------------------------------------

async def get_citizen_clarifications(
    session: AsyncSession,
    journey_id: uuid.UUID,
    citizen_db_id: uuid.UUID,
) -> CitizenClarificationListResponse:
    """Retrieve sanitized, citizen-safe clarification requests for an application.

    Strict Invariants:
    - IDOR Protection: returns 404 if application does not belong to authenticated citizen.
    - Strictly filters out internal officer notes, emails, and audit internals.
    """
    stmt = (
        select(EvaluationJourney)
        .options(
            selectinload(EvaluationJourney.scheme),
            selectinload(EvaluationJourney.clarification_requests).selectinload(ClarificationRequest.replacement_evidence),
        )
        .where(
            EvaluationJourney.id == journey_id,
            EvaluationJourney.citizen_id == citizen_db_id,
        )
    )
    journey = (await session.execute(stmt)).scalars().first()
    if not journey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found or does not belong to your account",
        )

    # Compute readiness
    status_dict = await compute_verification_status(session, journey.id)

    from app.api.v1.citizen_applications import build_application_ref

    items = []
    for cr in journey.clarification_requests:
        repl_name = None
        if cr.replacement_evidence and cr.replacement_evidence.metadata_json:
            repl_name = cr.replacement_evidence.metadata_json.get("document_name")

        items.append(
            CitizenClarificationItemResponse(
                id=cr.id,
                round=cr.round,
                evidence_id=cr.evidence_id,
                claim_id=cr.claim_id,
                request_reason=cr.request_reason,
                status=cr.status.value,
                requested_at=cr.requested_at,
                response_text=cr.response_text,
                responded_at=cr.responded_at,
                has_replacement_evidence=bool(cr.replacement_evidence_id),
                replacement_evidence_id=cr.replacement_evidence_id,
                replacement_evidence_name=repl_name,
                resolved_at=cr.resolved_at,
            )
        )

    return CitizenClarificationListResponse(
        application_id=journey.id,
        application_ref=build_application_ref(journey.id, journey.created_at),
        scheme_code=journey.scheme.scheme_code if journey.scheme else "UNKNOWN",
        scheme_name=journey.scheme.name_en if journey.scheme else "Welfare Scheme",
        verification_status=status_dict["verification_status"],
        clarifications=items,
    )
