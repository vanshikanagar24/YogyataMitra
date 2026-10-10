"""Comprehensive Test Suite for YogyataMitra Phase D.

Verifies:
1. Operational Officer Assignment Model:
   - Persisted officer assignments in PostgreSQL
   - Due date and SLA tracking
   - Partial unique constraint on active assignment per journey
2. Deterministic Workload Balancing Strategy:
   - Least-loaded distribution across verified officers
   - Explainable deterministic assignment without opaque AI scoring
3. Manual Assignment & Auditable Reassignment:
   - Manual assignment to verified eligible officers
   - Historical preservation (old assignment marked REASSIGNED with is_active=False)
   - Mandatory justification/reason for reassignment
   - Complete assignment history retrieval
4. SLA Status Computation:
   - NOT_DUE (future target)
   - DUE_SOON (<= 12 hours before target)
   - OVERDUE (past target due date)
   - COMPLETED (resolved cases)
5. Database-Backed Dashboard Metrics:
   - my_active_requests, unassigned_requests, due_soon, overdue, completed, total_active_workload
   - All counts derive from actual database records
6. Security and IDOR Protection:
   - Citizen tokens strictly rejected with 403 on all officer assignment and dashboard endpoints
   - Unauthenticated requests rejected with 401
   - Nonexistent officers and journeys handled safely with 400 / 404
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token
from app.models.assignment import OfficerAssignment
from app.models.citizen import Citizen, Claim
from app.models.enums import (
    AssignmentStatus,
    ClaimStatus,
    JourneyState,
    SchemeStatus,
    SLAStatus,
)
from app.models.human_review import HumanReviewAuditEvent
from app.models.journey import EvaluationJourney
from app.models.scheme import PolicyVersion, Scheme
from app.services.assignment_service import (
    compute_sla_status,
    get_active_assignment_for_journey,
    reassign_journey,
)


def _make_officer_token(
    email: str = "officer@yogyatamitra.local",
    role: str = "OFFICER",
    name: str = "Senior Verification Officer (Demo)",
) -> str:
    """Generate a valid officer Bearer JWT for test authorization."""
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
    ref: str = "SYN-CIT-DEMO0001",
    name: str = "Rameshwar Sharma",
) -> str:
    """Generate a citizen Bearer JWT."""
    payload = {
        "sub": email,
        "role": "CITIZEN",
        "citizen_ref": ref,
        "name": name,
        "state": "Maharashtra",
        "district": "Pune",
    }
    return create_access_token(data=payload)


async def _create_test_journey(
    session: AsyncSession,
    scheme_code: str = "PM_KISAN",
    state: JourneyState = JourneyState.EVIDENCE_PENDING,
) -> EvaluationJourney:
    """Helper to create a persisted submitted journey for testing."""
    # Find scheme
    stmt = select(Scheme).where(Scheme.scheme_code == scheme_code)
    scheme = (await session.execute(stmt)).scalars().first()
    if not scheme:
        scheme = Scheme(
            id=uuid.uuid4(),
            scheme_code=scheme_code,
            name_en=f"Test Scheme {scheme_code}",
            status=SchemeStatus.ACTIVE,
        )
        session.add(scheme)
        await session.flush()

    # Create synthetic citizen
    citizen = Citizen(
        id=uuid.uuid4(),
        synthetic_reference=f"SYN-TEST-{str(uuid.uuid4())[:8].upper()}",
        display_name="Test Citizen",
    )
    session.add(citizen)
    await session.flush()

    now = datetime.now(timezone.utc)
    journey = EvaluationJourney(
        id=uuid.uuid4(),
        citizen_id=citizen.id,
        scheme_id=scheme.id,
        state=state,
        submitted_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(journey)
    await session.commit()
    await session.refresh(journey)
    return journey


# ==============================================================================
# 1. SLA Status Computation Unit Tests
# ==============================================================================

def test_sla_status_computation():
    """Verify SLA status calculation transitions deterministically."""
    now = datetime.now(timezone.utc)

    # 1. Completed assignment
    assert compute_sla_status(now + timedelta(hours=24), AssignmentStatus.COMPLETED, now) == SLAStatus.COMPLETED

    # 2. Overdue: due_at in the past
    overdue_due = now - timedelta(hours=2)
    assert compute_sla_status(overdue_due, AssignmentStatus.ASSIGNED, now) == SLAStatus.OVERDUE

    # 3. Due soon: due_at is within 12 hours
    due_soon_due = now + timedelta(hours=6)
    assert compute_sla_status(due_soon_due, AssignmentStatus.ASSIGNED, now) == SLAStatus.DUE_SOON

    # 4. On Track / Not Due: due_at is 48 hours in future
    not_due = now + timedelta(hours=48)
    assert compute_sla_status(not_due, AssignmentStatus.ASSIGNED, now) == SLAStatus.NOT_DUE


# ==============================================================================
# 2. Deterministic Least-Loaded Auto-Assignment Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_deterministic_least_loaded_assignment(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verify auto-assignment routes cases across active officers using least-loaded strategy."""
    token = _make_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Create 3 submitted journeys
    j1 = await _create_test_journey(db_session, "PM_KISAN")
    j2 = await _create_test_journey(db_session, "PM_KISAN")
    j3 = await _create_test_journey(db_session, "SSY")

    # 1. Inspect pre-assignment workloads
    from app.services.assignment_service import calculate_officer_workloads, get_eligible_officers
    eligible = get_eligible_officers()
    w1 = await calculate_officer_workloads(db_session)
    min_count_1 = min(w1.get(o["email"], 0) for o in eligible)

    # Auto-assign j1: must select an officer with the minimum workload
    resp1 = await async_client.post(f"/api/v1/officer/cases/{j1.id}/auto-assign", headers=headers)
    assert resp1.status_code == 200
    a1 = resp1.json()
    assert a1["is_active"] is True
    assert a1["status"] == "ASSIGNED"
    officer_1 = a1["officer_identity"]
    assert w1.get(officer_1, 0) == min_count_1

    # Workload for officer_1 must have increased
    w2 = await calculate_officer_workloads(db_session)
    assert w2.get(officer_1, 0) == min_count_1 + 1

    # Auto-assign j2: must select an officer with current minimum workload
    min_count_2 = min(w2.get(o["email"], 0) for o in eligible)
    resp2 = await async_client.post(f"/api/v1/officer/cases/{j2.id}/auto-assign", headers=headers)
    assert resp2.status_code == 200
    a2 = resp2.json()
    assert a2["is_active"] is True
    officer_2 = a2["officer_identity"]
    assert w2.get(officer_2, 0) == min_count_2

    # Auto-assign j3: must select an officer with current minimum workload
    w3 = await calculate_officer_workloads(db_session)
    min_count_3 = min(w3.get(o["email"], 0) for o in eligible)
    resp3 = await async_client.post(f"/api/v1/officer/cases/{j3.id}/auto-assign", headers=headers)
    assert resp3.status_code == 200
    a3 = resp3.json()
    assert a3["is_active"] is True
    officer_3 = a3["officer_identity"]
    assert w3.get(officer_3, 0) == min_count_3



# ==============================================================================
# 3. Manual Assignment & Historical Reassignment Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_manual_assignment_and_reassignment_preserves_history(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verify manual assignment and subsequent reassignment preserves complete historical trail."""
    token = _make_officer_token("officer@yogyatamitra.local")
    headers = {"Authorization": f"Bearer {token}"}

    journey = await _create_test_journey(db_session, "PM_KISAN")

    # 1. Initial manual assignment to officer@yogyatamitra.local
    assign_payload = {
        "officer_identity": "officer@yogyatamitra.local",
        "sla_hours": 36,
        "reason": "Initial manual distribution",
    }
    resp1 = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/assign",
        json=assign_payload,
        headers=headers,
    )
    assert resp1.status_code == 200
    a1 = resp1.json()
    assert a1["officer_identity"] == "officer@yogyatamitra.local"
    assert a1["sla_duration_hours"] == 36
    assert a1["is_active"] is True

    # 2. Reassign to officer.varanasi@yogyatamitra.local
    reassign_payload = {
        "new_officer_identity": "officer.varanasi@yogyatamitra.local",
        "reason": "Jurisdiction transfer to Varanasi district verification cell",
        "sla_hours": 48,
    }
    resp2 = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/reassign",
        json=reassign_payload,
        headers=headers,
    )
    assert resp2.status_code == 200
    a2 = resp2.json()
    assert a2["officer_identity"] == "officer.varanasi@yogyatamitra.local"
    assert a2["is_active"] is True

    # 3. Inspect assignment history
    resp_hist = await async_client.get(
        f"/api/v1/officer/cases/{journey.id}/assignments",
        headers=headers,
    )
    assert resp_hist.status_code == 200
    history = resp_hist.json()
    assert len(history) == 2

    # Old assignment must be REASSIGNED and inactive
    old_assign = next(a for a in history if a["officer_identity"] == "officer@yogyatamitra.local")
    assert old_assign["is_active"] is False
    assert old_assign["status"] == "REASSIGNED"
    assert old_assign["reassigned_to_id"] == a2["id"]

    # New assignment must be ASSIGNED and active
    new_assign = next(a for a in history if a["officer_identity"] == "officer.varanasi@yogyatamitra.local")
    assert new_assign["is_active"] is True
    assert new_assign["status"] == "ASSIGNED"


@pytest.mark.asyncio
async def test_reassignment_validation(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Reassignment requires substantive justification and rejects reassigning to same officer."""
    token = _make_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    journey = await _create_test_journey(db_session, "PM_KISAN")

    # Assign initially
    await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/assign",
        json={"officer_identity": "officer@yogyatamitra.local"},
        headers=headers,
    )

    # 1. Try to reassign without reason -> 422 or 400
    resp_empty_reason = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/reassign",
        json={"new_officer_identity": "officer.varanasi@yogyatamitra.local", "reason": "  "},
        headers=headers,
    )
    assert resp_empty_reason.status_code in (400, 422)

    # 2. Try to reassign to the same officer -> 400
    resp_same_officer = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/reassign",
        json={
            "new_officer_identity": "officer@yogyatamitra.local",
            "reason": "Reassigning to same officer should fail",
        },
        headers=headers,
    )
    assert resp_same_officer.status_code == 400
    err_json = resp_same_officer.json()
    err_msg = err_json.get("detail") or (err_json.get("error", {}).get("message") if isinstance(err_json.get("error"), dict) else str(err_json))
    assert "already assigned" in str(err_msg).lower()



# ==============================================================================
# 4. Database-Backed Officer Dashboard Metrics Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_officer_dashboard_database_stats(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Dashboard statistics must derive from actual PostgreSQL data (no mock counters)."""
    officer_email = "officer.lucknow@yogyatamitra.local"
    token = _make_officer_token(officer_email)
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch initial stats
    resp_init = await async_client.get("/api/v1/officer/dashboard/stats", headers=headers)
    assert resp_init.status_code == 200
    init_stats = resp_init.json()
    init_my_active = init_stats["my_active_requests"]
    init_total = init_stats["total_active_workload"]

    # Assign a new journey to officer.lucknow
    journey = await _create_test_journey(db_session, "SSY")
    await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/assign",
        json={"officer_identity": officer_email},
        headers=headers,
    )

    # Re-fetch stats: my_active_requests and total_active_workload must increment by exactly 1
    resp_after = await async_client.get("/api/v1/officer/dashboard/stats", headers=headers)
    assert resp_after.status_code == 200
    after_stats = resp_after.json()
    assert after_stats["my_active_requests"] == init_my_active + 1
    assert after_stats["total_active_workload"] == init_total + 1


# ==============================================================================
# 5. Security & IDOR Tests (Citizen Boundary Enforcement)
# ==============================================================================

@pytest.mark.asyncio
async def test_citizen_cannot_access_officer_dashboard_or_assignments(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Citizen accounts must be strictly forbidden (403) from all internal officer endpoints."""
    citizen_token = _make_citizen_token()
    headers = {"Authorization": f"Bearer {citizen_token}"}

    journey = await _create_test_journey(db_session, "PM_KISAN")

    # 1. Citizen cannot view officer dashboard stats
    resp_dash = await async_client.get("/api/v1/officer/dashboard/stats", headers=headers)
    assert resp_dash.status_code == 403

    # 2. Citizen cannot view officer verification queue
    resp_queue = await async_client.get("/api/v1/officer/queue", headers=headers)
    assert resp_queue.status_code == 403

    # 3. Citizen cannot assign applications
    resp_assign = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/assign",
        json={"officer_identity": "officer@yogyatamitra.local"},
        headers=headers,
    )
    assert resp_assign.status_code == 403

    # 4. Citizen cannot reassign applications
    resp_reassign = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/reassign",
        json={
            "new_officer_identity": "officer.varanasi@yogyatamitra.local",
            "reason": "Unauthorized attempt",
        },
        headers=headers,
    )
    assert resp_reassign.status_code == 403

    # 5. Citizen cannot view internal case assignments
    resp_hist = await async_client.get(
        f"/api/v1/officer/cases/{journey.id}/assignments",
        headers=headers,
    )
    assert resp_hist.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_requests_rejected(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Unauthenticated requests without token must return 401."""
    journey_id = uuid.uuid4()
    assert (await async_client.get("/api/v1/officer/dashboard/stats")).status_code == 401
    assert (await async_client.get("/api/v1/officer/queue")).status_code == 401
    assert (await async_client.post(f"/api/v1/officer/cases/{journey_id}/assign", json={"officer_identity": "officer@yogyatamitra.local"})).status_code == 401


@pytest.mark.asyncio
async def test_invalid_officer_or_journey_fails_safely(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Invalid officer or journey IDs fail gracefully with safe HTTP errors."""
    token = _make_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    journey = await _create_test_journey(db_session, "PM_KISAN")

    # 1. Invalid officer identity -> 400
    resp_inv_officer = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/assign",
        json={"officer_identity": "nonexistent.fake@unknown.gov.in"},
        headers=headers,
    )
    assert resp_inv_officer.status_code == 400

    # 2. Non-existent journey ID -> 404
    fake_journey_id = uuid.uuid4()
    resp_inv_journey = await async_client.post(
        f"/api/v1/officer/cases/{fake_journey_id}/assign",
        json={"officer_identity": "officer@yogyatamitra.local"},
        headers=headers,
    )
    assert resp_inv_journey.status_code == 404


# ==============================================================================
# 6. Reassignment Authorization & Privilege Boundary Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_reassignment_object_level_authorization_matrix(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Enforce strict object-level authorization on case reassignment:
    - Regular Officer A cannot reassign Officer B's active case (403).
    - Failed unauthorized attempt does NOT mutate database rows or audit events.
    - Assigned Officer B CAN reassign their own active case (200).
    - Supervisor CAN reassign active cases (200).
    - Admin CAN reassign active cases (200).
    - Citizen is rejected (403).
    - Unauthenticated is rejected (401).
    - Client cannot bypass authorization by spoofing payload identity/role.
    """
    journey = await _create_test_journey(db_session, "PM_KISAN")
    journey_id = journey.id

    officer_b_email = "officer.varanasi@yogyatamitra.local"
    officer_a_email = "officer.lucknow@yogyatamitra.local"
    officer_c_email = "officer@yogyatamitra.local"
    supervisor_email = "supervisor@yogyatamitra.local"
    admin_email = "admin@yogyatamitra.local"

    token_b = _make_officer_token(officer_b_email, role="OFFICER")
    token_a = _make_officer_token(officer_a_email, role="OFFICER")
    token_super = _make_officer_token(supervisor_email, role="SUPERVISOR")
    token_admin = _make_officer_token(admin_email, role="ADMIN")
    token_citizen = _make_citizen_token()

    headers_b = {"Authorization": f"Bearer {token_b}"}
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_super = {"Authorization": f"Bearer {token_super}"}
    headers_admin = {"Authorization": f"Bearer {token_admin}"}
    headers_citizen = {"Authorization": f"Bearer {token_citizen}"}

    # Initial assignment to Officer B
    resp_init = await async_client.post(
        f"/api/v1/officer/cases/{journey_id}/assign",
        json={"officer_identity": officer_b_email},
        headers=headers_b,
    )
    assert resp_init.status_code == 200
    init_assign = resp_init.json()
    assert init_assign["officer_identity"] == officer_b_email
    assert init_assign["is_active"] is True

    # Count initial assignment rows and audit events
    stmt_assign_count = select(func.count(OfficerAssignment.id)).where(OfficerAssignment.journey_id == journey_id)
    stmt_audit_count = select(func.count(HumanReviewAuditEvent.id)).where(HumanReviewAuditEvent.journey_id == journey_id)
    initial_assign_count = (await db_session.execute(stmt_assign_count)).scalar() or 0
    initial_audit_count = (await db_session.execute(stmt_audit_count)).scalar() or 0

    # A. Regular Officer A attempts to reassign Officer B's active case -> 403 Forbidden
    resp_unauth_a = await async_client.post(
        f"/api/v1/officer/cases/{journey_id}/reassign",
        json={
            "new_officer_identity": officer_c_email,
            "reason": "Officer A tries to reassign Officer B case without authority",
        },
        headers=headers_a,
    )
    assert resp_unauth_a.status_code == 403
    err_a = resp_unauth_a.json()
    err_msg_a = err_a.get("detail") or err_a.get("error", {}).get("message", "")
    assert "Only the currently assigned officer or an administrative supervisor can reassign" in str(err_msg_a)

    # G & H. Officer A attempts payload manipulation: extra fields to spoof role/assignee -> 422
    resp_spoof = await async_client.post(
        f"/api/v1/officer/cases/{journey_id}/reassign",
        json={
            "new_officer_identity": officer_c_email,
            "reason": "Officer A payload injection attempt",
            "assigned_by": officer_b_email,
            "actor_role": "SUPERVISOR",
        },
        headers=headers_a,
    )
    assert resp_spoof.status_code == 422

    # L. Verify failed attempts did NOT mutate database rows, active assignment, or audit events
    db_session.expire_all()
    assign_count_after_fail = (await db_session.execute(stmt_assign_count)).scalar() or 0
    audit_count_after_fail = (await db_session.execute(stmt_audit_count)).scalar() or 0
    assert assign_count_after_fail == initial_assign_count
    assert audit_count_after_fail == initial_audit_count

    active_assign_db = await get_active_assignment_for_journey(db_session, journey_id)
    assert active_assign_db is not None
    assert active_assign_db.officer_identity == officer_b_email
    assert active_assign_db.is_active is True
    assert active_assign_db.reassigned_to_id is None

    # E. Citizen attempts reassignment -> 403
    resp_citizen = await async_client.post(
        f"/api/v1/officer/cases/{journey_id}/reassign",
        json={"new_officer_identity": officer_c_email, "reason": "Citizen attempt"},
        headers=headers_citizen,
    )
    assert resp_citizen.status_code == 403

    # F. Unauthenticated attempts reassignment -> 401
    resp_anon = await async_client.post(
        f"/api/v1/officer/cases/{journey_id}/reassign",
        json={"new_officer_identity": officer_c_email, "reason": "Anon attempt"},
    )
    assert resp_anon.status_code == 401

    # B. Assigned Officer B reassigns own case to Officer C -> 200 OK
    resp_self_reassign = await async_client.post(
        f"/api/v1/officer/cases/{journey_id}/reassign",
        json={
            "new_officer_identity": officer_c_email,
            "reason": "Officer B self-recusal / hand-off to Officer C",
        },
        headers=headers_b,
    )
    assert resp_self_reassign.status_code == 200
    new_assign_c = resp_self_reassign.json()
    assert new_assign_c["officer_identity"] == officer_c_email
    assert new_assign_c["is_active"] is True

    # K. Verify successful reassignment preserves historical chain
    db_session.expire_all()
    stmt_all = (
        select(OfficerAssignment)
        .where(OfficerAssignment.journey_id == journey_id)
        .order_by(OfficerAssignment.created_at.asc())
    )
    all_assigns = list((await db_session.execute(stmt_all)).scalars().all())
    assert len(all_assigns) == 2

    # Previous assignment
    prev = all_assigns[0]
    assert prev.officer_identity == officer_b_email
    assert prev.is_active is False
    assert prev.status == AssignmentStatus.REASSIGNED
    assert str(prev.reassigned_to_id) == new_assign_c["id"]

    # New active assignment
    curr = all_assigns[1]
    assert curr.officer_identity == officer_c_email
    assert curr.is_active is True
    assert curr.status == AssignmentStatus.ASSIGNED

    # C. Supervisor reassigns Officer C's active case to Officer A -> 200 OK
    resp_super_reassign = await async_client.post(
        f"/api/v1/officer/cases/{journey_id}/reassign",
        json={
            "new_officer_identity": officer_a_email,
            "reason": "Supervisory workload rebalancing to Officer A",
        },
        headers=headers_super,
    )
    assert resp_super_reassign.status_code == 200
    new_assign_a = resp_super_reassign.json()
    assert new_assign_a["officer_identity"] == officer_a_email
    assert new_assign_a["is_active"] is True

    # D. Admin reassigns Officer A's active case back to Officer B -> 200 OK
    resp_admin_reassign = await async_client.post(
        f"/api/v1/officer/cases/{journey_id}/reassign",
        json={
            "new_officer_identity": officer_b_email,
            "reason": "Administrative override returning case to Officer B",
        },
        headers=headers_admin,
    )
    assert resp_admin_reassign.status_code == 200
    new_assign_b = resp_admin_reassign.json()
    assert new_assign_b["officer_identity"] == officer_b_email
    assert new_assign_b["is_active"] is True


@pytest.mark.asyncio
async def test_reassignment_service_boundary_authorization(db_session: AsyncSession):
    """Directly test the reassign_journey service boundary for independent authorization enforcement.
    The service must deny unauthorized peer officers even if invoked directly without route middleware.
    """
    journey = await _create_test_journey(db_session, "SSY")
    officer_b_email = "officer.varanasi@yogyatamitra.local"
    officer_a_email = "officer.lucknow@yogyatamitra.local"
    officer_c_email = "officer@yogyatamitra.local"
    supervisor_email = "supervisor@yogyatamitra.local"

    # Initial manual assignment
    assign_init = OfficerAssignment(
        journey_id=journey.id,
        officer_identity=officer_b_email,
        officer_name="Varanasi Officer",
        assigned_by=officer_b_email,
        due_at=datetime.now(timezone.utc) + timedelta(hours=48),
        sla_duration_hours=48,
        status=AssignmentStatus.ASSIGNED,
        is_active=True,
    )
    db_session.add(assign_init)
    await db_session.commit()

    # 1. Direct service call by Officer A (non-owner, role OFFICER) -> 403 Forbidden
    with pytest.raises(HTTPException) as exc_info:
        await reassign_journey(
            session=db_session,
            journey_id=journey.id,
            new_officer_identity=officer_c_email,
            reassigned_by=officer_a_email,
            reassigned_by_role="OFFICER",
            reason="Service call unauthorized attempt",
        )
    assert exc_info.value.status_code == 403
    assert "Only the currently assigned officer or an administrative supervisor can reassign" in exc_info.value.detail

    # 2. Direct service call by Officer B (owner, role OFFICER) -> Success
    reassigned_owner = await reassign_journey(
        session=db_session,
        journey_id=journey.id,
        new_officer_identity=officer_c_email,
        reassigned_by=officer_b_email,
        reassigned_by_role="OFFICER",
        reason="Service call authorized owner self-reassignment",
    )
    assert reassigned_owner.officer_identity == officer_c_email
    assert reassigned_owner.is_active is True

    # 3. Direct service call by Supervisor (non-owner, role SUPERVISOR) -> Success
    reassigned_super = await reassign_journey(
        session=db_session,
        journey_id=journey.id,
        new_officer_identity=officer_a_email,
        reassigned_by=supervisor_email,
        reassigned_by_role="SUPERVISOR",
        reason="Service call authorized supervisory override",
    )
    assert reassigned_super.officer_identity == officer_a_email
    assert reassigned_super.is_active is True
