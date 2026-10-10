"""Officer Assignment, Workload Balancing, and SLA Management Service (Phase D).

Implements:
- Deterministic least-loaded workload balancing assignment
- Manual assignment and historical reassignment preserving previous records
- Configurable capacity limits and SLA tracking
- Due date and SLA status computation (NOT_DUE, DUE_SOON, OVERDUE, COMPLETED)
- Real database-driven aggregate workload metrics
- Comprehensive immutable audit trail logging
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.security import get_demo_users
from app.models.assignment import OfficerAssignment
from app.models.citizen import Citizen
from app.models.enums import (
    AssignmentStatus,
    HumanReviewStatus,
    JourneyState,
    SLAStatus,
)
from app.models.human_review import HumanReview, HumanReviewAuditEvent
from app.models.journey import EvaluationJourney


def compute_sla_status(
    due_at: datetime,
    assignment_status: AssignmentStatus,
    now: Optional[datetime] = None,
) -> SLAStatus:
    """Deterministically calculate operational SLA compliance status."""
    if assignment_status == AssignmentStatus.COMPLETED:
        return SLAStatus.COMPLETED

    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    if due_at.tzinfo is None:
        due_at = due_at.replace(tzinfo=timezone.utc)

    if now > due_at:
        return SLAStatus.OVERDUE

    due_soon_threshold = due_at - timedelta(hours=settings.OFFICER_SLA_DUE_SOON_HOURS)
    if now >= due_soon_threshold:
        return SLAStatus.DUE_SOON

    return SLAStatus.NOT_DUE


def get_eligible_officers() -> List[Dict[str, Any]]:
    """Return all active eligible officers for case assignment, deterministically ordered."""
    users = get_demo_users()
    officers = [
        u for u in users.values()
        if u.get("role") in ("OFFICER", "SUPERVISOR")
    ]
    # Deterministic sorting by email
    return sorted(officers, key=lambda x: x["email"])


def find_officer_by_identity(identity: str) -> Optional[Dict[str, Any]]:
    """Look up an eligible officer by identity / email."""
    for officer in get_eligible_officers():
        if officer["email"].lower() == identity.lower():
            return officer
    return None


async def calculate_officer_workloads(session: AsyncSession) -> Dict[str, int]:
    """Calculate the number of active cases currently assigned to each officer."""
    stmt = (
        select(OfficerAssignment.officer_identity, func.count(OfficerAssignment.id))
        .where(
            OfficerAssignment.is_active == True,
            OfficerAssignment.status.in_([AssignmentStatus.ASSIGNED, AssignmentStatus.IN_PROGRESS]),
        )
        .group_by(OfficerAssignment.officer_identity)
    )
    res = await session.execute(stmt)
    workload_map: Dict[str, int] = {row[0]: row[1] for row in res.all()}
    return workload_map


async def get_active_assignment_for_journey(
    session: AsyncSession, journey_id: uuid.UUID
) -> Optional[OfficerAssignment]:
    """Retrieve the currently active assignment for a given journey."""
    stmt = (
        select(OfficerAssignment)
        .where(
            OfficerAssignment.journey_id == journey_id,
            OfficerAssignment.is_active == True,
        )
    )
    res = await session.execute(stmt)
    return res.scalars().first()


async def get_assignment_history(
    session: AsyncSession, journey_id: uuid.UUID
) -> List[OfficerAssignment]:
    """Retrieve the complete historical audit of assignments for a journey."""
    stmt = (
        select(OfficerAssignment)
        .where(OfficerAssignment.journey_id == journey_id)
        .order_by(desc(OfficerAssignment.created_at))
    )
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def assign_journey_auto(
    session: AsyncSession,
    journey_id: uuid.UUID,
    sla_hours: Optional[int] = None,
) -> OfficerAssignment:
    """Deterministically assign an unassigned journey using least-loaded workload balancing.

    No AI, no opaque scoring. Balances workload across active officers below capacity limit.
    """
    # 1. Fetch journey and verify assignability
    stmt = select(EvaluationJourney).where(EvaluationJourney.id == journey_id)
    res = await session.execute(stmt)
    journey = res.scalars().first()
    if not journey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation journey with ID '{journey_id}' was not found",
        )

    if journey.state in (JourneyState.DRAFT, JourneyState.COMPLETED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot assign journey in '{journey.state.value}' state. Must be submitted/in-progress.",
        )

    # 2. Check if an active assignment already exists
    active_assignment = await get_active_assignment_for_journey(session, journey_id)
    if active_assignment:
        return active_assignment

    # 3. Discover eligible officers
    eligible_officers = get_eligible_officers()
    if not eligible_officers:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No eligible active officers available for case assignment",
        )

    # 4. Deterministic least-loaded selection
    workload_map = await calculate_officer_workloads(session)
    max_capacity = settings.OFFICER_MAX_ACTIVE_CASES

    # Filter officers below capacity, or fallback to all officers if all at capacity
    available = [
        o for o in eligible_officers
        if workload_map.get(o["email"], 0) < max_capacity
    ]
    candidate_pool = available if available else eligible_officers

    # Pick officer with lowest workload; tie-break alphabetically by email
    chosen_officer = min(
        candidate_pool,
        key=lambda o: (workload_map.get(o["email"], 0), o["email"]),
    )

    now = datetime.now(timezone.utc)
    duration = sla_hours or settings.OFFICER_DEFAULT_SLA_HOURS
    due_at = now + timedelta(hours=duration)

    assignment = OfficerAssignment(
        journey_id=journey.id,
        officer_identity=chosen_officer["email"],
        officer_name=chosen_officer.get("name"),
        assigned_by="SYSTEM_BALANCER",
        assigned_at=now,
        due_at=due_at,
        sla_duration_hours=duration,
        status=AssignmentStatus.ASSIGNED,
        is_active=True,
    )
    session.add(assignment)
    await session.flush()

    # Sync HumanReview record
    rev_stmt = select(HumanReview).where(HumanReview.journey_id == journey.id)
    rev_res = await session.execute(rev_stmt)
    human_review = rev_res.scalars().first()
    if not human_review:
        human_review = HumanReview(
            journey_id=journey.id,
            reviewer_identity=chosen_officer["email"],
            reviewer_role=chosen_officer.get("role", "OFFICER"),
            status=HumanReviewStatus.PENDING,
        )
        session.add(human_review)
        await session.flush()
    else:
        human_review.reviewer_identity = chosen_officer["email"]
        human_review.reviewer_role = chosen_officer.get("role", "OFFICER")

    # Record append-only audit event
    audit_event = HumanReviewAuditEvent(
        review_id=human_review.id,
        journey_id=journey.id,
        actor_identity="SYSTEM_BALANCER",
        actor_role="SYSTEM",
        action="OFFICER_ASSIGNED_AUTO",
        previous_status=None,
        new_status=chosen_officer["email"],
        reason="Deterministic least-loaded workload balancing assignment",
        details_json={
            "assignment_id": str(assignment.id),
            "assigned_officer": chosen_officer["email"],
            "due_at": due_at.isoformat(),
            "sla_duration_hours": duration,
            "current_workload_count": workload_map.get(chosen_officer["email"], 0),
        },
    )
    session.add(audit_event)
    await session.commit()
    await session.refresh(assignment)

    return assignment


async def assign_journey_manual(
    session: AsyncSession,
    journey_id: uuid.UUID,
    officer_identity: str,
    assigned_by: str,
    assigned_by_role: str = "OFFICER",
    sla_hours: Optional[int] = None,
    reason: Optional[str] = None,
) -> OfficerAssignment:
    """Manually assign or reassign an evaluation journey to a specific verified officer."""
    officer = find_officer_by_identity(officer_identity)
    if not officer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Officer '{officer_identity}' does not exist or is not eligible for assignment",
        )

    stmt = select(EvaluationJourney).where(EvaluationJourney.id == journey_id)
    res = await session.execute(stmt)
    journey = res.scalars().first()
    if not journey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation journey with ID '{journey_id}' was not found",
        )

    if journey.state in (JourneyState.DRAFT, JourneyState.COMPLETED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot assign journey in '{journey.state.value}' state. Must be submitted/in-progress.",
        )

    active_assignment = await get_active_assignment_for_journey(session, journey_id)
    now = datetime.now(timezone.utc)
    duration = sla_hours or settings.OFFICER_DEFAULT_SLA_HOURS
    due_at = now + timedelta(hours=duration)

    if active_assignment:
        if active_assignment.officer_identity.lower() == officer_identity.lower():
            return active_assignment

        # Reassigning an active case requires current assignee ownership or SUPERVISOR/ADMIN role
        actor_identity = (assigned_by or "").strip().lower()
        current_assignee = (active_assignment.officer_identity or "").strip().lower()
        is_assignee = (actor_identity == current_assignee)
        is_elevated = (assigned_by_role in ("SUPERVISOR", "ADMIN"))

        if not (is_assignee or is_elevated):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: Case is already actively assigned. Only the assigned officer or an administrative supervisor can reassign it.",
            )

        # Deactivate existing assignment without destroying historical record
        active_assignment.is_active = False
        active_assignment.status = AssignmentStatus.REASSIGNED
        active_assignment.reassignment_reason = reason or f"Reassigned to {officer['email']} by {assigned_by}"

    new_assignment = OfficerAssignment(
        journey_id=journey.id,
        officer_identity=officer["email"],
        officer_name=officer.get("name"),
        assigned_by=assigned_by,
        assigned_at=now,
        due_at=due_at,
        sla_duration_hours=duration,
        status=AssignmentStatus.ASSIGNED,
        is_active=True,
    )
    session.add(new_assignment)
    await session.flush()

    if active_assignment:
        active_assignment.reassigned_to_id = new_assignment.id

    # Sync HumanReview
    rev_stmt = select(HumanReview).where(HumanReview.journey_id == journey.id)
    rev_res = await session.execute(rev_stmt)
    human_review = rev_res.scalars().first()
    if not human_review:
        human_review = HumanReview(
            journey_id=journey.id,
            reviewer_identity=officer["email"],
            reviewer_role=officer.get("role", "OFFICER"),
            status=HumanReviewStatus.PENDING,
        )
        session.add(human_review)
        await session.flush()
    else:
        human_review.reviewer_identity = officer["email"]
        human_review.reviewer_role = officer.get("role", "OFFICER")

    # Record append-only audit event
    action_name = "OFFICER_REASSIGNED" if active_assignment else "OFFICER_ASSIGNED_MANUAL"
    audit_event = HumanReviewAuditEvent(
        review_id=human_review.id,
        journey_id=journey.id,
        actor_identity=assigned_by,
        actor_role=assigned_by_role,
        action=action_name,
        previous_status=active_assignment.officer_identity if active_assignment else None,
        new_status=officer["email"],
        reason=reason or ("Manual assignment" if not active_assignment else "Manual reassignment"),
        details_json={
            "assignment_id": str(new_assignment.id),
            "previous_assignment_id": str(active_assignment.id) if active_assignment else None,
            "assigned_officer": officer["email"],
            "due_at": due_at.isoformat(),
            "sla_duration_hours": duration,
        },
    )
    session.add(audit_event)
    await session.commit()
    await session.refresh(new_assignment)

    return new_assignment


async def reassign_journey(
    session: AsyncSession,
    journey_id: uuid.UUID,
    new_officer_identity: str,
    reassigned_by: str,
    reassigned_by_role: str = "OFFICER",
    reason: str = "",
    sla_hours: Optional[int] = None,
) -> OfficerAssignment:
    """Reassign an active case to a new officer, strictly requiring an auditable reason.

    Authorization Invariants:
    - ALLOW if reassigned_by == active_assignment.officer_identity (assigned officer hand-off/self-recusal).
    - ALLOW if reassigned_by_role in ("SUPERVISOR", "ADMIN") (administrative supervisory override).
    - DENY with HTTP 403 if a regular officer attempts to reassign another officer's case.
    """
    clean_reason = reason.strip() if reason else ""
    if not clean_reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A substantive reason is required when reassigning an active case",
        )

    active_assignment = await get_active_assignment_for_journey(session, journey_id)
    if not active_assignment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reassign: No active officer assignment exists for this case. Use manual assign instead.",
        )

    # Enforce object-level authorization: caller must be current assignee or supervisor/admin
    actor_identity = (reassigned_by or "").strip().lower()
    current_assignee = (active_assignment.officer_identity or "").strip().lower()
    is_assignee = (actor_identity == current_assignee)
    is_elevated = (reassigned_by_role in ("SUPERVISOR", "ADMIN"))

    if not (is_assignee or is_elevated):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Only the currently assigned officer or an administrative supervisor can reassign an active case.",
        )

    if active_assignment.officer_identity.lower() == new_officer_identity.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Case is already assigned to officer '{new_officer_identity}'",
        )

    return await assign_journey_manual(
        session=session,
        journey_id=journey_id,
        officer_identity=new_officer_identity,
        assigned_by=reassigned_by,
        assigned_by_role=reassigned_by_role,
        sla_hours=sla_hours,
        reason=clean_reason,
    )


async def get_officer_workload_metrics(
    session: AsyncSession,
    officer_identity: Optional[str] = None,
) -> Dict[str, Any]:
    """Compute comprehensive database-backed workload and SLA metrics.

    All counts derive directly from persisted assignments and journeys. No fake data.
    """
    now = datetime.now(timezone.utc)
    due_soon_threshold = now + timedelta(hours=settings.OFFICER_SLA_DUE_SOON_HOURS)

    # 1. My Active Requests
    my_active = 0
    if officer_identity:
        my_stmt = select(func.count(OfficerAssignment.id)).where(
            OfficerAssignment.officer_identity == officer_identity,
            OfficerAssignment.is_active == True,
            OfficerAssignment.status.in_([AssignmentStatus.ASSIGNED, AssignmentStatus.IN_PROGRESS]),
        )
        my_active = (await session.execute(my_stmt)).scalar() or 0

    # 2. Total Active Workload (all officers)
    total_active_stmt = select(func.count(OfficerAssignment.id)).where(
        OfficerAssignment.is_active == True,
        OfficerAssignment.status.in_([AssignmentStatus.ASSIGNED, AssignmentStatus.IN_PROGRESS]),
    )
    total_active = (await session.execute(total_active_stmt)).scalar() or 0

    # 3. Unassigned Requests (journeys in submitted/operational states with no active assignment)
    unassigned_stmt = (
        select(func.count(EvaluationJourney.id))
        .where(
            EvaluationJourney.state.notin_([JourneyState.DRAFT, JourneyState.COMPLETED]),
            ~EvaluationJourney.id.in_(
                select(OfficerAssignment.journey_id).where(OfficerAssignment.is_active == True)
            ),
        )
    )
    unassigned = (await session.execute(unassigned_stmt)).scalar() or 0

    # 4. Due Soon Requests (active assignments where due_at is between now and threshold)
    due_soon_stmt = select(func.count(OfficerAssignment.id)).where(
        OfficerAssignment.is_active == True,
        OfficerAssignment.status.in_([AssignmentStatus.ASSIGNED, AssignmentStatus.IN_PROGRESS]),
        OfficerAssignment.due_at >= now,
        OfficerAssignment.due_at <= due_soon_threshold,
    )
    due_soon = (await session.execute(due_soon_stmt)).scalar() or 0

    # 5. Overdue Requests (active assignments where due_at < now)
    overdue_stmt = select(func.count(OfficerAssignment.id)).where(
        OfficerAssignment.is_active == True,
        OfficerAssignment.status.in_([AssignmentStatus.ASSIGNED, AssignmentStatus.IN_PROGRESS]),
        OfficerAssignment.due_at < now,
    )
    overdue = (await session.execute(overdue_stmt)).scalar() or 0

    # 6. Completed Requests
    completed_stmt = select(func.count(OfficerAssignment.id)).where(
        OfficerAssignment.status == AssignmentStatus.COMPLETED,
    )
    completed = (await session.execute(completed_stmt)).scalar() or 0

    return {
        "my_active_requests": my_active,
        "unassigned_requests": unassigned,
        "due_soon": due_soon,
        "overdue": overdue,
        "completed": completed,
        "total_active_workload": total_active,
        "max_capacity_per_officer": settings.OFFICER_MAX_ACTIVE_CASES,
        "default_sla_duration_hours": settings.OFFICER_DEFAULT_SLA_HOURS,
    }
