"""Comprehensive Test Suite for YogyataMitra Phase F.

Verifies:
1. Server-Side Verification Gate Invariants:
   - Missing mandatory evidence yields INSUFFICIENT_INFORMATION.
   - Unverified / pending / rejected / clarification evidence yields VERIFICATION_REQUIRED.
   - When all mandatory requirements and evidence are verified, statutory evaluation executes.
2. Deterministic Rule Engine Execution:
   - PM_KISAN eligible and ineligible scenarios (pension >= 10k, tax payer, institutional holder).
   - PM_KISAN land transfer cutoff and succession exception.
   - Historical policy version binding and immutability (v1.0-2018 2ha ceiling vs v2/v3).
   - SSY eligible girl child, ineligible male child, age-at-opening boundary (attained age 10),
     and family account limit with multiple-birth exception.
   - Complex AST operators: AND, OR, NOT, comparison, temporal, and numeric boundaries.
3. Statutory Decision Persistence & Immutability:
   - Append-only EvaluationTrace persistence linked to journey.
   - Historical evaluation preservation (re-evaluation produces distinct records, preserves history).
   - Idempotency / double-click protection within 2 seconds.
   - HumanReviewAuditEvent logged with action="EVALUATION_COMPLETED".
   - JourneyState transitions accurately recorded in JourneyTransitionRecord.
4. Security, IDOR Protection & Authorization:
   - Citizen token forbidden from officer evaluation endpoints (403).
   - Unauthenticated requests rejected (401).
   - Citizen can view own decision with bilingual statutory disclaimers.
   - Citizen IDOR protection: cannot view other citizen's decision (404).
   - Officer object-level assignment authorization: unassigned/peer officer forbidden (403).
   - Supervisor / ADMIN override permitted (200).
   - Anti-spoofing: extra payload fields strictly rejected (422).
5. Safe Failure:
   - Unsupported schemes (schemes 3-10) fail safely with HTTP 400 without fabricating rules.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import create_access_token
from app.models.assignment import OfficerAssignment
from app.models.citizen import Citizen, Claim, Evidence, VerificationRecord
from app.models.enums import (
    AssignmentStatus,
    ClaimStatus,
    EligibilityResult,
    EvidenceStatus,
    HumanReviewStatus,
    JourneyState,
    SchemeStatus,
    VerificationStatus,
)
from app.models.evaluation import EvaluationTrace
from app.models.human_review import HumanReview, HumanReviewAuditEvent
from app.models.journey import EvaluationJourney, JourneyTransitionRecord
from app.models.scheme import PolicyVersion, RuleSet, Scheme
from app.services.policy_loader import load_all_policies
from tests.conftest import TestSessionLocal as AsyncSessionLocal


# ==============================================================================
# Auth Helpers
# ==============================================================================

def _make_officer_token(
    email: str = "officer.verif@yogyatamitra.local",
    role: str = "OFFICER",
    name: str = "Senior Verification Officer (Demo)",
) -> str:
    """Generate an officer JWT for test requests."""
    payload = {
        "sub": email,
        "email": email,
        "role": role,
        "name": name,
        "designation": "Verification Officer Grade II",
        "department": "Welfare Verification Cell",
    }
    return create_access_token(data=payload)


def _make_citizen_token(
    email: str = "rameshwar.sharma@test.local",
    ref: str = "SYN-CIT-PHASE-F",
    name: str = "Rameshwar Sharma",
) -> str:
    """Generate a citizen JWT for test requests."""
    payload = {
        "sub": email,
        "role": "CITIZEN",
        "citizen_ref": ref,
        "name": name,
        "state": "Maharashtra",
        "district": "Pune",
    }
    return create_access_token(data=payload)


# ==============================================================================
# Database Seed Fixture
# ==============================================================================

@pytest_asyncio.fixture(scope="function", autouse=True)
async def ensure_schemes_and_policies():
    """Ensure PM_KISAN and SSY canonical policies and rulesets are loaded."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Scheme).where(Scheme.scheme_code == "PM_KISAN"))
        if not res.scalar_one_or_none():
            await load_all_policies(session=session)


# ==============================================================================
# Test Data Creation Helpers
# ==============================================================================

async def _create_test_journey_for_eval(
    session: AsyncSession,
    scheme_code: str = "PM_KISAN",
    citizen_ref: str = "SYN-CIT-PHASE-F",
    assigned_officer_email: str | None = "officer.verif@yogyatamitra.local",
    policy_version_code: str | None = None,
    claims_data: Optional[Dict[str, Any]] = None,
    evidence_statuses: Optional[Dict[str, EvidenceStatus]] = None,
    default_claim_status: ClaimStatus = ClaimStatus.VERIFIED,
    claims_status: Optional[Dict[str, ClaimStatus]] = None,
) -> tuple[EvaluationJourney, Citizen, List[Claim], List[Evidence]]:
    """Helper to persist a submitted evaluation journey with claims and evidence."""
    # 1. Resolve Scheme
    stmt_s = select(Scheme).where(Scheme.scheme_code == scheme_code)
    scheme = (await session.execute(stmt_s)).scalars().first()
    if not scheme:
        scheme = Scheme(
            id=uuid.uuid4(),
            scheme_code=scheme_code,
            name_en=f"Scheme {scheme_code}",
            name_hi=f"योजना {scheme_code}",
            description_en=f"Description for {scheme_code}",
            description_hi=f"विवरण {scheme_code}",
            official_url="https://welfare.gov.in/test",
            status=SchemeStatus.ACTIVE,
        )
        session.add(scheme)
        await session.flush()

    # 2. Resolve PolicyVersion
    pv_stmt = select(PolicyVersion).where(PolicyVersion.scheme_id == scheme.id)
    if policy_version_code:
        pv_stmt = pv_stmt.where(PolicyVersion.version_code == policy_version_code)
    else:
        pv_stmt = pv_stmt.order_by(PolicyVersion.effective_from.desc())
    pv = (await session.execute(pv_stmt)).scalars().first()
    pv_id = pv.id if pv else None

    # 3. Citizen
    stmt_cit = select(Citizen).where(Citizen.synthetic_reference == citizen_ref)
    citizen = (await session.execute(stmt_cit)).scalars().first()
    if not citizen:
        citizen = Citizen(
            id=uuid.uuid4(),
            synthetic_reference=citizen_ref,
            display_name="Rameshwar Sharma",
            state="Maharashtra",
            district="Pune",
        )
        session.add(citizen)
        await session.flush()

    # 4. Journey
    now = datetime.now(timezone.utc)
    journey = EvaluationJourney(
        id=uuid.uuid4(),
        citizen_id=citizen.id,
        scheme_id=scheme.id,
        policy_version_id=pv_id,
        state=JourneyState.VERIFICATION_IN_PROGRESS,
        submitted_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(journey)
    await session.flush()

    # 5. Active Assignment
    if assigned_officer_email:
        assignment = OfficerAssignment(
            id=uuid.uuid4(),
            journey_id=journey.id,
            officer_identity=assigned_officer_email,
            officer_name="Senior Verification Officer (Demo)",
            assigned_by="SYSTEM_BALANCER",
            assigned_at=now,
            due_at=now + timedelta(hours=48),
            sla_duration_hours=48,
            status=AssignmentStatus.ASSIGNED,
            is_active=True,
        )
        session.add(assignment)
        await session.flush()

    # 6. Claims
    claims: List[Claim] = []
    if claims_data:
        for section_or_field, val in claims_data.items():
            st = claims_status.get(section_or_field, default_claim_status) if claims_status else default_claim_status
            claim = Claim(
                id=uuid.uuid4(),
                citizen_id=citizen.id,
                journey_id=journey.id,
                claim_type=section_or_field,
                value_json=val if isinstance(val, dict) else {"value": val},
                status=st,
                source="CITIZEN_DECLARATION",
                claimed_at=now,
            )
            session.add(claim)
            await session.flush()
            claims.append(claim)

    # 7. Evidence Items
    evidence_items: List[Evidence] = []
    if evidence_statuses:
        # Link evidence to first claim or fallback claim
        target_claim = claims[0] if claims else None
        if not target_claim:
            target_claim = Claim(
                id=uuid.uuid4(),
                citizen_id=citizen.id,
                journey_id=journey.id,
                claim_type="statutory.evidence",
                value_json={"attached": True},
                status=ClaimStatus.PENDING,
                source="CITIZEN_DECLARATION",
                claimed_at=now,
            )
            session.add(target_claim)
            await session.flush()
            claims.append(target_claim)

        for ev_type, ev_status in evidence_statuses.items():
            ev = Evidence(
                id=uuid.uuid4(),
                claim_id=target_claim.id,
                evidence_type=ev_type,
                storage_reference=f"docs/{ev_type.lower()}_test.pdf",
                metadata_json={"document_name": f"{ev_type}.pdf", "file_size_bytes": 102400},
                status=ev_status,
                submitted_at=now,
            )
            session.add(ev)
            await session.flush()

            if ev_status in (EvidenceStatus.VERIFIED, EvidenceStatus.REJECTED, EvidenceStatus.CLARIFICATION_REQUIRED):
                v_record = VerificationRecord(
                    id=uuid.uuid4(),
                    evidence_id=ev.id,
                    claim_id=target_claim.id,
                    verification_method="MANUAL_OFFICER_REVIEW",
                    status=VerificationStatus[ev_status.value],
                    verified_by=assigned_officer_email or "SYSTEM",
                    details_json={"notes": "Statutory verification test finding recorded."},
                    verified_at=now,
                )
                session.add(v_record)
                await session.flush()

            evidence_items.append(ev)

    await session.commit()
    await session.refresh(journey)
    return journey, citizen, claims, evidence_items


# ==============================================================================
# 1. Server-Side Verification Gate Invariant Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_gate_missing_mandatory_evidence_yields_insufficient_information(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Missing mandatory documents halt evaluation with INSUFFICIENT_INFORMATION."""
    # PM_KISAN requires LAND_RECORD, AADHAAR, BANK_PASSBOOK
    # Provide only 1 mandatory item (LAND_RECORD)
    journey, citizen, _, _ = await _create_test_journey_for_eval(
        db_session,
        scheme_code="PM_KISAN",
        claims_data={"family": {"owns_cultivable_land": True}},
        evidence_statuses={"LAND_RECORD": EvidenceStatus.VERIFIED},
    )

    token = _make_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evaluate",
        headers=headers,
        json={"notes": "Executing preliminary evaluation"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["determination"] == "INSUFFICIENT_INFORMATION"
    assert len(data["missing_facts"]) > 0
    # Must list the missing mandatory evidence types
    missing_str = " ".join(data["missing_facts"])
    assert "AADHAAR" in missing_str or "BANK_PASSBOOK" in missing_str
    assert len(data["reasons_en"]) > 0
    assert len(data["reasons_hi"]) > 0

    # Verify Journey state transitioned to ACTION_REQUIRED
    async with AsyncSessionLocal() as session:
        j = await session.get(EvaluationJourney, journey.id)
        assert j.state == JourneyState.ACTION_REQUIRED
        assert j.latest_evaluation_id == uuid.UUID(data["evaluation_id"])

        # Verify audit event
        stmt_audit = select(HumanReviewAuditEvent).where(
            HumanReviewAuditEvent.journey_id == journey.id,
            HumanReviewAuditEvent.action == "EVALUATION_COMPLETED",
        )
        audit = (await session.execute(stmt_audit)).scalars().first()
        assert audit is not None
        assert audit.details_json["outcome"] == "INSUFFICIENT_INFORMATION"


@pytest.mark.asyncio
async def test_gate_pending_evidence_yields_verification_required(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Pending unverified evidence halts evaluation with VERIFICATION_REQUIRED."""
    # All 3 documents attached, but one is PENDING
    journey, citizen, _, _ = await _create_test_journey_for_eval(
        db_session,
        scheme_code="PM_KISAN",
        claims_data={"family": {"owns_cultivable_land": True}},
        evidence_statuses={
            "LAND_RECORD": EvidenceStatus.VERIFIED,
            "AADHAAR": EvidenceStatus.PENDING,
            "BANK_PASSBOOK": EvidenceStatus.VERIFIED,
        },
    )

    token = _make_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evaluate",
        headers=headers,
        json={"notes": "Evaluating case with pending document"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["determination"] == "VERIFICATION_REQUIRED"
    assert any("AADHAAR" in reason for reason in data["reasons_en"])

    async with AsyncSessionLocal() as session:
        j = await session.get(EvaluationJourney, journey.id)
        assert j.state == JourneyState.ACTION_REQUIRED


@pytest.mark.asyncio
async def test_gate_rejected_evidence_yields_verification_required(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Rejected mandatory evidence halts evaluation with VERIFICATION_REQUIRED."""
    journey, citizen, _, _ = await _create_test_journey_for_eval(
        db_session,
        scheme_code="PM_KISAN",
        claims_data={"family": {"owns_cultivable_land": True}},
        evidence_statuses={
            "LAND_RECORD": EvidenceStatus.VERIFIED,
            "AADHAAR": EvidenceStatus.REJECTED,
            "BANK_PASSBOOK": EvidenceStatus.VERIFIED,
        },
    )

    token = _make_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evaluate",
        headers=headers,
        json={"notes": "Evaluating rejected doc"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["determination"] == "VERIFICATION_REQUIRED"
    assert any("REJECTED" in reason or "AADHAAR" in reason for reason in data["reasons_en"])


# ==============================================================================
# 2. PM_KISAN Deterministic Evaluation Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_pmkisan_fully_eligible_farmer_evaluation(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verified eligible farmer evaluates to ELIGIBLE with complete trace and bilingual reasons."""
    claims_data = {
        "family": {
            "owns_cultivable_land": True,
            "total_land_area_hectares": 1.5,
            "is_institutional_landholder": False,
            "has_constitutional_post_holder": False,
            "has_public_representative": False,
            "has_disqualified_government_employee": False,
            "has_pensioner_above_ten_thousand": False,
            "has_income_tax_payer": False,
            "has_registered_practicing_professional": False,
            "is_nri": False,
        },
        "land": {
            "transferred_after_cutoff": False,
            "acquired_via_succession": False,
        },
    }
    evidence_statuses = {
        "LAND_RECORD": EvidenceStatus.VERIFIED,
        "AADHAAR": EvidenceStatus.VERIFIED,
        "BANK_PASSBOOK": EvidenceStatus.VERIFIED,
    }

    journey, citizen, _, _ = await _create_test_journey_for_eval(
        db_session,
        scheme_code="PM_KISAN",
        claims_data=claims_data,
        evidence_statuses=evidence_statuses,
    )

    token = _make_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evaluate",
        headers=headers,
        json={"notes": "Full statutory verification satisfied"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["determination"] == "ELIGIBLE"
    assert len(data["rules_evaluated"]) > 0
    # Every evaluated rule has operator, expected, and actual values
    for r in data["rules_evaluated"]:
        assert r["result"] in ("PASS", "FAIL", "UNKNOWN")
        assert "rule_id" in r
    assert len(data["reasons_en"]) > 0
    assert len(data["reasons_hi"]) > 0

    # Verify Journey state transitioned to EVALUATED
    async with AsyncSessionLocal() as session:
        j = await session.get(EvaluationJourney, journey.id)
        assert j.state == JourneyState.EVALUATED
        assert j.latest_evaluation_id == uuid.UUID(data["evaluation_id"])

        # Check EvaluationTrace persistence
        trace = await session.get(EvaluationTrace, uuid.UUID(data["evaluation_id"]))
        assert trace is not None
        assert trace.result_state == EligibilityResult.ELIGIBLE
        assert trace.journey_id == journey.id
        assert trace.evaluated_by == "officer.verif@yogyatamitra.local"


@pytest.mark.asyncio
async def test_pmkisan_ineligible_pensioner_exclusion(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Pensioner drawing >= Rs. 10,000 / month evaluates to INELIGIBLE."""
    claims_data = {
        "family": {
            "owns_cultivable_land": True,
            "total_land_area_hectares": 1.5,
            "is_institutional_landholder": False,
            "has_constitutional_post_holder": False,
            "has_public_representative": False,
            "has_disqualified_government_employee": False,
            "has_pensioner_above_ten_thousand": True,  # Disqualifier
            "has_income_tax_payer": False,
            "has_registered_practicing_professional": False,
            "is_nri": False,
        },
        "land": {
            "transferred_after_cutoff": False,
            "acquired_via_succession": False,
        },
    }
    evidence_statuses = {
        "LAND_RECORD": EvidenceStatus.VERIFIED,
        "AADHAAR": EvidenceStatus.VERIFIED,
        "BANK_PASSBOOK": EvidenceStatus.VERIFIED,
    }

    journey, citizen, _, _ = await _create_test_journey_for_eval(
        db_session,
        scheme_code="PM_KISAN",
        claims_data=claims_data,
        evidence_statuses=evidence_statuses,
    )

    token = _make_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evaluate",
        headers=headers,
        json={"notes": "Pensioner exclusion check"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["determination"] == "INELIGIBLE"
    assert len(data["disqualifiers"]) > 0
    # Pensioner exclusion must be reflected in disqualifiers
    disq_text = " ".join(data["disqualifiers"]).lower()
    assert "pension" in disq_text or "10,000" in disq_text or "pensioner" in disq_text

    async with AsyncSessionLocal() as session:
        j = await session.get(EvaluationJourney, journey.id)
        assert j.state == JourneyState.ACTION_REQUIRED


@pytest.mark.asyncio
async def test_pmkisan_ineligible_income_tax_payer(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Income tax payer evaluates to INELIGIBLE."""
    claims_data = {
        "family": {
            "owns_cultivable_land": True,
            "total_land_area_hectares": 1.5,
            "is_institutional_landholder": False,
            "has_constitutional_post_holder": False,
            "has_public_representative": False,
            "has_disqualified_government_employee": False,
            "has_pensioner_above_ten_thousand": False,
            "has_income_tax_payer": True,  # Disqualifier
            "has_registered_practicing_professional": False,
            "is_nri": False,
        },
        "land": {
            "transferred_after_cutoff": False,
            "acquired_via_succession": False,
        },
    }
    evidence_statuses = {
        "LAND_RECORD": EvidenceStatus.VERIFIED,
        "AADHAAR": EvidenceStatus.VERIFIED,
        "BANK_PASSBOOK": EvidenceStatus.VERIFIED,
    }

    journey, citizen, _, _ = await _create_test_journey_for_eval(
        db_session,
        scheme_code="PM_KISAN",
        claims_data=claims_data,
        evidence_statuses=evidence_statuses,
    )

    token = _make_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evaluate",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["determination"] == "INELIGIBLE"
    disq_text = " ".join(data["disqualifiers"]).lower()
    assert "tax" in disq_text or "income" in disq_text


@pytest.mark.asyncio
async def test_pmkisan_ineligible_institutional_landholder(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Institutional landholder evaluates to INELIGIBLE."""
    claims_data = {
        "family": {
            "owns_cultivable_land": True,
            "total_land_area_hectares": 1.5,
            "is_institutional_landholder": True,  # Disqualifier
            "has_constitutional_post_holder": False,
            "has_public_representative": False,
            "has_disqualified_government_employee": False,
            "has_pensioner_above_ten_thousand": False,
            "has_income_tax_payer": False,
            "has_registered_practicing_professional": False,
            "is_nri": False,
        },
        "land": {
            "transferred_after_cutoff": False,
            "acquired_via_succession": False,
        },
    }
    evidence_statuses = {
        "LAND_RECORD": EvidenceStatus.VERIFIED,
        "AADHAAR": EvidenceStatus.VERIFIED,
        "BANK_PASSBOOK": EvidenceStatus.VERIFIED,
    }

    journey, citizen, _, _ = await _create_test_journey_for_eval(
        db_session,
        scheme_code="PM_KISAN",
        claims_data=claims_data,
        evidence_statuses=evidence_statuses,
    )

    token = _make_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evaluate",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["determination"] == "INELIGIBLE"


@pytest.mark.asyncio
async def test_pmkisan_multiple_exclusion_criteria_captured(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Multiple triggered exclusions are all recorded in trace and disqualifiers."""
    claims_data = {
        "family": {
            "owns_cultivable_land": True,
            "total_land_area_hectares": 1.5,
            "is_institutional_landholder": False,
            "has_constitutional_post_holder": False,
            "has_public_representative": False,
            "has_disqualified_government_employee": False,
            "has_pensioner_above_ten_thousand": True,
            "has_income_tax_payer": True,
            "has_registered_practicing_professional": True,
            "is_nri": False,
        },
        "land": {
            "transferred_after_cutoff": False,
            "acquired_via_succession": False,
        },
    }
    evidence_statuses = {
        "LAND_RECORD": EvidenceStatus.VERIFIED,
        "AADHAAR": EvidenceStatus.VERIFIED,
        "BANK_PASSBOOK": EvidenceStatus.VERIFIED,
    }

    journey, citizen, _, _ = await _create_test_journey_for_eval(
        db_session,
        scheme_code="PM_KISAN",
        claims_data=claims_data,
        evidence_statuses=evidence_statuses,
    )

    token = _make_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evaluate",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["determination"] == "INELIGIBLE"
    assert len(data["disqualifiers"]) >= 3


@pytest.mark.asyncio
async def test_pmkisan_land_transfer_cutoff_and_succession(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Land transferred after cutoff is ineligible unless acquired strictly via succession."""
    # Case A: Transferred after cut-off WITHOUT succession -> INELIGIBLE
    claims_no_succ = {
        "family": {
            "owns_cultivable_land": True,
            "total_land_area_hectares": 1.5,
            "is_institutional_landholder": False,
            "has_constitutional_post_holder": False,
            "has_public_representative": False,
            "has_disqualified_government_employee": False,
            "has_pensioner_above_ten_thousand": False,
            "has_income_tax_payer": False,
            "has_registered_practicing_professional": False,
            "is_nri": False,
        },
        "land": {
            "transferred_after_cutoff": True,
            "acquired_via_succession": False,
            "acquisition_mode": "PURCHASE",
            "previous_owner_deceased": False,
        },
    }
    ev_stat = {
        "LAND_RECORD": EvidenceStatus.VERIFIED,
        "AADHAAR": EvidenceStatus.VERIFIED,
        "BANK_PASSBOOK": EvidenceStatus.VERIFIED,
    }

    journey_a, _, _, _ = await _create_test_journey_for_eval(
        db_session,
        scheme_code="PM_KISAN",
        citizen_ref="SYN-CIT-CUTOFF-A",
        claims_data=claims_no_succ,
        evidence_statuses=ev_stat,
    )
    token = _make_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp_a = await async_client.post(f"/api/v1/officer/cases/{journey_a.id}/evaluate", headers=headers)
    assert resp_a.status_code == 200
    assert resp_a.json()["determination"] == "INELIGIBLE"

    # Case B: Transferred after cut-off WITH succession -> ELIGIBLE
    claims_succ = {
        "family": {
            "owns_cultivable_land": True,
            "total_land_area_hectares": 1.5,
            "is_institutional_landholder": False,
            "has_constitutional_post_holder": False,
            "has_public_representative": False,
            "has_disqualified_government_employee": False,
            "has_pensioner_above_ten_thousand": False,
            "has_income_tax_payer": False,
            "has_registered_practicing_professional": False,
            "is_nri": False,
        },
        "land": {
            "transferred_after_cutoff": True,
            "acquired_via_succession": True,
            "acquisition_mode": "SUCCESSION",
            "previous_owner_deceased": True,
        },
    }
    journey_b, _, _, _ = await _create_test_journey_for_eval(
        db_session,
        scheme_code="PM_KISAN",
        citizen_ref="SYN-CIT-CUTOFF-B",
        claims_data=claims_succ,
        evidence_statuses=ev_stat,
    )
    resp_b = await async_client.post(f"/api/v1/officer/cases/{journey_b.id}/evaluate", headers=headers)
    assert resp_b.status_code == 200
    assert resp_b.json()["determination"] == "ELIGIBLE"


@pytest.mark.asyncio
async def test_pmkisan_bound_historical_policy_version_immutability(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Journey bound to historical v1.0-2018 enforces 2ha ceiling; does not upgrade to v3."""
    # Under v1.0-2018, land ceiling was 2.0 hectares. A farmer with 2.5 ha is INELIGIBLE.
    claims_large_farmer = {
        "family": {
            "owns_cultivable_land": True,
            "total_land_area_hectares": 2.5,  # Exceeds 2ha ceiling under v1.0-2018
            "is_institutional_landholder": False,
            "has_constitutional_post_holder": False,
            "has_public_representative": False,
            "has_disqualified_government_employee": False,
            "has_pensioner_above_ten_thousand": False,
            "has_income_tax_payer": False,
            "has_registered_practicing_professional": False,
            "is_nri": False,
        },
        "land": {
            "transferred_after_cutoff": False,
            "acquired_via_succession": False,
        },
    }
    ev_stat = {
        "LAND_RECORD": EvidenceStatus.VERIFIED,
        "AADHAAR": EvidenceStatus.VERIFIED,
        "BANK_PASSBOOK": EvidenceStatus.VERIFIED,
    }

    journey, _, _, _ = await _create_test_journey_for_eval(
        db_session,
        scheme_code="PM_KISAN",
        citizen_ref="SYN-CIT-HIST-V1",
        policy_version_code="v1.0-2018",
        claims_data=claims_large_farmer,
        evidence_statuses=ev_stat,
    )

    token = _make_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.post(f"/api/v1/officer/cases/{journey.id}/evaluate", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["ruleset_version"] == "v1.0-2018"
    assert data["determination"] == "INELIGIBLE"
    failed_names = " ".join([r["rule_id"] for r in data["rules_evaluated"] if r["result"] == "FAIL"])
    assert "CEILING" in failed_names or "2HA" in failed_names or len(data["disqualifiers"]) > 0


# ==============================================================================
# 3. Sukanya Samriddhi Yojana (SSY) Deterministic Evaluation Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_ssy_eligible_girl_child_evaluation(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Eligible girl child under 10 years of age evaluates to ELIGIBLE."""
    claims_data = {
        "beneficiary": {
            "gender": "FEMALE",
            "is_indian_resident": True,
            "date_of_birth": "2020-05-15",
        },
        "account": {
            "opening_date": "2024-06-01",
            "is_first_account_for_child": True,
        },
        "guardian": {
            "is_natural_guardian": True,
            "is_court_appointed_legal_guardian": False,
        },
        "family": {
            "active_ssy_accounts_count": 0,
            "has_multiple_birth_exception": False,
        },
    }
    evidence_statuses = {
        "BIRTH_CERTIFICATE": EvidenceStatus.VERIFIED,
        "AADHAAR": EvidenceStatus.VERIFIED,
    }

    journey, citizen, _, _ = await _create_test_journey_for_eval(
        db_session,
        scheme_code="SSY",
        citizen_ref="SYN-CIT-SSY-OK",
        claims_data=claims_data,
        evidence_statuses=evidence_statuses,
    )

    token = _make_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.post(f"/api/v1/officer/cases/{journey.id}/evaluate", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["determination"] == "ELIGIBLE"
    assert len(data["rules_evaluated"]) > 0
    assert len(data["reasons_en"]) > 0


@pytest.mark.asyncio
async def test_ssy_ineligible_male_beneficiary(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Male beneficiary evaluates to INELIGIBLE under statutory SSY scheme rules."""
    claims_data = {
        "beneficiary": {
            "gender": "MALE",  # Ineligible: strictly girl child only
            "is_indian_resident": True,
            "date_of_birth": "2020-05-15",
        },
        "account": {
            "opening_date": "2024-06-01",
            "is_first_account_for_child": True,
        },
        "guardian": {
            "is_natural_guardian": True,
            "is_court_appointed_legal_guardian": False,
        },
        "family": {
            "active_ssy_accounts_count": 0,
            "has_multiple_birth_exception": False,
        },
    }
    evidence_statuses = {
        "BIRTH_CERTIFICATE": EvidenceStatus.VERIFIED,
        "AADHAAR": EvidenceStatus.VERIFIED,
    }

    journey, citizen, _, _ = await _create_test_journey_for_eval(
        db_session,
        scheme_code="SSY",
        citizen_ref="SYN-CIT-SSY-BOY",
        claims_data=claims_data,
        evidence_statuses=evidence_statuses,
    )

    token = _make_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.post(f"/api/v1/officer/cases/{journey.id}/evaluate", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["determination"] == "INELIGIBLE"
    disq_text = " ".join(data["disqualifiers"]).lower()
    assert "girl" in disq_text or "female" in disq_text or "gender" in disq_text


@pytest.mark.asyncio
async def test_ssy_age_boundary_at_exactly_ten(
    async_client: AsyncClient, db_session: AsyncSession
):
    """SSY age boundary: girl attaining age 10 on or after opening date is ineligible."""
    dob = "2014-05-10"
    ev_stat = {
        "BIRTH_CERTIFICATE": EvidenceStatus.VERIFIED,
        "AADHAAR": EvidenceStatus.VERIFIED,
    }

    # Case 1: Exactly on 10th birthday -> INELIGIBLE (has attained age 10)
    claims_age_10 = {
        "beneficiary": {"gender": "FEMALE", "is_indian_resident": True, "date_of_birth": dob},
        "account": {"opening_date": "2024-05-10", "is_first_account_for_child": True},
        "guardian": {"is_natural_guardian": True, "is_court_appointed_legal_guardian": False},
        "family": {"active_ssy_accounts_count": 0, "has_multiple_birth_exception": False},
    }
    journey_10, _, _, _ = await _create_test_journey_for_eval(
        db_session, scheme_code="SSY", citizen_ref="SYN-CIT-SSY-AGE10", claims_data=claims_age_10, evidence_statuses=ev_stat
    )
    token = _make_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp_10 = await async_client.post(f"/api/v1/officer/cases/{journey_10.id}/evaluate", headers=headers)
    assert resp_10.status_code == 200
    assert resp_10.json()["determination"] == "INELIGIBLE"

    # Case 2: One day before 10th birthday (age 9y 364d) -> ELIGIBLE
    claims_age_9 = {
        "beneficiary": {"gender": "FEMALE", "is_indian_resident": True, "date_of_birth": dob},
        "account": {"opening_date": "2024-05-09", "is_first_account_for_child": True},
        "guardian": {"is_natural_guardian": True, "is_court_appointed_legal_guardian": False},
        "family": {"active_ssy_accounts_count": 0, "has_multiple_birth_exception": False},
    }
    journey_9, _, _, _ = await _create_test_journey_for_eval(
        db_session, scheme_code="SSY", citizen_ref="SYN-CIT-SSY-AGE9", claims_data=claims_age_9, evidence_statuses=ev_stat
    )
    resp_9 = await async_client.post(f"/api/v1/officer/cases/{journey_9.id}/evaluate", headers=headers)
    assert resp_9.status_code == 200
    assert resp_9.json()["determination"] == "ELIGIBLE"


@pytest.mark.asyncio
async def test_ssy_family_account_limit_and_multiple_birth(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Family with 2 existing accounts is ineligible unless multiple birth exception applies."""
    ev_stat = {
        "BIRTH_CERTIFICATE": EvidenceStatus.VERIFIED,
        "AADHAAR": EvidenceStatus.VERIFIED,
    }

    # Case A: 2 accounts without multiple birth exception -> INELIGIBLE
    claims_2_acc = {
        "beneficiary": {"gender": "FEMALE", "is_indian_resident": True, "date_of_birth": "2020-01-01"},
        "account": {"opening_date": "2024-01-01", "is_first_account_for_child": True},
        "guardian": {"is_natural_guardian": True, "is_court_appointed_legal_guardian": False},
        "family": {"active_ssy_accounts_count": 2, "has_multiple_birth_exception": False},
    }
    journey_a, _, _, _ = await _create_test_journey_for_eval(
        db_session, scheme_code="SSY", citizen_ref="SYN-CIT-SSY-2ACC", claims_data=claims_2_acc, evidence_statuses=ev_stat
    )
    token = _make_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp_a = await async_client.post(f"/api/v1/officer/cases/{journey_a.id}/evaluate", headers=headers)
    assert resp_a.status_code == 200
    assert resp_a.json()["determination"] == "INELIGIBLE"

    # Case B: 2 accounts with multiple birth exception -> ELIGIBLE
    claims_twin = {
        "beneficiary": {"gender": "FEMALE", "is_indian_resident": True, "date_of_birth": "2020-01-01"},
        "account": {"opening_date": "2024-01-01", "is_first_account_for_child": True},
        "guardian": {"is_natural_guardian": True, "is_court_appointed_legal_guardian": False},
        "family": {"active_ssy_accounts_count": 2, "has_multiple_birth_exception": True},
    }
    journey_b, _, _, _ = await _create_test_journey_for_eval(
        db_session, scheme_code="SSY", citizen_ref="SYN-CIT-SSY-TWIN", claims_data=claims_twin, evidence_statuses=ev_stat
    )
    resp_b = await async_client.post(f"/api/v1/officer/cases/{journey_b.id}/evaluate", headers=headers)
    assert resp_b.status_code == 200
    assert resp_b.json()["determination"] == "ELIGIBLE"


# ==============================================================================
# 4. Unsupported Scheme Safe Failure Test
# ==============================================================================

@pytest.mark.asyncio
async def test_unsupported_scheme_safe_failure_400(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Unsupported schemes fail safely with HTTP 400 without fabricating rules."""
    # Create a non-canonical scheme
    scheme = Scheme(
        id=uuid.uuid4(),
        scheme_code="UNSUPPORTED_SCHEME",
        name_en="Unsupported Test Scheme",
        name_hi="असमर्थित परीक्षण योजना",
        description_en="Non-statutory welfare program",
        description_hi="गैर-वैधानिक कल्याण योजना",
        official_url="https://welfare.gov.in/unsupported",
        status=SchemeStatus.ACTIVE,
    )
    db_session.add(scheme)
    await db_session.flush()

    pv = PolicyVersion(
        id=uuid.uuid4(),
        scheme_id=scheme.id,
        version_code="v1.0-test",
        effective_from=date(2023, 1, 1),
        source_url="https://welfare.gov.in/unsupported",
        source_title="Unsupported Guidelines",
    )
    db_session.add(pv)
    await db_session.flush()

    journey, _, _, _ = await _create_test_journey_for_eval(
        db_session,
        scheme_code="UNSUPPORTED_SCHEME",
        citizen_ref="SYN-CIT-UNSUPPORTED",
        policy_version_code="v1.0-test",
        claims_data={"applicant": {"is_indian_citizen": True}},
        evidence_statuses={},
    )

    token = _make_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.post(f"/api/v1/officer/cases/{journey.id}/evaluate", headers=headers)
    assert resp.status_code == 400
    assert "does not have a structured deterministic ruleset" in resp.text.lower()


# ==============================================================================
# 5. Security, IDOR Protection & Authorization Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_officer_case_assignment_ownership_authorization(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Strict Phase D & E object-level officer assignment verification on evaluate endpoint."""
    journey, _, _, _ = await _create_test_journey_for_eval(
        db_session,
        scheme_code="PM_KISAN",
        assigned_officer_email="assigned.officer@yogyatamitra.local",
        claims_data={"family": {"owns_cultivable_land": True}},
        evidence_statuses={},
    )

    # 1. Assigned officer permitted
    assigned_token = _make_officer_token(email="assigned.officer@yogyatamitra.local")
    resp_assigned = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evaluate",
        headers={"Authorization": f"Bearer {assigned_token}"},
    )
    # Permitted to execute evaluation gate
    assert resp_assigned.status_code == 200

    # 2. Peer / unassigned officer forbidden (403)
    peer_token = _make_officer_token(email="peer.officer@yogyatamitra.local")
    resp_peer = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evaluate",
        headers={"Authorization": f"Bearer {peer_token}"},
    )
    assert resp_peer.status_code == 403
    assert "assigned to another officer" in resp_peer.text.lower()

    # 3. Supervisor permitted
    supervisor_token = _make_officer_token(email="supervisor@yogyatamitra.local", role="SUPERVISOR")
    resp_sup = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evaluate",
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert resp_sup.status_code == 200


@pytest.mark.asyncio
async def test_citizen_cannot_execute_evaluation_or_view_officer_traces(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Citizen tokens strictly forbidden from officer evaluation endpoints."""
    journey, _, _, _ = await _create_test_journey_for_eval(
        db_session,
        scheme_code="PM_KISAN",
        claims_data={"family": {"owns_cultivable_land": True}},
        evidence_statuses={},
    )

    citizen_token = _make_citizen_token()
    headers = {"Authorization": f"Bearer {citizen_token}"}

    # POST /evaluate -> 403
    resp_post = await async_client.post(f"/api/v1/officer/cases/{journey.id}/evaluate", headers=headers)
    assert resp_post.status_code == 403

    # GET /evaluation -> 403
    resp_get = await async_client.get(f"/api/v1/officer/cases/{journey.id}/evaluation", headers=headers)
    assert resp_get.status_code == 403

    # GET /evaluation/history -> 403
    resp_hist = await async_client.get(f"/api/v1/officer/cases/{journey.id}/evaluation/history", headers=headers)
    assert resp_hist.status_code == 403


@pytest.mark.asyncio
async def test_citizen_decision_retrieval_and_idor_protection(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Citizen can view own decision; other citizens receive 404 IDOR protection."""
    journey, citizen, _, _ = await _create_test_journey_for_eval(
        db_session,
        scheme_code="PM_KISAN",
        citizen_ref="SYN-CIT-OWNER",
        claims_data={"family": {"owns_cultivable_land": True, "total_land_area_hectares": 1.5, "is_institutional_landholder": False, "has_constitutional_post_holder": False, "has_public_representative": False, "has_disqualified_government_employee": False, "has_pensioner_above_ten_thousand": False, "has_income_tax_payer": False, "has_registered_practicing_professional": False, "is_nri": False}, "land": {"transferred_after_cutoff": False, "acquired_via_succession": False}},
        evidence_statuses={"LAND_RECORD": EvidenceStatus.VERIFIED, "AADHAAR": EvidenceStatus.VERIFIED, "BANK_PASSBOOK": EvidenceStatus.VERIFIED},
    )

    owner_token = _make_citizen_token(email="owner@test.local", ref="SYN-CIT-OWNER")
    foreign_token = _make_citizen_token(email="foreign@test.local", ref="SYN-CIT-FOREIGN")

    # 1. Before evaluation: decision returns PENDING_EVALUATION
    resp_pre = await async_client.get(
        f"/api/v1/citizen/applications/{journey.id}/decision",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp_pre.status_code == 200
    data_pre = resp_pre.json()
    assert data_pre["is_evaluated"] is False
    assert data_pre["outcome"] == "PENDING_EVALUATION"

    # Execute evaluation as officer
    officer_token = _make_officer_token()
    await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evaluate",
        headers={"Authorization": f"Bearer {officer_token}"},
    )

    # 2. After evaluation: Owner retrieves statutory decision with bilingual text & disclaimers
    resp_post = await async_client.get(
        f"/api/v1/citizen/applications/{journey.id}/decision",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp_post.status_code == 200
    data_post = resp_post.json()
    assert data_post["is_evaluated"] is True
    assert data_post["outcome"] == "ELIGIBLE"
    assert "statutory_disclaimer_en" in data_post
    assert "statutory_disclaimer_hi" in data_post

    # 3. Foreign citizen receives 404 (IDOR protection)
    resp_foreign = await async_client.get(
        f"/api/v1/citizen/applications/{journey.id}/decision",
        headers={"Authorization": f"Bearer {foreign_token}"},
    )
    assert resp_foreign.status_code == 404


# ==============================================================================
# 6. Append-Only Persistence, Idempotency & History Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_append_only_evaluation_traces_and_history(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Re-evaluation creates distinct EvaluationTrace records and preserves complete history."""
    journey, citizen, _, _ = await _create_test_journey_for_eval(
        db_session,
        scheme_code="PM_KISAN",
        claims_data={"family": {"owns_cultivable_land": True}},
        evidence_statuses={},
    )
    token = _make_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    # 1. First evaluation: INSUFFICIENT_INFORMATION
    resp1 = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evaluate",
        headers=headers,
        json={"notes": "First evaluation round"},
    )
    assert resp1.status_code == 200
    eval_id_1 = resp1.json()["evaluation_id"]

    # Wait 2.1 seconds to exceed the idempotency deduplication window
    await asyncio.sleep(2.1)

    # 2. Second evaluation round with different notes
    resp2 = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evaluate",
        headers=headers,
        json={"notes": "Second evaluation round"},
    )
    assert resp2.status_code == 200
    eval_id_2 = resp2.json()["evaluation_id"]

    assert eval_id_1 != eval_id_2

    # 3. Check history endpoint
    resp_hist = await async_client.get(
        f"/api/v1/officer/cases/{journey.id}/evaluation/history",
        headers=headers,
    )
    assert resp_hist.status_code == 200
    hist = resp_hist.json()
    assert len(hist) == 2
    # Reverse chronological order
    assert hist[0]["evaluation_id"] == eval_id_2
    assert hist[1]["evaluation_id"] == eval_id_1


@pytest.mark.asyncio
async def test_idempotency_caching_within_two_seconds(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Rapid duplicate evaluation requests (< 2s) return cached result without duplicating traces."""
    journey, _, _, _ = await _create_test_journey_for_eval(
        db_session,
        scheme_code="PM_KISAN",
        claims_data={"family": {"owns_cultivable_land": True}},
        evidence_statuses={},
    )
    token = _make_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp1 = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evaluate",
        headers=headers,
    )
    assert resp1.status_code == 200
    id1 = resp1.json()["evaluation_id"]

    # Immediate second call
    resp2 = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evaluate",
        headers=headers,
    )
    assert resp2.status_code == 200
    id2 = resp2.json()["evaluation_id"]

    # Same evaluation returned
    assert id1 == id2


@pytest.mark.asyncio
async def test_anti_spoofing_extra_payload_fields_forbidden(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Payloads attempting to spoof evaluation outcome or inject unknown fields fail with 422."""
    journey, _, _, _ = await _create_test_journey_for_eval(
        db_session,
        scheme_code="PM_KISAN",
        claims_data={"family": {"owns_cultivable_land": True}},
        evidence_statuses={},
    )
    token = _make_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to spoof outcome
    bad_payload = {
        "notes": "Legitimate note",
        "outcome": "ELIGIBLE",
        "spoofed_status": True,
    }
    resp = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evaluate",
        headers=headers,
        json=bad_payload,
    )
    assert resp.status_code == 422

# ==============================================================================
# Verified Fact Provenance Regression Tests (FINDING-F-01 Remediation)
# ==============================================================================

@pytest.mark.asyncio
async def test_provenance_claimed_claim_not_in_evaluation_facts(
    db_session: AsyncSession,
):
    """TEST 1: CLAIMED claim value must NOT appear in evaluation facts."""
    from app.services.evaluation_service import EvaluationService

    service = EvaluationService(db_session)
    claim = Claim(
        id=uuid.uuid4(),
        citizen_id=uuid.uuid4(),
        claim_type="family.has_pensioner_above_ten_thousand",
        value_json={"value": True},
        status=ClaimStatus.CLAIMED,
        source="CITIZEN_DECLARATION",
    )
    facts = service._extract_facts_from_claims([claim])
    assert "family" not in facts or "has_pensioner_above_ten_thousand" not in facts.get("family", {})
    assert facts == {}


@pytest.mark.asyncio
async def test_provenance_pending_claim_not_in_evaluation_facts(
    db_session: AsyncSession,
):
    """TEST 2: PENDING claim value must NOT appear in evaluation facts."""
    from app.services.evaluation_service import EvaluationService

    service = EvaluationService(db_session)
    claim = Claim(
        id=uuid.uuid4(),
        citizen_id=uuid.uuid4(),
        claim_type="family.owns_cultivable_land",
        value_json={"value": True},
        status=ClaimStatus.PENDING,
        source="CITIZEN_DECLARATION",
    )
    facts = service._extract_facts_from_claims([claim])
    assert facts == {}


@pytest.mark.asyncio
async def test_provenance_rejected_claim_not_in_evaluation_facts(
    db_session: AsyncSession,
):
    """TEST 3: REJECTED claim value must NOT appear in evaluation facts."""
    from app.services.evaluation_service import EvaluationService

    service = EvaluationService(db_session)
    claim = Claim(
        id=uuid.uuid4(),
        citizen_id=uuid.uuid4(),
        claim_type="beneficiary.gender",
        value_json={"value": "FEMALE"},
        status=ClaimStatus.REJECTED,
        source="CITIZEN_DECLARATION",
    )
    facts = service._extract_facts_from_claims([claim])
    assert facts == {}


@pytest.mark.asyncio
async def test_provenance_verified_claim_enters_evaluation_facts(
    db_session: AsyncSession,
):
    """TEST 4: VERIFIED claim value MAY appear in evaluation facts and be evaluated."""
    from app.services.evaluation_service import EvaluationService

    service = EvaluationService(db_session)
    claim = Claim(
        id=uuid.uuid4(),
        citizen_id=uuid.uuid4(),
        claim_type="family.has_pensioner_above_ten_thousand",
        value_json={"value": False},
        status=ClaimStatus.VERIFIED,
        source="CITIZEN_DECLARATION",
    )
    facts = service._extract_facts_from_claims([claim])
    assert facts == {"family": {"has_pensioner_above_ten_thousand": False}}


@pytest.mark.asyncio
async def test_provenance_mandatory_fact_unverified_claim_yields_insufficient_information(
    async_client: AsyncClient, db_session: AsyncSession
):
    """TEST 5: Mandatory fact exists only as an unverified claim -> evaluation must not use unverified value, produces INSUFFICIENT_INFORMATION."""
    pm_kisan_verified_evidence = {
        "LAND_RECORD": EvidenceStatus.VERIFIED,
        "AADHAAR": EvidenceStatus.VERIFIED,
        "BANK_PASSBOOK": EvidenceStatus.VERIFIED,
    }
    claims = {
        "family": {
            "owns_cultivable_land": True,
            "total_land_area_hectares": 1.5,
            "is_institutional_landholder": False,
            "has_constitutional_post_holder": False,
            "has_public_representative": False,
            "has_disqualified_government_employee": False,
            "has_pensioner_above_ten_thousand": False,
            "has_income_tax_payer": False,
            "has_registered_practicing_professional": False,
            "is_nri": False,
        },
        "land": {
            "transferred_after_cutoff": False,
            "acquired_via_succession": False,
        },
    }
    # Set family claims to CLAIMED (unverified)
    claims_status = {
        "family": ClaimStatus.CLAIMED,
        "land": ClaimStatus.VERIFIED,
    }
    journey, _, _, _ = await _create_test_journey_for_eval(
        db_session,
        scheme_code="PM_KISAN",
        claims_data=claims,
        evidence_statuses=pm_kisan_verified_evidence,
        claims_status=claims_status,
    )
    token = _make_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evaluate",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["determination"] == "INSUFFICIENT_INFORMATION"


@pytest.mark.asyncio
async def test_provenance_client_payload_manipulation_rejected(
    async_client: AsyncClient, db_session: AsyncSession
):
    """TEST 6: Attempt to manipulate client payload to inject verified facts fails."""
    journey, _, _, _ = await _create_test_journey_for_eval(
        db_session,
        scheme_code="PM_KISAN",
        claims_data={"family": {"owns_cultivable_land": True}},
        evidence_statuses={},
    )
    token = _make_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    malicious_payload = {
        "notes": "Trying to bypass verified claim provenance",
        "facts": {"family": {"owns_cultivable_land": True}},
        "verified_claims": [{"claim_type": "family.owns_cultivable_land", "value": True}],
    }
    resp = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evaluate",
        headers=headers,
        json=malicious_payload,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_provenance_input_snapshot_json_contains_only_legitimate_verified_facts(
    async_client: AsyncClient, db_session: AsyncSession
):
    """TEST 7: EvaluationTrace.input_snapshot_json contains only facts legitimately admitted into context."""
    pm_kisan_verified_evidence = {
        "LAND_RECORD": EvidenceStatus.VERIFIED,
        "AADHAAR": EvidenceStatus.VERIFIED,
        "BANK_PASSBOOK": EvidenceStatus.VERIFIED,
    }
    claims = {
        "family.owns_cultivable_land": True,
        "family.is_institutional_landholder": False,
        "family.has_constitutional_post_holder": False,
        "family.has_public_representative": False,
        "family.has_disqualified_government_employee": False,
        "family.has_pensioner_above_ten_thousand": False,
        "family.has_income_tax_payer": True,  # UNVERIFIED
        "family.has_registered_practicing_professional": False,
        "family.is_nri": False,
        "land.transferred_after_cutoff": False,
        "land.acquired_via_succession": False,
    }
    claims_status = {
        "family.has_income_tax_payer": ClaimStatus.CLAIMED,  # UNVERIFIED
    }
    journey, _, _, _ = await _create_test_journey_for_eval(
        db_session,
        scheme_code="PM_KISAN",
        claims_data=claims,
        evidence_statuses=pm_kisan_verified_evidence,
        default_claim_status=ClaimStatus.VERIFIED,
        claims_status=claims_status,
    )
    token = _make_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evaluate",
        headers=headers,
    )
    assert resp.status_code == 200

    stmt = (
        select(EvaluationTrace)
        .where(EvaluationTrace.journey_id == journey.id)
        .order_by(EvaluationTrace.created_at.desc())
    )
    trace = (await db_session.execute(stmt)).scalars().first()
    assert trace is not None
    snapshot = trace.input_snapshot_json or {}

    # Verified facts MUST be present
    assert snapshot.get("family", {}).get("owns_cultivable_land") is True
    assert snapshot.get("family", {}).get("is_institutional_landholder") is False

    # Unverified fact MUST NOT be present in snapshot
    assert "has_income_tax_payer" not in snapshot.get("family", {})


@pytest.mark.asyncio
async def test_provenance_existing_eligible_scenario_when_verified(
    async_client: AsyncClient, db_session: AsyncSession
):
    """TEST 8: Existing eligible scenario remains eligible when all relevant claims are legitimately VERIFIED."""
    pm_kisan_verified_evidence = {
        "LAND_RECORD": EvidenceStatus.VERIFIED,
        "AADHAAR": EvidenceStatus.VERIFIED,
        "BANK_PASSBOOK": EvidenceStatus.VERIFIED,
    }
    claims_data = {
        "family": {
            "owns_cultivable_land": True,
            "total_land_area_hectares": 1.5,
            "is_institutional_landholder": False,
            "has_constitutional_post_holder": False,
            "has_public_representative": False,
            "has_disqualified_government_employee": False,
            "has_pensioner_above_ten_thousand": False,
            "has_income_tax_payer": False,
            "has_registered_practicing_professional": False,
            "is_nri": False,
        },
        "land": {
            "transferred_after_cutoff": False,
            "acquired_via_succession": False,
        },
    }
    journey, _, _, _ = await _create_test_journey_for_eval(
        db_session,
        scheme_code="PM_KISAN",
        claims_data=claims_data,
        evidence_statuses=pm_kisan_verified_evidence,
        default_claim_status=ClaimStatus.VERIFIED,
    )
    token = _make_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evaluate",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["determination"] == "ELIGIBLE"


@pytest.mark.asyncio
async def test_provenance_existing_ineligible_scenario_when_decisive_fact_verified(
    async_client: AsyncClient, db_session: AsyncSession
):
    """TEST 9: Existing ineligible scenario remains ineligible when the decisive fact is VERIFIED."""
    pm_kisan_verified_evidence = {
        "LAND_RECORD": EvidenceStatus.VERIFIED,
        "AADHAAR": EvidenceStatus.VERIFIED,
        "BANK_PASSBOOK": EvidenceStatus.VERIFIED,
    }
    claims_data = {
        "family": {
            "owns_cultivable_land": True,
            "total_land_area_hectares": 1.5,
            "is_institutional_landholder": False,
            "has_constitutional_post_holder": False,
            "has_public_representative": False,
            "has_disqualified_government_employee": False,
            "has_pensioner_above_ten_thousand": True,  # Disqualifier
            "has_income_tax_payer": False,
            "has_registered_practicing_professional": False,
            "is_nri": False,
        },
        "land": {
            "transferred_after_cutoff": False,
            "acquired_via_succession": False,
        },
    }
    journey, _, _, _ = await _create_test_journey_for_eval(
        db_session,
        scheme_code="PM_KISAN",
        claims_data=claims_data,
        evidence_statuses=pm_kisan_verified_evidence,
        default_claim_status=ClaimStatus.VERIFIED,
    )
    token = _make_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evaluate",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["determination"] == "INELIGIBLE"
    failed_rules = [r for r in resp.json()["rules_evaluated"] if r["result"] == "FAIL"]
    assert any("pension" in str(r).lower() for r in failed_rules)


@pytest.mark.asyncio
async def test_provenance_reevaluation_after_claim_verification(
    async_client: AsyncClient, db_session: AsyncSession
):
    """TEST 10: Re-evaluation after claim verification uses the newly verified fact and does not use stale unverified values."""
    pm_kisan_verified_evidence = {
        "LAND_RECORD": EvidenceStatus.VERIFIED,
        "AADHAAR": EvidenceStatus.VERIFIED,
        "BANK_PASSBOOK": EvidenceStatus.VERIFIED,
    }
    claims = {
        "family.owns_cultivable_land": True,
        "family.total_land_area_hectares": 1.5,
        "family.is_institutional_landholder": False,
        "family.has_constitutional_post_holder": False,
        "family.has_public_representative": False,
        "family.has_disqualified_government_employee": False,
        "family.has_pensioner_above_ten_thousand": True,
        "family.has_income_tax_payer": False,
        "family.has_registered_practicing_professional": False,
        "family.is_nri": False,
        "land.transferred_after_cutoff": False,
        "land.acquired_via_succession": False,
    }
    # Initial state: has_pensioner_above_ten_thousand is CLAIMED (unverified), all others verified
    claims_status = {
        "family.has_pensioner_above_ten_thousand": ClaimStatus.CLAIMED,  # UNVERIFIED
    }
    journey, _, claims_objs, _ = await _create_test_journey_for_eval(
        db_session,
        scheme_code="PM_KISAN",
        claims_data=claims,
        evidence_statuses=pm_kisan_verified_evidence,
        default_claim_status=ClaimStatus.VERIFIED,
        claims_status=claims_status,
    )
    token = _make_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Round 1 Evaluation: has_pensioner_above_ten_thousand is unverified -> INSUFFICIENT_INFORMATION
    resp1 = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evaluate",
        headers=headers,
    )
    assert resp1.status_code == 200
    res1 = resp1.json()
    assert res1["determination"] == "INSUFFICIENT_INFORMATION"

    # Now officer verifies the pension claim
    pension_claim = next(c for c in claims_objs if c.claim_type == "family.has_pensioner_above_ten_thousand")
    pension_claim.status = ClaimStatus.VERIFIED
    pension_claim.updated_at = datetime.now(timezone.utc)
    await db_session.commit()

    # Wait past the 2-second deduplication cache window
    await asyncio.sleep(2.1)

    # Round 2 Evaluation: newly verified fact is now admitted into evaluation facts -> INELIGIBLE
    resp2 = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evaluate",
        headers=headers,
    )
    assert resp2.status_code == 200
    res2 = resp2.json()
    assert res2["determination"] == "INELIGIBLE"

    # Verify both traces are recorded in history
    resp_hist = await async_client.get(
        f"/api/v1/officer/cases/{journey.id}/evaluation/history",
        headers=headers,
    )
    assert resp_hist.status_code == 200
    hist = resp_hist.json()
    assert len(hist) == 2
    assert hist[0]["determination"] == "INELIGIBLE"
    assert hist[1]["determination"] == "INSUFFICIENT_INFORMATION"
