"""Comprehensive Test Suite for YogyataMitra Phase E.

Operational Evidence Verification & Clarification Workflow.

Verifies:
1. Operational Evidence Verification Model:
   - Initial submitted evidence items in PENDING status
   - Linking to claims with immutability of asserted factual claim values
2. Officer Evidence Verification:
   - Officer can verify evidence (VERIFY -> VERIFIED, creates VerificationRecord, logs EVIDENCE_VERIFIED audit)
   - Officer can reject evidence (REJECT -> REJECTED, mandatory justification required, logs EVIDENCE_REJECTED audit)
   - Claim status updated to VERIFIED / REJECTED without mutating declared facts
3. Operational Clarification Workflow:
   - Officer can initiate clarification request (CLARIFICATION_REQUIRED status, round tracked, logs audit)
   - Journey transitions to ACTION_REQUIRED
4. Citizen Clarification Response:
   - Citizen can view clarifications (internal officer notes stripped)
   - Citizen can respond with explanation and optional replacement evidence
   - Clarification transitions to RESPONDED, journey transitions back to VERIFICATION_IN_PROGRESS
   - Anti-spoofing enforcement (extra="forbid" on request payloads)
5. Multi-round Verification & History Preservation:
   - Subsequent rounds (Round 1, Round 2) tracked immutably
   - Verification history endpoint returns all rounds, records, and audit events
6. Backend-Driven Verification Completeness:
   - Derived readiness states: VERIFICATION_IN_PROGRESS, CLARIFICATION_REQUIRED, VERIFICATION_BLOCKED, VERIFICATION_COMPLETE
   - Transition to READY_FOR_EVALUATION upon completeness without invoking statutory AST engine
7. Security & IDOR Protection:
   - Citizen A cannot view or respond to Citizen B's clarifications (returns 404)
   - Role boundaries enforced (403 for cross-role access, 401 for unauthenticated)
8. End-to-end Regression:
   - Phase A, B, C, D compatibility with Phase E verification
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.assignment import OfficerAssignment
from app.models.citizen import Citizen, Claim, Evidence, VerificationRecord
from app.models.clarification import ClarificationRequest
from app.models.enums import (
    AssignmentStatus,
    ClaimStatus,
    ClarificationStatus,
    EvidenceStatus,
    JourneyState,
    SchemeStatus,
    VerificationCompleteness,
)
from app.models.human_review import HumanReviewAuditEvent
from app.models.journey import EvaluationJourney
from app.models.scheme import PolicyVersion, Scheme
from app.services.verification_service import (
    compute_verification_status,
    request_clarification,
    verify_evidence,
    verify_officer_case_access,
)


def _make_officer_token(
    email: str = "officer.verif@yogyatamitra.local",
    role: str = "OFFICER",
    name: str = "Verification Officer Grade I",
) -> str:
    """Generate a valid officer Bearer JWT."""
    payload = {
        "sub": email,
        "email": email,
        "role": role,
        "name": name,
        "designation": "Verification Officer Grade I",
        "department": "Evidence Scrutiny Directorate",
    }
    return create_access_token(data=payload)


def _make_citizen_token(
    email: str = "citizen.applicant@test.local",
    ref: str = "SYN-CIT-PHASE-E",
    name: str = "Radha Sharma",
) -> str:
    """Generate a valid citizen Bearer JWT."""
    payload = {
        "sub": email,
        "role": "CITIZEN",
        "citizen_ref": ref,
        "name": name,
        "state": "Uttar Pradesh",
        "district": "Varanasi",
    }
    return create_access_token(data=payload)


async def _create_test_journey_with_evidence(
    session: AsyncSession,
    scheme_code: str = "PM_KISAN",
    citizen_ref: str = "SYN-CIT-PHASE-E",
    num_evidence_items: int = 1,
    evidence_types: list[str] | None = None,
    initial_journey_state: JourneyState = JourneyState.VERIFICATION_IN_PROGRESS,
    assigned_officer_email: str | None = "officer.verif@yogyatamitra.local",
    policy_version_id: uuid.UUID | None = None,
) -> tuple[EvaluationJourney, Citizen, list[Claim], list[Evidence]]:
    """Helper to persist a submitted journey with claims and evidence."""
    # 1. Scheme
    stmt = select(Scheme).where(Scheme.scheme_code == scheme_code)
    scheme = (await session.execute(stmt)).scalars().first()
    if not scheme:
        scheme = Scheme(
            id=uuid.uuid4(),
            scheme_code=scheme_code,
            name_en=f"Scheme {scheme_code}",
            status=SchemeStatus.ACTIVE,
        )
        session.add(scheme)
        await session.flush()

    # Policy Version
    pv_id = policy_version_id
    if not pv_id:
        pv_stmt = (
            select(PolicyVersion)
            .where(PolicyVersion.scheme_id == scheme.id)
            .order_by(PolicyVersion.effective_from.desc())
        )
        pv = (await session.execute(pv_stmt)).scalars().first()
        if pv:
            pv_id = pv.id
        else:
            new_pv = PolicyVersion(
                id=uuid.uuid4(),
                scheme_id=scheme.id,
                version_code="v1.0-test",
                effective_from=date(2023, 1, 1),
                source_url="https://welfare.gov.in/test",
                source_title="Statutory Test Policy",
            )
            session.add(new_pv)
            await session.flush()
            pv_id = new_pv.id

    # 2. Citizen
    stmt_cit = select(Citizen).where(Citizen.synthetic_reference == citizen_ref)
    citizen = (await session.execute(stmt_cit)).scalars().first()
    if not citizen:
        citizen = Citizen(
            id=uuid.uuid4(),
            synthetic_reference=citizen_ref,
            display_name="Radha Sharma",
        )
        session.add(citizen)
        await session.flush()

    # 3. Journey
    now = datetime.now(timezone.utc)
    journey = EvaluationJourney(
        id=uuid.uuid4(),
        citizen_id=citizen.id,
        scheme_id=scheme.id,
        policy_version_id=pv_id,
        state=initial_journey_state,
        submitted_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(journey)
    await session.flush()

    # 4. Active Assignment
    if assigned_officer_email:
        assignment = OfficerAssignment(
            id=uuid.uuid4(),
            journey_id=journey.id,
            officer_identity=assigned_officer_email,
            officer_name="Verification Officer Grade I",
            assigned_by="SYSTEM_BALANCER",
            assigned_at=now,
            due_at=now + timedelta(hours=48),
            sla_duration_hours=48,
            status=AssignmentStatus.ASSIGNED,
            is_active=True,
        )
        session.add(assignment)
        await session.flush()

    # 5. Claims and Evidence
    claims = []
    evidence_items = []
    types_to_create = evidence_types if evidence_types is not None else [
        "LAND_RECORD" if i == 0 else f"EVIDENCE_TYPE_{i+1}" for i in range(num_evidence_items)
    ]
    for i, ev_type in enumerate(types_to_create):
        claim = Claim(
            id=uuid.uuid4(),
            citizen_id=citizen.id,
            journey_id=journey.id,
            claim_type=f"CRITERION_{ev_type}_{i+1}",
            value_json={"land_holding_hectares": 1.5, "is_cultivable": True, "index": i + 1},
            status=ClaimStatus.PENDING,
            source="CITIZEN_DECLARATION",
            claimed_at=now,
        )
        session.add(claim)
        await session.flush()
        claims.append(claim)

        ev = Evidence(
            id=uuid.uuid4(),
            claim_id=claim.id,
            evidence_type=ev_type,
            storage_reference=f"docs/{ev_type.lower()}_{i+1}.pdf",
            metadata_json={"document_name": f"{ev_type} {i+1}.pdf", "file_size_bytes": 102400},
            status=EvidenceStatus.PENDING,
            submitted_at=now,
        )
        session.add(ev)
        await session.flush()
        evidence_items.append(ev)

    await session.commit()
    await session.refresh(journey)
    for c in claims:
        await session.refresh(c)
    for ev in evidence_items:
        await session.refresh(ev)

    return journey, citizen, claims, evidence_items


# ==============================================================================
# 1. Operational Evidence Verification Model & Findings Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_officer_verify_evidence_success(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verify an officer can record a VERIFY finding on submitted evidence."""
    journey, citizen, claims, evidence_items = await _create_test_journey_with_evidence(
        db_session, num_evidence_items=1
    )
    ev = evidence_items[0]
    claim = claims[0]

    token = _make_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "action": "VERIFY",
        "notes": "Verified against state land revenue database.",
    }

    resp = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evidence/{ev.id}/verify",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "VERIFIED"
    assert data["id"] == str(ev.id)

    # Verify claim status updated without mutating declared values
    await db_session.refresh(claim)
    assert claim.status == ClaimStatus.VERIFIED
    assert claim.value_json == {"land_holding_hectares": 1.5, "is_cultivable": True, "index": 1}

    # Verify audit event and verification record
    await db_session.refresh(ev)
    assert ev.status == EvidenceStatus.VERIFIED
    assert ev.verified_at is not None

    stmt_vr = select(VerificationRecord).where(VerificationRecord.evidence_id == ev.id)
    vr = (await db_session.execute(stmt_vr)).scalars().first()
    assert vr is not None
    assert vr.status == "VERIFIED"

    stmt_audit = select(HumanReviewAuditEvent).where(
        HumanReviewAuditEvent.journey_id == journey.id,
        HumanReviewAuditEvent.action == "EVIDENCE_VERIFIED",
    )
    audit = (await db_session.execute(stmt_audit)).scalars().first()
    assert audit is not None


@pytest.mark.asyncio
async def test_officer_reject_evidence_with_mandatory_reason(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verify evidence rejection requires a mandatory justification reason."""
    journey, citizen, claims, evidence_items = await _create_test_journey_with_evidence(
        db_session, num_evidence_items=1
    )
    ev = evidence_items[0]
    claim = claims[0]

    token = _make_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Missing reason must fail
    resp_bad = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evidence/{ev.id}/verify",
        json={"action": "REJECT"},
        headers=headers,
    )
    assert resp_bad.status_code == 422

    # 2. Rejection with mandatory reason succeeds
    rejection_reason = "Document unreadable, resolution below minimum statutory threshold."
    resp_ok = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evidence/{ev.id}/verify",
        json={"action": "REJECT", "reason": rejection_reason, "notes": "Officer manual rejection"},
        headers=headers,
    )
    assert resp_ok.status_code == 200
    data = resp_ok.json()
    assert data["status"] == "REJECTED"
    assert data["rejection_reason"] == rejection_reason

    # Verify claim status updated to REJECTED but value preserved
    await db_session.refresh(claim)
    assert claim.status == ClaimStatus.REJECTED
    assert claim.value_json == {"land_holding_hectares": 1.5, "is_cultivable": True, "index": 1}

    # Verify audit event
    stmt_audit = select(HumanReviewAuditEvent).where(
        HumanReviewAuditEvent.journey_id == journey.id,
        HumanReviewAuditEvent.action == "EVIDENCE_REJECTED",
    )
    audit = (await db_session.execute(stmt_audit)).scalars().first()
    assert audit is not None
    assert audit.reason == rejection_reason


# ==============================================================================
# 2. Operational Clarification Workflow Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_officer_request_clarification(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verify officer can request clarification and journey transitions to ACTION_REQUIRED."""
    journey, citizen, claims, evidence_items = await _create_test_journey_with_evidence(
        db_session, num_evidence_items=1
    )
    ev = evidence_items[0]

    token = _make_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    clarification_reason = "Land record is dated 2018. Please upload updated Khatauni from 2026."
    payload = {
        "reason": clarification_reason,
        "notes": "Internal review note: Check land parcel registry",
    }

    resp = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evidence/{ev.id}/clarification",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "OPEN"
    assert data["round"] == 1
    assert data["request_reason"] == clarification_reason
    assert data["notes"] == "Internal review note: Check land parcel registry"

    # Verify evidence status transitioned to CLARIFICATION_REQUIRED
    await db_session.refresh(ev)
    assert ev.status == EvidenceStatus.CLARIFICATION_REQUIRED

    # Verify journey transitioned to ACTION_REQUIRED
    await db_session.refresh(journey)
    assert journey.state == JourneyState.ACTION_REQUIRED

    # Verify ClarificationRequest record in DB
    stmt_cl = select(ClarificationRequest).where(ClarificationRequest.journey_id == journey.id)
    cl = (await db_session.execute(stmt_cl)).scalars().first()
    assert cl is not None
    assert cl.status == ClarificationStatus.OPEN
    assert cl.round == 1


# ==============================================================================
# 3. Citizen Clarification Response & IDOR Protection Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_citizen_view_clarifications_and_idor_protection(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verify citizen sees clarifications with notes stripped, and Citizen B is blocked (404)."""
    journey, citizen, claims, evidence_items = await _create_test_journey_with_evidence(
        db_session, citizen_ref="SYN-CIT-OWNER"
    )
    ev = evidence_items[0]

    # Officer creates clarification
    officer_token = _make_officer_token()
    await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evidence/{ev.id}/clarification",
        json={"reason": "Upload legible record", "notes": "CONFIDENTIAL_INTERNAL_NOTE_DO_NOT_LEAK"},
        headers={"Authorization": f"Bearer {officer_token}"},
    )

    # 1. Owner Citizen views clarifications
    citizen_token = _make_citizen_token(email="owner@test.local", ref="SYN-CIT-OWNER")
    resp_owner = await async_client.get(
        f"/api/v1/citizen/applications/{journey.id}/clarifications",
        headers={"Authorization": f"Bearer {citizen_token}"},
    )
    assert resp_owner.status_code == 200
    data = resp_owner.json()
    assert len(data["clarifications"]) == 1
    item = data["clarifications"][0]
    assert item["request_reason"] == "Upload legible record"
    assert item["status"] == "OPEN"
    # Internal officer notes MUST NOT be leaked to citizen
    assert "CONFIDENTIAL_INTERNAL_NOTE_DO_NOT_LEAK" not in str(data)

    # 2. Attacker Citizen B attempts to access Owner's clarifications -> 404
    attacker_token = _make_citizen_token(email="attacker@test.local", ref="SYN-CIT-ATTACKER")
    resp_attacker = await async_client.get(
        f"/api/v1/citizen/applications/{journey.id}/clarifications",
        headers={"Authorization": f"Bearer {attacker_token}"},
    )
    assert resp_attacker.status_code == 404


@pytest.mark.asyncio
async def test_citizen_respond_to_clarification_with_replacement_evidence(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verify citizen can respond to open clarification with text and replacement evidence."""
    journey, citizen, claims, evidence_items = await _create_test_journey_with_evidence(
        db_session, citizen_ref="SYN-CIT-RESPONDER"
    )
    ev = evidence_items[0]

    # Officer creates clarification
    officer_token = _make_officer_token()
    resp_cl = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evidence/{ev.id}/clarification",
        json={"reason": "Please provide 2026 revenue passbook"},
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    clarification_id = resp_cl.json()["id"]

    # Citizen responds
    citizen_token = _make_citizen_token(email="responder@test.local", ref="SYN-CIT-RESPONDER")
    response_payload = {
        "response_text": "I have uploaded the current 2026 digital revenue passbook issued by Tehsildar.",
        "replacement_evidence": {
            "document_name": "Revenue_Passbook_2026.pdf",
            "storage_reference": "docs/rev_passbook_2026.pdf",
            "evidence_type": "LAND_REVENUE_RECORD",
        },
    }

    resp_respond = await async_client.post(
        f"/api/v1/citizen/applications/{journey.id}/clarifications/{clarification_id}/respond",
        json=response_payload,
        headers={"Authorization": f"Bearer {citizen_token}"},
    )
    assert resp_respond.status_code == 200, resp_respond.text
    data = resp_respond.json()
    assert data["status"] == "RESPONDED"
    assert data["response_text"] == response_payload["response_text"]
    assert data["has_replacement_evidence"] is True
    assert data["replacement_evidence_id"] is not None

    # Journey transitions back to VERIFICATION_IN_PROGRESS
    await db_session.refresh(journey)
    assert journey.state == JourneyState.VERIFICATION_IN_PROGRESS

    # Audit event logged
    stmt_audit = select(HumanReviewAuditEvent).where(
        HumanReviewAuditEvent.journey_id == journey.id,
        HumanReviewAuditEvent.action == "CLARIFICATION_RESPONDED",
    )
    audit = (await db_session.execute(stmt_audit)).scalars().first()
    assert audit is not None
    assert audit.actor_role == "CITIZEN"


@pytest.mark.asyncio
async def test_citizen_anti_spoofing_extra_fields_forbidden(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verify citizen request schema forbids extra fields to prevent metadata spoofing."""
    journey, citizen, claims, evidence_items = await _create_test_journey_with_evidence(
        db_session, citizen_ref="SYN-CIT-SPOOF"
    )
    ev = evidence_items[0]

    # Officer creates clarification
    officer_token = _make_officer_token()
    resp_cl = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evidence/{ev.id}/clarification",
        json={"reason": "Document needs clarification"},
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    clarification_id = resp_cl.json()["id"]

    citizen_token = _make_citizen_token(email="spoof@test.local", ref="SYN-CIT-SPOOF")

    # Attacker tries to inject status or internal fields
    bad_payload = {
        "response_text": "Trying to bypass verification",
        "status": "RESOLVED",
        "injected_field": "exploit",
    }
    resp = await async_client.post(
        f"/api/v1/citizen/applications/{journey.id}/clarifications/{clarification_id}/respond",
        json=bad_payload,
        headers={"Authorization": f"Bearer {citizen_token}"},
    )
    assert resp.status_code == 422  # Pydantic validation error due to extra="forbid"


# ==============================================================================
# 4. Multi-Round Verification & History Preservation Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_multi_round_clarification_history_preservation(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verify multiple rounds of clarification are preserved immutably in verification history."""
    journey, citizen, claims, evidence_items = await _create_test_journey_with_evidence(
        db_session, citizen_ref="SYN-CIT-MULTIRANK"
    )
    ev = evidence_items[0]

    officer_token = _make_officer_token()
    citizen_token = _make_citizen_token(email="multi@test.local", ref="SYN-CIT-MULTIRANK")

    # Round 1: Request & Respond
    resp_r1 = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evidence/{ev.id}/clarification",
        json={"reason": "Round 1: Document stamp missing"},
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    r1_id = resp_r1.json()["id"]
    await async_client.post(
        f"/api/v1/citizen/applications/{journey.id}/clarifications/{r1_id}/respond",
        json={"response_text": "Round 1 response: Re-stamped document uploaded"},
        headers={"Authorization": f"Bearer {citizen_token}"},
    )

    # Round 2: Request & Respond
    resp_r2 = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evidence/{ev.id}/clarification",
        json={"reason": "Round 2: Tehsildar signature unverified in portal"},
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    r2_id = resp_r2.json()["id"]
    assert resp_r2.json()["round"] == 2

    await async_client.post(
        f"/api/v1/citizen/applications/{journey.id}/clarifications/{r2_id}/respond",
        json={"response_text": "Round 2 response: Attached digital certificate with QR code"},
        headers={"Authorization": f"Bearer {citizen_token}"},
    )

    # Round 3: Officer now VERIFIES the evidence
    resp_verify = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evidence/{ev.id}/verify",
        json={"action": "VERIFY", "notes": "Satisfied with Round 2 QR verification."},
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    assert resp_verify.status_code == 200

    # Retrieve verification history
    resp_hist = await async_client.get(
        f"/api/v1/officer/cases/{journey.id}/verification-history",
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    assert resp_hist.status_code == 200
    hist = resp_hist.json()
    assert hist["journey_id"] == str(journey.id)
    assert hist["current_round"] == 2
    assert len(hist["clarification_requests"]) == 2
    assert hist["clarification_requests"][0]["round"] == 1
    assert hist["clarification_requests"][1]["round"] == 2
    # Verify audit events logged for all rounds
    actions = [e["action"] for e in hist["audit_events"]]
    assert "CLARIFICATION_REQUESTED" in actions
    assert "CLARIFICATION_RESPONDED" in actions
    assert "EVIDENCE_VERIFIED" in actions


# ==============================================================================
# 5. Verification Completeness & Transition to READY_FOR_EVALUATION Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_verification_completeness_and_ready_for_evaluation(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verify that when all policy-bound mandatory evidence items are verified, journey transitions to READY_FOR_EVALUATION."""
    journey, citizen, claims, evidence_items = await _create_test_journey_with_evidence(
        db_session,
        evidence_types=["LAND_RECORD", "AADHAAR", "BANK_PASSBOOK"],
    )
    journey_id = journey.id
    ev1_id = evidence_items[0].id
    ev2_id = evidence_items[1].id
    ev3_id = evidence_items[2].id

    officer_token = _make_officer_token()
    headers = {"Authorization": f"Bearer {officer_token}"}

    # Initially: VERIFICATION_IN_PROGRESS (all 3 pending)
    status_init = await compute_verification_status(db_session, journey_id)
    assert status_init["verification_status"] == VerificationCompleteness.VERIFICATION_IN_PROGRESS.value
    assert len(status_init["missing_mandatory_requirements"]) == 0
    assert len(status_init["pending_mandatory_requirements"]) == 3
    assert status_init["is_ready_for_evaluation"] is False

    # Verify first evidence item (LAND_RECORD)
    resp_ev1 = await async_client.post(
        f"/api/v1/officer/cases/{journey_id}/evidence/{ev1_id}/verify",
        json={"action": "VERIFY"},
        headers=headers,
    )
    assert resp_ev1.status_code == 200

    # Journey still in VERIFICATION_IN_PROGRESS
    stmt_j = select(EvaluationJourney).where(EvaluationJourney.id == journey_id)
    j_mid1 = (await db_session.execute(stmt_j)).scalar_one()
    assert j_mid1.state == JourneyState.VERIFICATION_IN_PROGRESS

    # Verify second evidence item (AADHAAR)
    resp_ev2 = await async_client.post(
        f"/api/v1/officer/cases/{journey_id}/evidence/{ev2_id}/verify",
        json={"action": "VERIFY"},
        headers=headers,
    )
    assert resp_ev2.status_code == 200

    # Journey still in VERIFICATION_IN_PROGRESS (BANK_PASSBOOK still pending)
    db_session.expire_all()
    j_mid2 = (await db_session.execute(stmt_j)).scalar_one()
    assert j_mid2.state == JourneyState.VERIFICATION_IN_PROGRESS

    # Verify third evidence item (BANK_PASSBOOK) -> All mandatory satisfied and verified!
    resp_ev3 = await async_client.post(
        f"/api/v1/officer/cases/{journey_id}/evidence/{ev3_id}/verify",
        json={"action": "VERIFY"},
        headers=headers,
    )
    assert resp_ev3.status_code == 200

    # Journey automatically transitions to READY_FOR_EVALUATION
    db_session.expire_all()
    j_final = (await db_session.execute(stmt_j)).scalar_one()
    assert j_final.state == JourneyState.READY_FOR_EVALUATION

    # Audit event logged
    stmt_audit = select(HumanReviewAuditEvent).where(
        HumanReviewAuditEvent.journey_id == journey.id,
        HumanReviewAuditEvent.action == "VERIFICATION_COMPLETED",
    )
    audit = (await db_session.execute(stmt_audit)).scalars().first()
    assert audit is not None


# ==============================================================================
# 6. Security & Role Matrix Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_security_authorization_matrix(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verify 401 for unauthenticated and 403 for unauthorized role access."""
    journey, citizen, claims, evidence_items = await _create_test_journey_with_evidence(
        db_session
    )
    ev = evidence_items[0]

    # 1. Unauthenticated requests -> 401
    resp_unauth_officer = await async_client.get(f"/api/v1/officer/cases/{journey.id}/evidence")
    assert resp_unauth_officer.status_code == 401

    resp_unauth_citizen = await async_client.get(
        f"/api/v1/citizen/applications/{journey.id}/clarifications"
    )
    assert resp_unauth_citizen.status_code == 401

    # 2. Citizen token on officer endpoint -> 403
    citizen_token = _make_citizen_token()
    resp_cit_on_off = await async_client.get(
        f"/api/v1/officer/cases/{journey.id}/evidence",
        headers={"Authorization": f"Bearer {citizen_token}"},
    )
    assert resp_cit_on_off.status_code == 403

    # 3. Officer token on citizen endpoint -> 403
    officer_token = _make_officer_token()
    resp_off_on_cit = await async_client.get(
        f"/api/v1/citizen/applications/{journey.id}/clarifications",
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    assert resp_off_on_cit.status_code == 403


# ==============================================================================
# 7. Remediation Finding 1 — Policy-Bound Verification Completeness Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_completeness_missing_mandatory_evidence_prevents_ready_for_evaluation(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verify missing mandatory evidence items prevent transition to READY_FOR_EVALUATION."""
    # Only 1 mandatory evidence attached (LAND_RECORD); AADHAAR and BANK_PASSBOOK missing
    journey, citizen, claims, evidence_items = await _create_test_journey_with_evidence(
        db_session,
        evidence_types=["LAND_RECORD"],
    )
    journey_id = journey.id
    ev = evidence_items[0]
    officer_token = _make_officer_token()
    headers = {"Authorization": f"Bearer {officer_token}"}

    # Verify the only attached evidence item
    resp = await async_client.post(
        f"/api/v1/officer/cases/{journey_id}/evidence/{ev.id}/verify",
        json={"action": "VERIFY", "notes": "Land record verified."},
        headers=headers,
    )
    assert resp.status_code == 200

    # Verification completeness status
    db_session.expire_all()
    status_diag = await compute_verification_status(db_session, journey_id)
    assert status_diag["is_ready_for_evaluation"] is False
    assert status_diag["verification_status"] == VerificationCompleteness.VERIFICATION_IN_PROGRESS.value
    assert "AADHAAR" in status_diag["missing_mandatory_requirements"]
    assert "BANK_PASSBOOK" in status_diag["missing_mandatory_requirements"]
    assert "LAND_RECORD" in status_diag["satisfied_mandatory_requirements"]

    # Journey state MUST remain in VERIFICATION_IN_PROGRESS
    stmt_j = select(EvaluationJourney).where(EvaluationJourney.id == journey_id)
    j = (await db_session.execute(stmt_j)).scalar_one()
    assert j.state == JourneyState.VERIFICATION_IN_PROGRESS


@pytest.mark.asyncio
async def test_completeness_pending_mandatory_evidence_prevents_ready_for_evaluation(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verify that when mandatory evidence is pending verification, readiness is denied."""
    journey, citizen, claims, evidence_items = await _create_test_journey_with_evidence(
        db_session,
        evidence_types=["LAND_RECORD", "AADHAAR", "BANK_PASSBOOK"],
    )
    journey_id = journey.id
    officer_token = _make_officer_token()
    headers = {"Authorization": f"Bearer {officer_token}"}

    # Verify LAND_RECORD and AADHAAR, leave BANK_PASSBOOK pending
    await async_client.post(
        f"/api/v1/officer/cases/{journey_id}/evidence/{evidence_items[0].id}/verify",
        json={"action": "VERIFY"},
        headers=headers,
    )
    await async_client.post(
        f"/api/v1/officer/cases/{journey_id}/evidence/{evidence_items[1].id}/verify",
        json={"action": "VERIFY"},
        headers=headers,
    )

    db_session.expire_all()
    status_diag = await compute_verification_status(db_session, journey_id)
    assert status_diag["is_ready_for_evaluation"] is False
    assert status_diag["verification_status"] == VerificationCompleteness.VERIFICATION_IN_PROGRESS.value
    assert "BANK_PASSBOOK" in status_diag["pending_mandatory_requirements"]
    assert len(status_diag["satisfied_mandatory_requirements"]) == 2

    stmt_j = select(EvaluationJourney).where(EvaluationJourney.id == journey_id)
    j = (await db_session.execute(stmt_j)).scalar_one()
    assert j.state == JourneyState.VERIFICATION_IN_PROGRESS


@pytest.mark.asyncio
async def test_completeness_rejected_mandatory_evidence_blocks_evaluation(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verify rejected mandatory evidence transitions journey to VERIFICATION_BLOCKED."""
    journey, citizen, claims, evidence_items = await _create_test_journey_with_evidence(
        db_session,
        evidence_types=["LAND_RECORD", "AADHAAR", "BANK_PASSBOOK"],
    )
    journey_id = journey.id
    officer_token = _make_officer_token()
    headers = {"Authorization": f"Bearer {officer_token}"}

    # Reject LAND_RECORD with mandatory reason
    resp = await async_client.post(
        f"/api/v1/officer/cases/{journey_id}/evidence/{evidence_items[0].id}/verify",
        json={"action": "REJECT", "reason": "Fraudulent deed suspected; seal counterfeit.", "notes": "Fraudulent deed"},
        headers=headers,
    )
    assert resp.status_code == 200

    db_session.expire_all()
    status_diag = await compute_verification_status(db_session, journey_id)
    assert status_diag["is_ready_for_evaluation"] is False
    assert status_diag["verification_status"] == VerificationCompleteness.VERIFICATION_BLOCKED.value
    assert "LAND_RECORD" in status_diag["rejected_mandatory_requirements"]

    stmt_j = select(EvaluationJourney).where(EvaluationJourney.id == journey_id)
    j = (await db_session.execute(stmt_j)).scalar_one()
    assert j.state != JourneyState.READY_FOR_EVALUATION


@pytest.mark.asyncio
async def test_completeness_clarification_mandatory_evidence_requires_clarification(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verify clarification request on mandatory evidence sets CLARIFICATION_REQUIRED."""
    journey, citizen, claims, evidence_items = await _create_test_journey_with_evidence(
        db_session,
        evidence_types=["LAND_RECORD", "AADHAAR", "BANK_PASSBOOK"],
    )
    journey_id = journey.id
    officer_token = _make_officer_token()
    headers = {"Authorization": f"Bearer {officer_token}"}

    # Request clarification on AADHAAR
    resp = await async_client.post(
        f"/api/v1/officer/cases/{journey_id}/evidence/{evidence_items[1].id}/clarification",
        json={"reason": "Aadhaar photo is blurred, please upload clear scan."},
        headers=headers,
    )
    assert resp.status_code == 200

    db_session.expire_all()
    status_diag = await compute_verification_status(db_session, journey_id)
    assert status_diag["is_ready_for_evaluation"] is False
    assert status_diag["verification_status"] == VerificationCompleteness.CLARIFICATION_REQUIRED.value
    assert "AADHAAR" in status_diag["clarification_mandatory_requirements"]

    stmt_j = select(EvaluationJourney).where(EvaluationJourney.id == journey_id)
    j = (await db_session.execute(stmt_j)).scalar_one()
    assert j.state == JourneyState.ACTION_REQUIRED


@pytest.mark.asyncio
async def test_completeness_optional_evidence_cannot_satisfy_mandatory_requirement(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verify that verifying non-mandatory evidence does not satisfy missing mandatory requirements."""
    journey, citizen, claims, evidence_items = await _create_test_journey_with_evidence(
        db_session,
        evidence_types=["LAND_RECORD", "PENSION_SLIP"],
    )
    journey_id = journey.id
    officer_token = _make_officer_token()
    headers = {"Authorization": f"Bearer {officer_token}"}

    # Verify both attached items
    for ev in evidence_items:
        resp = await async_client.post(
            f"/api/v1/officer/cases/{journey_id}/evidence/{ev.id}/verify",
            json={"action": "VERIFY"},
            headers=headers,
        )
        assert resp.status_code == 200

    # Even though all attached items are VERIFIED, AADHAAR and BANK_PASSBOOK are missing
    db_session.expire_all()
    status_diag = await compute_verification_status(db_session, journey_id)
    assert status_diag["is_ready_for_evaluation"] is False
    assert status_diag["verification_status"] == VerificationCompleteness.VERIFICATION_IN_PROGRESS.value
    assert "AADHAAR" in status_diag["missing_mandatory_requirements"]
    assert "BANK_PASSBOOK" in status_diag["missing_mandatory_requirements"]

    stmt_j = select(EvaluationJourney).where(EvaluationJourney.id == journey_id)
    j = (await db_session.execute(stmt_j)).scalar_one()
    assert j.state == JourneyState.VERIFICATION_IN_PROGRESS


@pytest.mark.asyncio
async def test_completeness_bound_policy_version_immutability(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verify completeness is strictly evaluated against journey's bound policy_version_id."""
    journey, citizen, claims, evidence_items = await _create_test_journey_with_evidence(
        db_session,
        evidence_types=["LAND_RECORD", "AADHAAR", "BANK_PASSBOOK"],
    )
    journey_id = journey.id
    status_diag = await compute_verification_status(db_session, journey_id)
    assert status_diag["bound_policy_version_id"] == str(journey.policy_version_id)
    assert status_diag["mandatory_requirements"] == ["LAND_RECORD", "AADHAAR", "BANK_PASSBOOK"]


# ==============================================================================
# 8. Remediation Finding 2 — Officer Case Assignment Ownership Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_officer_assignment_ownership_assigned_officer_permitted(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verify that the designated assigned officer is permitted to verify and clarify."""
    assigned_email = "officer.designated@yogyatamitra.local"
    journey, citizen, claims, evidence_items = await _create_test_journey_with_evidence(
        db_session,
        assigned_officer_email=assigned_email,
        evidence_types=["LAND_RECORD"],
    )
    journey_id = journey.id
    ev = evidence_items[0]

    token = _make_officer_token(email=assigned_email, role="OFFICER")
    headers = {"Authorization": f"Bearer {token}"}

    # Verify action permitted
    resp_v = await async_client.post(
        f"/api/v1/officer/cases/{journey_id}/evidence/{ev.id}/verify",
        json={"action": "VERIFY", "notes": "Permitted action by assigned officer."},
        headers=headers,
    )
    assert resp_v.status_code == 200


@pytest.mark.asyncio
async def test_officer_assignment_ownership_peer_officer_forbidden_403(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verify that a different regular officer is denied access with HTTP 403."""
    assigned_email = "officer.owner@yogyatamitra.local"
    peer_email = "officer.intruder@yogyatamitra.local"

    journey, citizen, claims, evidence_items = await _create_test_journey_with_evidence(
        db_session,
        assigned_officer_email=assigned_email,
        evidence_types=["LAND_RECORD"],
    )
    journey_id = journey.id
    ev = evidence_items[0]

    peer_token = _make_officer_token(email=peer_email, role="OFFICER")
    peer_headers = {"Authorization": f"Bearer {peer_token}"}

    # 1. Peer attempts verify -> 403 Forbidden
    resp_v = await async_client.post(
        f"/api/v1/officer/cases/{journey_id}/evidence/{ev.id}/verify",
        json={"action": "VERIFY"},
        headers=peer_headers,
    )
    assert resp_v.status_code == 403
    assert "assigned to another officer" in resp_v.text.lower()

    # 2. Peer attempts clarification -> 403 Forbidden
    resp_c = await async_client.post(
        f"/api/v1/officer/cases/{journey_id}/evidence/{ev.id}/clarification",
        json={"reason": "Unauthorized clarification attempt"},
        headers=peer_headers,
    )
    assert resp_c.status_code == 403
    assert "assigned to another officer" in resp_c.text.lower()

    # 3. Peer attempts review -> 403 Forbidden
    resp_r = await async_client.post(
        f"/api/v1/officer/cases/{journey_id}/review",
        json={"decision": "VERIFIED", "notes": "Unauthorized review attempt"},
        headers=peer_headers,
    )
    assert resp_r.status_code == 403
    assert "assigned to another officer" in resp_r.text.lower()


@pytest.mark.asyncio
async def test_officer_assignment_ownership_unassigned_case_forbidden_403(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verify that a regular officer cannot act on an unassigned case (HTTP 403)."""
    journey, citizen, claims, evidence_items = await _create_test_journey_with_evidence(
        db_session,
        assigned_officer_email=None,  # No active assignment
        evidence_types=["LAND_RECORD"],
    )
    journey_id = journey.id
    ev = evidence_items[0]

    officer_token = _make_officer_token(email="officer.random@yogyatamitra.local", role="OFFICER")
    headers = {"Authorization": f"Bearer {officer_token}"}

    resp = await async_client.post(
        f"/api/v1/officer/cases/{journey_id}/evidence/{ev.id}/verify",
        json={"action": "VERIFY"},
        headers=headers,
    )
    assert resp.status_code == 403
    assert "not assigned to you" in resp.text.lower()


@pytest.mark.asyncio
async def test_officer_assignment_ownership_supervisor_and_admin_permitted(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verify that SUPERVISOR and ADMIN roles can act even if not the active assignee."""
    assigned_email = "officer.worker@yogyatamitra.local"
    journey, citizen, claims, evidence_items = await _create_test_journey_with_evidence(
        db_session,
        assigned_officer_email=assigned_email,
        evidence_types=["LAND_RECORD", "AADHAAR"],
    )
    journey_id = journey.id
    ev1_id = evidence_items[0].id
    ev2_id = evidence_items[1].id

    # 1. Supervisor acts on ev1
    sup_token = _make_officer_token(email="supervisor@yogyatamitra.local", role="SUPERVISOR")
    resp_sup = await async_client.post(
        f"/api/v1/officer/cases/{journey_id}/evidence/{ev1_id}/verify",
        json={"action": "VERIFY", "notes": "Verified by supervisor override."},
        headers={"Authorization": f"Bearer {sup_token}"},
    )
    assert resp_sup.status_code == 200
    assert resp_sup.json()["status"] == "VERIFIED"

    # 2. Admin acts on ev2 (clarification)
    admin_token = _make_officer_token(email="admin@yogyatamitra.local", role="ADMIN")
    resp_adm = await async_client.post(
        f"/api/v1/officer/cases/{journey_id}/evidence/{ev2_id}/clarification",
        json={"reason": "Admin requires additional documentation"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_adm.status_code == 200
    assert resp_adm.json()["status"] == "OPEN"

    # Verify evidence status was updated to CLARIFICATION_REQUIRED
    db_session.expire_all()
    stmt_ev2 = select(Evidence).where(Evidence.id == ev2_id)
    ev2_reloaded = (await db_session.execute(stmt_ev2)).scalar_one()
    assert ev2_reloaded.status == EvidenceStatus.CLARIFICATION_REQUIRED


@pytest.mark.asyncio
async def test_officer_assignment_ownership_no_database_mutation_on_403(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verify that a rejected 403 request does not mutate evidence, claims, or audit logs."""
    assigned_email = "officer.legit@yogyatamitra.local"
    attacker_email = "officer.attacker@yogyatamitra.local"

    journey, citizen, claims, evidence_items = await _create_test_journey_with_evidence(
        db_session,
        assigned_officer_email=assigned_email,
        evidence_types=["LAND_RECORD"],
    )
    journey_id = journey.id
    ev_id = evidence_items[0].id
    claim_id = claims[0].id

    attacker_token = _make_officer_token(email=attacker_email, role="OFFICER")
    resp = await async_client.post(
        f"/api/v1/officer/cases/{journey_id}/evidence/{ev_id}/verify",
        json={"action": "VERIFY", "notes": "Illegitimate verification attempt"},
        headers={"Authorization": f"Bearer {attacker_token}"},
    )
    assert resp.status_code == 403

    # Assert database state remains clean and untouched
    db_session.expire_all()
    stmt_ev = select(Evidence).where(Evidence.id == ev_id)
    ev_reloaded = (await db_session.execute(stmt_ev)).scalar_one()
    assert ev_reloaded.status == EvidenceStatus.PENDING

    stmt_claim = select(Claim).where(Claim.id == claim_id)
    claim_reloaded = (await db_session.execute(stmt_claim)).scalar_one()
    assert claim_reloaded.status == ClaimStatus.PENDING

    # Assert no VerificationRecord was created
    stmt_vr = select(VerificationRecord).where(VerificationRecord.evidence_id == ev_id)
    vr = (await db_session.execute(stmt_vr)).scalars().first()
    assert vr is None

    # Assert no HumanReviewAuditEvent was logged for this unauthorized attempt
    stmt_audit = select(HumanReviewAuditEvent).where(
        HumanReviewAuditEvent.journey_id == journey_id,
        HumanReviewAuditEvent.actor_identity == attacker_email,
    )
    audit = (await db_session.execute(stmt_audit)).scalars().first()
    assert audit is None
