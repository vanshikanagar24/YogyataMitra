"""Officer / Human Verification Portal service layer.

Implements queue management, case inspection, plain-language claim presentation,
evidence verification, human review determinations, policy provenance inspection,
and immutable append-only audit trail logging.
"""

from __future__ import annotations

import json
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
    AssignmentStatus,
    ClaimStatus,
    EligibilityResult,
    EvidenceStatus,
    HumanReviewStatus,
    JourneyState,
    SLAStatus,
    VerificationStatus,
)
from app.models.evaluation import EvaluationTrace
from app.models.human_review import HumanReview, HumanReviewAuditEvent
from app.models.journey import EvaluationJourney
from app.models.scheme import PolicyVersion, RuleSet, Scheme
from app.schemas.officer import (
    OfficerAssessmentResponse,
    OfficerAssessmentRuleResponse,
    OfficerAssignmentResponse,
    OfficerAuditEventResponse,
    OfficerCaseDetailResponse,
    OfficerCaseReviewRequest,
    OfficerClaimResponse,
    OfficerEvidenceResponse,
    OfficerEvidenceVerifyRequest,
    OfficerPolicyProvenanceResponse,
    OfficerQueueItemResponse,
    OfficerQueueListResponse,
    OfficerQueueMetricsResponse,
)
from app.services.assignment_service import compute_sla_status


# ------------------------------------------------------------------------------
# Plain-Language Formatting Dictionaries & Helpers
# ------------------------------------------------------------------------------

CLAIM_TYPE_LABELS: Dict[str, str] = {
    "land_size_hectares": "Agricultural Landholding",
    "is_farmer": "Farmer Status",
    "is_institutional_landholder": "Institutional Landholder Exemption",
    "is_constitutional_post_holder": "Constitutional Post Holder Exemption",
    "is_retired_or_serving_govt_employee": "Government Service Exemption",
    "is_income_tax_payer": "Income Tax Assessment Exemption",
    "monthly_pension_amount": "Monthly Pension Amount",
    "girl_child_age": "Girl Child Age",
    "is_indian_citizen": "Indian Citizenship",
    "family_girl_children_count": "Number of Girl Children in Family",
    "account_count_for_child": "Existing Accounts for Girl Child",
}

EVIDENCE_TYPE_LABELS: Dict[str, str] = {
    "LAND_RECORD": "Land Ownership Record / Record of Rights (RoR)",
    "AADHAAR": "Aadhaar Card (Identity / Address Proof)",
    "BIRTH_CERTIFICATE": "Birth Certificate (Age Proof)",
    "BANK_PASSBOOK": "Bank Account Passbook",
    "TAX_RETURN": "Income Tax Return (ITR-V)",
    "PENSION_SLIP": "Pension Payment Order / Slip",
}


def format_claim_label(claim_type: str) -> str:
    """Return a plain, accessible title for a claim type."""
    return CLAIM_TYPE_LABELS.get(claim_type, claim_type.replace("_", " ").title())


def format_claim_value(claim_type: str, value_json: Dict[str, Any]) -> str:
    """Format claim value dictionary into plain, human-readable text."""
    val = value_json.get("value", value_json)
    if isinstance(val, bool):
        return "Yes (Confirmed)" if val else "No (Not Applicable)"
    if isinstance(val, (int, float)):
        if claim_type == "land_size_hectares":
            return f"{val} hectares"
        if claim_type == "monthly_pension_amount":
            return f"₹{val:,.2f} per month"
        if claim_type == "girl_child_age":
            return f"{val} years old"
        return str(val)
    if isinstance(val, str):
        return val
    return json.dumps(val)


def format_evidence_label(evidence_type: str) -> str:
    """Return a plain, official document label for an evidence type."""
    return EVIDENCE_TYPE_LABELS.get(evidence_type, evidence_type.replace("_", " ").title())


# ------------------------------------------------------------------------------
# Service Operations
# ------------------------------------------------------------------------------

async def get_or_create_human_review(
    session: AsyncSession, journey_id: uuid.UUID
) -> HumanReview:
    """Get the active HumanReview record for a journey, or initialize a PENDING one."""
    stmt = select(HumanReview).where(HumanReview.journey_id == journey_id)
    res = await session.execute(stmt)
    review = res.scalars().first()
    if not review:
        review = HumanReview(
            journey_id=journey_id,
            reviewer_identity="UNASSIGNED",
            reviewer_role="OFFICER",
            status=HumanReviewStatus.PENDING,
        )
        session.add(review)
        await session.flush()
    return review


async def get_officer_queue(
    session: AsyncSession,
    status_filter: Optional[str] = None,
    scheme_filter: Optional[str] = None,
    sla_filter: Optional[str] = None,
    assigned_to_me: Optional[bool] = None,
    unassigned_only: Optional[bool] = None,
    current_officer_identity: Optional[str] = None,
) -> OfficerQueueListResponse:
    """Query the verification queue and compute aggregate operational metrics including assignment & SLA."""
    # Query all evaluation journeys with related entities
    stmt = (
        select(EvaluationJourney)
        .options(
            selectinload(EvaluationJourney.scheme),
            selectinload(EvaluationJourney.citizen),
            selectinload(EvaluationJourney.claims).selectinload(Claim.evidence_items),
            selectinload(EvaluationJourney.latest_evaluation),
        )
        .order_by(desc(EvaluationJourney.created_at))
    )
    result = await session.execute(stmt)
    journeys = result.scalars().all()

    # Load all human reviews and active assignments for quick lookup
    journey_ids = [j.id for j in journeys]
    reviews_map: Dict[uuid.UUID, HumanReview] = {}
    assignments_map: Dict[uuid.UUID, OfficerAssignment] = {}
    if journey_ids:
        r_stmt = select(HumanReview).where(HumanReview.journey_id.in_(journey_ids))
        r_res = await session.execute(r_stmt)
        for r in r_res.scalars().all():
            reviews_map[r.journey_id] = r

        a_stmt = select(OfficerAssignment).where(
            OfficerAssignment.journey_id.in_(journey_ids),
            OfficerAssignment.is_active == True,
        )
        a_res = await session.execute(a_stmt)
        for a in a_res.scalars().all():
            assignments_map[a.journey_id] = a

    # Compute metrics across all journeys
    total_cases = len(journeys)
    pending_cases = 0
    in_review_cases = 0
    escalated_cases = 0
    completed_cases = 0

    now = datetime.now(timezone.utc)
    queue_items: List[OfficerQueueItemResponse] = []

    for j in journeys:
        rev = reviews_map.get(j.id)
        rev_status = rev.status.value if rev else HumanReviewStatus.PENDING.value
        rev_decision = rev.decision if rev else None

        if rev_status == HumanReviewStatus.PENDING.value:
            pending_cases += 1
        elif rev_status == HumanReviewStatus.IN_REVIEW.value:
            in_review_cases += 1
        elif rev_status == HumanReviewStatus.ESCALATED.value:
            escalated_cases += 1
        elif rev_status in (HumanReviewStatus.COMPLETED.value, HumanReviewStatus.VERIFIED.value):
            completed_cases += 1

        assign = assignments_map.get(j.id)
        assign_officer = assign.officer_identity if assign else None
        assign_officer_name = assign.officer_name if assign else None
        assign_status = assign.status.value if assign else "UNASSIGNED"
        assign_at = assign.assigned_at if assign else None
        due_at = assign.due_at if assign else None

        sla_st = compute_sla_status(assign.due_at, assign.status, now) if assign else SLAStatus.NOT_DUE

        # Filter by review status
        if status_filter and status_filter.upper() != "ALL":
            if rev_status.upper() != status_filter.upper():
                continue

        # Filter by scheme
        if scheme_filter and scheme_filter.upper() != "ALL":
            if j.scheme.scheme_code.upper() != scheme_filter.upper():
                continue

        # Filter by SLA status
        if sla_filter and sla_filter.upper() != "ALL":
            if sla_st.value != sla_filter.upper():
                continue

        # Filter: assigned to me
        if assigned_to_me:
            if not assign or assign.officer_identity.lower() != (current_officer_identity or "").lower():
                continue

        # Filter: unassigned only
        if unassigned_only:
            if assign is not None:
                continue

        # Count evidence items
        evidence_count = 0
        verified_evidence_count = 0
        for c in j.claims:
            for ev in c.evidence_items:
                evidence_count += 1
                if ev.status == EvidenceStatus.VERIFIED:
                    verified_evidence_count += 1

        # Automated eligibility preview
        auto_eligibility = None
        if j.latest_evaluation:
            auto_eligibility = j.latest_evaluation.result_state.value

        citizen_ref = getattr(j.citizen, "synthetic_id", None) or f"SYN-CIT-{str(j.citizen_id)[:8].upper()}"

        queue_items.append(
            OfficerQueueItemResponse(
                journey_id=j.id,
                citizen_ref=citizen_ref,
                scheme_code=j.scheme.scheme_code,
                scheme_name=j.scheme.name_en,
                journey_state=j.state.value,
                submitted_at=j.submitted_at or j.created_at,
                review_status=rev_status,
                review_decision=rev_decision,
                evidence_count=evidence_count,
                verified_evidence_count=verified_evidence_count,
                automated_eligibility=auto_eligibility,
                assigned_officer=assign_officer,
                assigned_officer_name=assign_officer_name,
                assignment_status=assign_status,
                assigned_at=assign_at,
                due_at=due_at,
                sla_status=sla_st.value,
            )
        )

    metrics = OfficerQueueMetricsResponse(
        total_cases=total_cases,
        pending_cases=pending_cases,
        in_review_cases=in_review_cases,
        escalated_cases=escalated_cases,
        completed_cases=completed_cases,
    )

    return OfficerQueueListResponse(metrics=metrics, items=queue_items)



async def get_case_detail(
    session: AsyncSession, journey_id: uuid.UUID
) -> OfficerCaseDetailResponse:
    """Retrieve full case dossier for officer inspection and verification."""
    stmt = (
        select(EvaluationJourney)
        .options(
            selectinload(EvaluationJourney.scheme),
            selectinload(EvaluationJourney.citizen),
            selectinload(EvaluationJourney.claims).selectinload(Claim.evidence_items).selectinload(Evidence.verification_records),
            selectinload(EvaluationJourney.latest_evaluation).selectinload(EvaluationTrace.policy_version),
            selectinload(EvaluationJourney.clarification_requests).selectinload(ClarificationRequest.replacement_evidence),
        )
        .where(EvaluationJourney.id == journey_id)
    )
    res = await session.execute(stmt)
    journey = res.scalars().first()
    if not journey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Verification case with ID '{journey_id}' was not found",
        )

    # Get or initialize HumanReview
    review = await get_or_create_human_review(session, journey.id)

    # Fetch audit history for this journey
    audit_stmt = (
        select(HumanReviewAuditEvent)
        .where(HumanReviewAuditEvent.journey_id == journey.id)
        .order_by(HumanReviewAuditEvent.created_at.asc())
    )
    audit_res = await session.execute(audit_stmt)
    audit_records = audit_res.scalars().all()

    # Format claims
    claims_response: List[OfficerClaimResponse] = []
    evidence_response: List[OfficerEvidenceResponse] = []

    for c in journey.claims:
        claims_response.append(
            OfficerClaimResponse(
                id=c.id,
                claim_type=c.claim_type,
                claim_label=format_claim_label(c.claim_type),
                value_json=c.value_json,
                value_display=format_claim_value(c.claim_type, c.value_json),
                source=c.source,
                status=c.status.value,
                claimed_at=c.claimed_at,
            )
        )

        for ev in c.evidence_items:
            v_recs = [
                {
                    "id": str(vr.id),
                    "method": vr.verification_method,
                    "status": vr.status.value,
                    "verified_by": vr.verified_by,
                    "verified_at": vr.verified_at.isoformat() if vr.verified_at else None,
                    "details": vr.details_json,
                }
                for vr in ev.verification_records
            ]
            evidence_response.append(
                OfficerEvidenceResponse(
                    id=ev.id,
                    claim_id=ev.claim_id,
                    claim_type=c.claim_type,
                    evidence_type=ev.evidence_type,
                    evidence_type_label=format_evidence_label(ev.evidence_type),
                    storage_reference=ev.storage_reference,
                    metadata_json=ev.metadata_json,
                    status=ev.status.value,
                    submitted_at=ev.submitted_at,
                    verified_at=ev.verified_at,
                    rejected_at=ev.rejected_at,
                    rejection_reason=ev.rejection_reason,
                    verification_records=v_recs,
                )
            )

    # Parse automated assessment
    assessment_response: Optional[OfficerAssessmentResponse] = None
    if journey.latest_evaluation:
        trace = journey.latest_evaluation
        trace_json = trace.trace_json or {}
        rules_evaluated: List[OfficerAssessmentRuleResponse] = []

        for r in trace_json.get("rules_evaluated", []):
            rules_evaluated.append(
                OfficerAssessmentRuleResponse(
                    rule_id=r.get("rule_id", "UNKNOWN"),
                    rule_name=r.get("rule_name", r.get("rule_id", "Statutory Rule")),
                    description=r.get("description", ""),
                    result=r.get("result", "UNKNOWN"),
                    details=r.get("details") or r.get("reason"),
                    operator=r.get("operator"),
                    expected_value=str(r.get("expected_value")) if r.get("expected_value") is not None else None,
                    actual_value=str(r.get("actual_value")) if r.get("actual_value") is not None else None,
                )
            )

        raw_missing = trace_json.get("missing_facts", [])
        missing_facts = [
            item.get("fact_key", item.get("name", str(item))) if isinstance(item, dict) else str(item)
            for item in raw_missing
        ]

        raw_disqualifiers = trace_json.get("disqualifiers", trace_json.get("blockers", []))
        disqualifiers = [
            item.get("message", item.get("description", item.get("code", str(item))))
            if isinstance(item, dict) else str(item)
            for item in raw_disqualifiers
        ]

        assessment_response = OfficerAssessmentResponse(
            evaluation_id=trace.id,
            determination=trace.result_state.value,
            evaluated_at=trace.created_at,
            ruleset_version=trace.policy_version.version_code if trace.policy_version else "1.0",
            ruleset_hash=trace.rule_definition_hash,
            rules_evaluated=rules_evaluated,
            missing_facts=missing_facts,
            disqualifiers=disqualifiers,
            reasons_en=trace_json.get("reasons_en", []),
            reasons_hi=trace_json.get("reasons_hi", []),
        )

    # Policy provenance
    policy_prov: Optional[OfficerPolicyProvenanceResponse] = None
    if journey.latest_evaluation and journey.latest_evaluation.policy_version:
        pv = journey.latest_evaluation.policy_version
        rs_stmt = select(RuleSet).where(RuleSet.policy_version_id == pv.id)
        rs_res = await session.execute(rs_stmt)
        ruleset = rs_res.scalars().first()
        rule_count = len(ruleset.definition_json.get("rules", [])) if ruleset else 0

        # Check for bound official document version
        from app.models.provenance import OfficialDocument, OfficialDocumentVersion, PolicySourceBinding
        bind_stmt = (
            select(PolicySourceBinding)
            .options(
                selectinload(PolicySourceBinding.document_version)
                .selectinload(OfficialDocumentVersion.document)
            )
            .where(PolicySourceBinding.policy_version_id == pv.id)
        )
        bind_res = await session.execute(bind_stmt)
        binding = bind_res.scalars().first()

        doc_title = None
        doc_ver = None
        doc_hash = None
        source_url = pv.source_url
        issuing_auth = "Government of India / Nodal Ministry"
        comp = "COMPLETE"

        if binding and binding.document_version:
            dv = binding.document_version
            doc = dv.document
            doc_title = doc.document_title
            doc_ver = dv.version_label
            doc_hash = dv.document_hash
            source_url = dv.official_url
            issuing_auth = doc.issuing_authority
            comp = dv.provenance_completeness.value

        policy_prov = OfficerPolicyProvenanceResponse(
            scheme_code=journey.scheme.scheme_code,
            scheme_name=journey.scheme.name_en,
            policy_version=pv.version_code,
            ruleset_version=ruleset.rule_set_version if ruleset else "1.0",
            effective_from=str(pv.effective_from),
            effective_to=str(pv.effective_to) if pv.effective_to else None,
            content_sha256=pv.rule_definition_hash or "N/A",
            official_citation=pv.source_title,
            gazette_reference=pv.source_document_identifier or "Official Gazette of India",
            issuing_authority=issuing_auth,
            rule_definitions_count=rule_count,
            is_statutory_source_verified=True,
            document_title=doc_title,
            document_version=doc_ver,
            document_hash=doc_hash,
            official_source_url=source_url,
            provenance_completeness=comp,
        )

    # Audit events
    audit_history = [
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
        for a in audit_records
    ]

    # Assignments and SLA history
    assign_stmt = (
        select(OfficerAssignment)
        .where(OfficerAssignment.journey_id == journey.id)
        .order_by(desc(OfficerAssignment.created_at))
    )
    assign_res = await session.execute(assign_stmt)
    db_assignments = list(assign_res.scalars().all())

    now = datetime.now(timezone.utc)
    active_assign_model: Optional[OfficerAssignmentResponse] = None
    assignment_history: List[OfficerAssignmentResponse] = []

    for a in db_assignments:
        sla_st = compute_sla_status(a.due_at, a.status, now)
        a_model = OfficerAssignmentResponse(
            id=a.id,
            journey_id=a.journey_id,
            officer_identity=a.officer_identity,
            officer_name=a.officer_name,
            assigned_by=a.assigned_by,
            assigned_at=a.assigned_at,
            due_at=a.due_at,
            sla_duration_hours=a.sla_duration_hours,
            status=a.status.value,
            is_active=a.is_active,
            reassigned_to_id=a.reassigned_to_id,
            reassignment_reason=a.reassignment_reason,
            sla_status=sla_st.value,
            created_at=a.created_at,
            updated_at=a.updated_at,
        )
        assignment_history.append(a_model)
        if a.is_active and not active_assign_model:
            active_assign_model = a_model

    from app.services.verification_service import compute_verification_status
    v_metrics = await compute_verification_status(session, journey.id)
    v_status = v_metrics["verification_status"]

    clarifications_list = [
        {
            "id": str(cr.id),
            "journey_id": str(cr.journey_id),
            "evidence_id": str(cr.evidence_id) if cr.evidence_id else None,
            "claim_id": str(cr.claim_id) if cr.claim_id else None,
            "round": cr.round,
            "requesting_officer": cr.requesting_officer,
            "requesting_officer_role": cr.requesting_officer_role,
            "request_reason": cr.request_reason,
            "notes": cr.notes,
            "status": cr.status.value,
            "requested_at": cr.requested_at.isoformat() if cr.requested_at else None,
            "response_text": cr.response_text,
            "responded_at": cr.responded_at.isoformat() if cr.responded_at else None,
            "replacement_evidence_id": str(cr.replacement_evidence_id) if cr.replacement_evidence_id else None,
            "resolution_notes": cr.resolution_notes,
            "resolved_at": cr.resolved_at.isoformat() if cr.resolved_at else None,
            "resolved_by": cr.resolved_by,
            "created_at": cr.created_at.isoformat() if cr.created_at else None,
        }
        for cr in (journey.clarification_requests or [])
    ]

    citizen_ref = getattr(journey.citizen, "synthetic_id", None) or f"SYN-CIT-{str(journey.citizen_id)[:8].upper()}"

    return OfficerCaseDetailResponse(
        journey_id=journey.id,
        citizen_ref=citizen_ref,
        scheme_code=journey.scheme.scheme_code,
        scheme_name=journey.scheme.name_en,
        journey_state=journey.state.value,
        submitted_at=journey.submitted_at or journey.created_at,
        updated_at=journey.updated_at,
        review_status=review.status.value,
        review_decision=review.decision,
        review_notes=review.notes,
        reviewer_identity=review.reviewer_identity,
        reviewer_role=review.reviewer_role,
        claims=claims_response,
        evidence_items=evidence_response,
        automated_assessment=assessment_response,
        policy_provenance=policy_prov,
        audit_history=audit_history,
        active_assignment=active_assign_model,
        assignment_history=assignment_history,
        clarifications=clarifications_list,
        verification_status=v_status,
    )



async def verify_evidence_item(
    session: AsyncSession,
    journey_id: uuid.UUID,
    evidence_id: uuid.UUID,
    request: OfficerEvidenceVerifyRequest,
    current_officer: Dict[str, Any],
) -> OfficerEvidenceResponse:
    """Verify, reject, or request clarification on an individual evidence item.

    Strict Invariants:
    - Never mutates Claim.value_json.
    - Appends a VerificationRecord (Phase 7 audit model).
    - Appends an immutable HumanReviewAuditEvent record.
    """
    valid_actions = ("VERIFY", "REJECT", "REQUEST_CLARIFICATION")
    action_upper = request.action.upper().strip()
    if action_upper not in valid_actions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid verification action '{request.action}'. Allowed: {', '.join(valid_actions)}",
        )

    if action_upper in ("REJECT", "REQUEST_CLARIFICATION") and (not request.reason or not request.reason.strip()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Mandatory 'reason' justification is required when action is {action_upper}",
        )

    # Load evidence and verify it belongs to this journey
    stmt = (
        select(Evidence)
        .join(Claim, Evidence.claim_id == Claim.id)
        .options(selectinload(Evidence.claim), selectinload(Evidence.verification_records))
        .where(Evidence.id == evidence_id, Claim.journey_id == journey_id)
    )
    res = await session.execute(stmt)
    evidence = res.scalars().first()
    if not evidence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence '{evidence_id}' for journey '{journey_id}' was not found",
        )

    # Get or initialize HumanReview
    review = await get_or_create_human_review(session, journey_id)
    if review.status == HumanReviewStatus.PENDING:
        review.status = HumanReviewStatus.IN_REVIEW
        review.reviewer_identity = current_officer["email"]
        review.reviewer_role = current_officer["role"]

    prev_evidence_status = evidence.status.value
    now = datetime.now(timezone.utc)

    # Determine status transitions
    if action_upper == "VERIFY":
        evidence.status = EvidenceStatus.VERIFIED
        evidence.verified_at = now
        evidence.rejected_at = None
        evidence.rejection_reason = None
        v_status = VerificationStatus.VERIFIED
    elif action_upper == "REJECT":
        evidence.status = EvidenceStatus.REJECTED
        evidence.rejected_at = now
        evidence.rejection_reason = request.reason.strip()
        v_status = VerificationStatus.REJECTED
    else:  # REQUEST_CLARIFICATION
        evidence.status = EvidenceStatus.PENDING
        evidence.rejection_reason = f"Clarification requested: {request.reason.strip()}"
        v_status = VerificationStatus.PENDING

    # Create VerificationRecord (Phase 7 model)
    v_record = VerificationRecord(
        evidence_id=evidence.id,
        claim_id=evidence.claim_id,
        verification_method="OFFICER_MANUAL_REVIEW",
        status=v_status,
        verified_by=current_officer["email"],
        verified_at=now,
        details_json={
            "action": action_upper,
            "reason": request.reason,
            "notes": request.notes,
            "officer_role": current_officer["role"],
        },
    )
    session.add(v_record)

    # Append immutable HumanReviewAuditEvent
    audit_event = HumanReviewAuditEvent(
        review_id=review.id,
        journey_id=journey_id,
        actor_identity=current_officer["email"],
        actor_role=current_officer["role"],
        action=f"EVIDENCE_{action_upper}",
        previous_status=prev_evidence_status,
        new_status=evidence.status.value,
        reason=request.reason,
        details_json={
            "evidence_id": str(evidence.id),
            "evidence_type": evidence.evidence_type,
            "notes": request.notes,
        },
    )
    session.add(audit_event)

    await session.commit()
    await session.refresh(evidence)

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
        claim_type=evidence.claim.claim_type,
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


async def record_case_review(
    session: AsyncSession,
    journey_id: uuid.UUID,
    request: OfficerCaseReviewRequest,
    current_officer: Dict[str, Any],
) -> OfficerCaseDetailResponse:
    """Record an overall officer determination on a case.

    Supported decisions:
    - VERIFIED: All claims and evidence verified.
    - CLARIFICATION_REQUIRED: Officer requests citizen follow-up (mandatory reason).
    - REJECTED: Evidence or claims invalid (mandatory reason).
    - ESCALATED: Escalated to Supervisor for policy or integrity review (mandatory reason).
    - COMPLETED: Review finalized.

    RBAC Rule:
    - If a case is already in ESCALATED state, only a SUPERVISOR can change its status
      to COMPLETED or VERIFIED.
    """
    valid_decisions = ("VERIFIED", "CLARIFICATION_REQUIRED", "REJECTED", "ESCALATED", "COMPLETED")
    decision_upper = request.decision.upper().strip()
    if decision_upper not in valid_decisions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid decision '{request.decision}'. Allowed: {', '.join(valid_decisions)}",
        )

    # Mandatory reason check for adverse or escalated actions
    if decision_upper in ("CLARIFICATION_REQUIRED", "REJECTED", "ESCALATED") and (
        not request.reason or not request.reason.strip()
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Mandatory 'reason' justification is required when decision is {decision_upper}",
        )

    review = await get_or_create_human_review(session, journey_id)
    prev_status = review.status.value

    # RBAC protection: Resolving an escalated case requires SUPERVISOR role
    if review.status == HumanReviewStatus.ESCALATED and decision_upper in ("COMPLETED", "VERIFIED", "REJECTED"):
        if current_officer["role"] != "SUPERVISOR":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Elevated privilege required: Only a Welfare Review Supervisor can resolve an escalated case.",
            )
        if not request.reason or not request.reason.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Supervisor resolution requires a mandatory supervisory justification reason.",
            )

    # Update review state
    target_status = HumanReviewStatus(decision_upper)
    review.status = target_status
    review.decision = decision_upper
    review.reason = request.reason.strip() if request.reason else None
    review.notes = request.notes.strip() if request.notes else None
    review.reviewer_identity = current_officer["email"]
    review.reviewer_role = current_officer["role"]

    # Append immutable audit trail event
    audit_event = HumanReviewAuditEvent(
        review_id=review.id,
        journey_id=journey_id,
        actor_identity=current_officer["email"],
        actor_role=current_officer["role"],
        action=f"DECISION_{decision_upper}",
        previous_status=prev_status,
        new_status=decision_upper,
        reason=request.reason,
        details_json={
            "notes": request.notes,
            "decision": decision_upper,
        },
    )
    session.add(audit_event)

    await session.commit()

    return await get_case_detail(session, journey_id)
