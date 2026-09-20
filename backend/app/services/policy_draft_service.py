"""Policy Draft Service and Controlled Lifecycle State Machine.

Enforces strict human governance, separation of duties between author and reviewer,
mandatory substantive justification reasons, and immutable append-only audit logging.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple
import uuid

from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.engine.ast.validation import validate_ast
from app.engine.explainability.provenance import compute_canonical_rule_hash
from app.models.policy_discovery import CandidateReviewStatus, PolicyDiscoveryCandidate
from app.models.policy_draft import (
    PolicyDraft,
    PolicyDraftAuditEvent,
    PolicyDraftLifecycleStatus,
    PolicyDraftRevision,
    PolicyDraftTest,
    PolicyDraftTestStatus,
    PolicyDraftValidationStatus,
)
from app.models.scheme import PolicyVersion, Scheme
from app.schemas.policy_authoring import (
    PolicyDraftCreateRequest,
    PolicyDraftQueueMetrics,
    PolicyDraftUpdateRequest,
)
from app.services.policy_compiler_service import (
    compile_draft_ruleset,
    validate_draft_static_invariants,
)
from app.services.policy_test_service import verify_canonical_policy_regression

logger = logging.getLogger("yogyatamitra.services.policy_draft_service")


# ==============================================================================
# Legal Lifecycle Transitions Graph
# ==============================================================================

LEGAL_DRAFT_TRANSITIONS: Dict[Tuple[PolicyDraftLifecycleStatus, str], PolicyDraftLifecycleStatus] = {
    # DRAFT transitions
    (PolicyDraftLifecycleStatus.DRAFT, "START_AUTHORING"): PolicyDraftLifecycleStatus.AUTHORING,
    (PolicyDraftLifecycleStatus.DRAFT, "ARCHIVE"): PolicyDraftLifecycleStatus.ARCHIVED,

    # AUTHORING transitions
    (PolicyDraftLifecycleStatus.AUTHORING, "PAUSE_AUTHORING"): PolicyDraftLifecycleStatus.DRAFT,
    (PolicyDraftLifecycleStatus.AUTHORING, "RUN_VALIDATION"): PolicyDraftLifecycleStatus.VALIDATING,
    (PolicyDraftLifecycleStatus.AUTHORING, "ARCHIVE"): PolicyDraftLifecycleStatus.ARCHIVED,

    # VALIDATING transitions
    (PolicyDraftLifecycleStatus.VALIDATING, "RETURN_TO_AUTHORING"): PolicyDraftLifecycleStatus.AUTHORING,
    (PolicyDraftLifecycleStatus.VALIDATING, "PROCEED_TO_TESTING"): PolicyDraftLifecycleStatus.TESTING,

    # TESTING transitions
    (PolicyDraftLifecycleStatus.TESTING, "RETURN_TO_AUTHORING"): PolicyDraftLifecycleStatus.AUTHORING,
    (PolicyDraftLifecycleStatus.TESTING, "SUBMIT_FOR_REVIEW"): PolicyDraftLifecycleStatus.PENDING_REVIEW,

    # PENDING_REVIEW transitions
    (PolicyDraftLifecycleStatus.PENDING_REVIEW, "START_REVIEW"): PolicyDraftLifecycleStatus.IN_REVIEW,

    # IN_REVIEW determinations
    (PolicyDraftLifecycleStatus.IN_REVIEW, "STAGE"): PolicyDraftLifecycleStatus.STAGED,
    (PolicyDraftLifecycleStatus.IN_REVIEW, "REJECT"): PolicyDraftLifecycleStatus.REJECTED,
    (PolicyDraftLifecycleStatus.IN_REVIEW, "REQUEST_CLARIFICATION"): PolicyDraftLifecycleStatus.NEEDS_CLARIFICATION,

    # NEEDS_CLARIFICATION transitions
    (PolicyDraftLifecycleStatus.NEEDS_CLARIFICATION, "RESUME_AUTHORING"): PolicyDraftLifecycleStatus.AUTHORING,
    (PolicyDraftLifecycleStatus.NEEDS_CLARIFICATION, "RESUBMIT_FOR_REVIEW"): PolicyDraftLifecycleStatus.IN_REVIEW,

    # Terminal or Post-Review Archiving
    (PolicyDraftLifecycleStatus.REJECTED, "ARCHIVE"): PolicyDraftLifecycleStatus.ARCHIVED,
    (PolicyDraftLifecycleStatus.STAGED, "ARCHIVE"): PolicyDraftLifecycleStatus.ARCHIVED,
}


# ==============================================================================
# CRUD and Candidate Import Operations
# ==============================================================================

async def get_draft_detail(
    session: AsyncSession, draft_id: uuid.UUID
) -> Optional[PolicyDraft]:
    """Retrieve full policy draft with scheme, candidate, revisions, tests, and audit events."""
    stmt = (
        select(PolicyDraft)
        .execution_options(populate_existing=True)
        .options(
            selectinload(PolicyDraft.scheme),
            selectinload(PolicyDraft.source_candidate),
            selectinload(PolicyDraft.parent_policy_version),
            selectinload(PolicyDraft.audit_events),
            selectinload(PolicyDraft.revisions),
            selectinload(PolicyDraft.tests),
        )
        .where(PolicyDraft.id == draft_id)
    )
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def create_policy_draft(
    session: AsyncSession,
    payload: PolicyDraftCreateRequest,
    actor_email: str,
    actor_role: str,
) -> PolicyDraft:
    """Create a new policy draft in initial DRAFT lifecycle state."""
    # 1. Resolve Scheme
    code = payload.scheme_code.upper().strip()
    scheme_res = await session.execute(
        select(Scheme).where(Scheme.scheme_code == code)
    )
    scheme = scheme_res.scalars().first()
    if not scheme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scheme '{code}' not found.",
        )

    # 2. If source candidate provided, verify it is APPROVED
    candidate: Optional[PolicyDiscoveryCandidate] = None
    if payload.source_candidate_id:
        cand_res = await session.execute(
            select(PolicyDiscoveryCandidate).where(
                PolicyDiscoveryCandidate.id == payload.source_candidate_id
            )
        )
        candidate = cand_res.scalar_one_or_none()
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Policy discovery candidate '{payload.source_candidate_id}' not found.",
            )
        if candidate.review_status != CandidateReviewStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Candidate cannot be imported: status is '{candidate.review_status.value}'. "
                    "Only APPROVED candidates may be imported into policy drafts."
                ),
            )

    now = datetime.now(timezone.utc)
    draft_id = uuid.uuid4()

    authored_rules = payload.authored_rules_json or {}
    rule_hash = None
    if authored_rules and authored_rules.get("node_type"):
        try:
            validated = validate_ast(authored_rules)
            rule_hash = compute_canonical_rule_hash(validated)
        except Exception:
            rule_hash = None

    draft = PolicyDraft(
        id=draft_id,
        scheme_id=scheme.id,
        policy_title=payload.policy_title.strip(),
        description=payload.description.strip(),
        lifecycle_status=PolicyDraftLifecycleStatus.DRAFT,
        source_candidate_id=candidate.id if candidate else None,
        source_url=candidate.source_url if candidate else None,
        source_title=candidate.source_title if candidate else None,
        source_publisher=candidate.source_publisher if candidate else None,
        source_document_identifier=candidate.source_document_identifier if candidate else None,
        source_publication_date=candidate.source_publication_date if candidate else None,
        source_effective_date=candidate.source_effective_date if candidate else None,
        source_retrieved_at=candidate.retrieved_at if candidate else None,
        source_excerpt=candidate.source_excerpt if candidate else None,
        provenance_status=candidate.provenance_status.value if candidate else None,
        adversarial_flag_detected=candidate.adversarial_flag_detected if candidate else False,
        candidate_type=candidate.candidate_type.value if candidate else None,
        authored_rules_json=authored_rules,
        canonical_rules_json=authored_rules if rule_hash else None,
        rule_hash=rule_hash,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        parent_policy_version_id=payload.parent_policy_version_id,
        validation_status=PolicyDraftValidationStatus.NOT_VALIDATED,
        test_status=PolicyDraftTestStatus.NOT_TESTED,
        author_id=actor_email,
        author_role=actor_role,
        created_at=now,
        updated_at=now,
    )
    session.add(draft)

    # Initial revision snapshot
    revision = PolicyDraftRevision(
        id=uuid.uuid4(),
        draft_id=draft_id,
        revision_number=1,
        author_id=actor_email,
        author_role=actor_role,
        change_summary="Initial draft creation.",
        previous_rule_hash=None,
        new_rule_hash=rule_hash,
        rules_snapshot_json=authored_rules,
        created_at=now,
    )
    session.add(revision)

    # Initial audit event
    audit_event = PolicyDraftAuditEvent(
        id=uuid.uuid4(),
        draft_id=draft_id,
        actor_identity=actor_email,
        actor_role=actor_role,
        previous_status=None,
        new_status=PolicyDraftLifecycleStatus.DRAFT.value,
        action="CREATE_DRAFT",
        reason="Initial policy draft initiated by policy author.",
        details_json={
            "scheme_code": code,
            "source_candidate_id": str(candidate.id) if candidate else None,
        },
        created_at=now,
    )
    session.add(audit_event)

    await session.commit()
    return await get_draft_detail(session, draft_id)  # type: ignore[return-value]


async def import_candidate_into_draft(
    session: AsyncSession,
    draft_id: uuid.UUID,
    candidate_id: uuid.UUID,
    actor_email: str,
    actor_role: str,
) -> PolicyDraft:
    """Import an APPROVED discovery candidate into an existing draft.
    
    Copies provenance snapshot verbatim. Candidate record itself is never mutated.
    """
    draft = await get_draft_detail(session, draft_id)
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy draft '{draft_id}' not found.",
        )

    if draft.lifecycle_status not in (
        PolicyDraftLifecycleStatus.DRAFT,
        PolicyDraftLifecycleStatus.AUTHORING,
        PolicyDraftLifecycleStatus.NEEDS_CLARIFICATION,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot import candidate: draft is in '{draft.lifecycle_status.value}' state.",
        )

    cand_res = await session.execute(
        select(PolicyDiscoveryCandidate).where(PolicyDiscoveryCandidate.id == candidate_id)
    )
    candidate = cand_res.scalar_one_or_none()
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy discovery candidate '{candidate_id}' not found.",
        )

    if candidate.review_status != CandidateReviewStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Candidate cannot be imported: status is '{candidate.review_status.value}'. "
                "Only APPROVED candidates may be imported into policy drafts."
            ),
        )

    now = datetime.now(timezone.utc)
    draft.source_candidate_id = candidate.id
    draft.source_url = candidate.source_url
    draft.source_title = candidate.source_title
    draft.source_publisher = candidate.source_publisher
    draft.source_document_identifier = candidate.source_document_identifier
    draft.source_publication_date = candidate.source_publication_date
    draft.source_effective_date = candidate.source_effective_date
    draft.source_retrieved_at = candidate.retrieved_at
    draft.source_excerpt = candidate.source_excerpt
    draft.provenance_status = candidate.provenance_status.value
    draft.adversarial_flag_detected = candidate.adversarial_flag_detected
    draft.candidate_type = candidate.candidate_type.value
    draft.updated_at = now

    audit_event = PolicyDraftAuditEvent(
        id=uuid.uuid4(),
        draft_id=draft.id,
        actor_identity=actor_email,
        actor_role=actor_role,
        previous_status=draft.lifecycle_status.value,
        new_status=draft.lifecycle_status.value,
        action="IMPORT_CANDIDATE",
        reason=f"Imported approved candidate '{candidate.title}' ({candidate.id}).",
        details_json={
            "candidate_id": str(candidate.id),
            "source_url": candidate.source_url,
            "candidate_type": candidate.candidate_type.value,
        },
        created_at=now,
    )
    session.add(audit_event)
    await session.commit()
    return await get_draft_detail(session, draft_id)  # type: ignore[return-value]


async def update_policy_draft(
    session: AsyncSession,
    draft_id: uuid.UUID,
    payload: PolicyDraftUpdateRequest,
    actor_email: str,
    actor_role: str,
) -> PolicyDraft:
    """Update draft title, description, dates, or authored rules.
    
    Creates a new revision snapshot when rules change and resets validation/test status.
    """
    draft = await get_draft_detail(session, draft_id)
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy draft '{draft_id}' not found.",
        )

    if draft.lifecycle_status not in (
        PolicyDraftLifecycleStatus.DRAFT,
        PolicyDraftLifecycleStatus.AUTHORING,
        PolicyDraftLifecycleStatus.NEEDS_CLARIFICATION,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot edit draft in '{draft.lifecycle_status.value}' state. Must be in DRAFT, AUTHORING, or NEEDS_CLARIFICATION.",
        )

    now = datetime.now(timezone.utc)
    if payload.policy_title is not None:
        draft.policy_title = payload.policy_title.strip()
    if payload.description is not None:
        draft.description = payload.description.strip()
    if payload.effective_from is not None:
        draft.effective_from = payload.effective_from
    if payload.effective_to is not None:
        draft.effective_to = payload.effective_to
    if payload.change_summary is not None:
        draft.change_summary = payload.change_summary.strip()

    # If authored rules changed, calculate new hash and snapshot revision
    if payload.authored_rules_json is not None:
        old_hash = draft.rule_hash
        draft.authored_rules_json = payload.authored_rules_json

        new_hash = None
        if payload.authored_rules_json and payload.authored_rules_json.get("node_type"):
            try:
                validated = validate_ast(payload.authored_rules_json)
                new_hash = compute_canonical_rule_hash(validated)
            except Exception:
                new_hash = None

        draft.rule_hash = new_hash
        draft.canonical_rules_json = payload.authored_rules_json if new_hash else None

        # Invalidate validation and test status because rules changed
        draft.validation_status = PolicyDraftValidationStatus.NOT_VALIDATED
        draft.test_status = PolicyDraftTestStatus.NOT_TESTED

        # Determine revision number
        rev_count = len(draft.revisions) if draft.revisions else 0
        new_rev = PolicyDraftRevision(
            id=uuid.uuid4(),
            draft_id=draft.id,
            revision_number=rev_count + 1,
            author_id=actor_email,
            author_role=actor_role,
            change_summary=payload.change_summary or "Authored rules updated.",
            previous_rule_hash=old_hash,
            new_rule_hash=new_hash,
            rules_snapshot_json=payload.authored_rules_json,
            created_at=now,
        )
        session.add(new_rev)
        if draft.revisions is not None:
            draft.revisions.append(new_rev)

    draft.updated_at = now
    await session.commit()
    return await get_draft_detail(session, draft_id)  # type: ignore[return-value]


# ==============================================================================
# State Machine Lifecycle Transitions
# ==============================================================================

async def record_draft_transition(
    session: AsyncSession,
    draft_id: uuid.UUID,
    action: str,
    reason: str,
    actor_email: str,
    actor_role: str,
    notes: Optional[str] = None,
) -> PolicyDraft:
    """Execute a lifecycle state transition with mandatory substantive reason and RBAC."""
    draft = await get_draft_detail(session, draft_id)
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy draft '{draft_id}' not found.",
        )

    # 1. Terminal Check
    if draft.lifecycle_status == PolicyDraftLifecycleStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Policy draft is in terminal ARCHIVED state and cannot be transitioned.",
        )

    action_clean = action.upper().strip()
    curr_status = draft.lifecycle_status
    if isinstance(curr_status, str):
        curr_status = PolicyDraftLifecycleStatus(curr_status)

    target_status = LEGAL_DRAFT_TRANSITIONS.get((curr_status, action_clean))
    if not target_status:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Illegal transition: Cannot perform action '{action_clean}' from state '{curr_status.value}'.",
        )

    # 2. Mandatory Substantive Reason Enforcement
    if not reason or len(reason.strip()) < 5:
        raise HTTPException(
            status_code=422,
            detail=f"Mandatory substantive reason (minimum 5 characters) required for review transition '{action_clean}'.",
        )

    # 3. Prerequisites for SUBMIT_FOR_REVIEW (TESTING -> PENDING_REVIEW)
    if action_clean == "SUBMIT_FOR_REVIEW":
        if draft.validation_status != PolicyDraftValidationStatus.VALID:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot submit for review: Policy draft must pass static validation (VALID).",
            )
        if draft.test_status != PolicyDraftTestStatus.PASSED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot submit for review: Policy test suite must be fully executed and PASSED.",
            )
        # Verify statutory regression suite
        try:
            verify_canonical_policy_regression()
        except RuntimeError as err:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Statutory regression failed: {str(err)}",
            )

    # 4. Prerequisites for STAGE (IN_REVIEW -> STAGED)
    if action_clean == "STAGE":
        if actor_role != "SUPERVISOR":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation requires elevated SUPERVISOR role. Officers cannot stage policy.",
            )
        # Separation of duties: Author cannot approve their own draft
        if draft.author_id.lower() == actor_email.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Separation of duties violation: Author cannot approve and stage their own policy draft.",
            )

    # 5. Role restrictions for Supervisory Determinations (REJECT, REQUEST_CLARIFICATION)
    if action_clean in ("REJECT", "REQUEST_CLARIFICATION"):
        if actor_role != "SUPERVISOR":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Determination '{action_clean}' requires elevated SUPERVISOR role.",
            )

    now = datetime.now(timezone.utc)
    prev_status_str = curr_status.value

    # Update draft fields
    draft.lifecycle_status = target_status
    draft.updated_at = now

    if action_clean == "SUBMIT_FOR_REVIEW":
        draft.submitted_at = now
    elif action_clean in ("STAGE", "REJECT", "REQUEST_CLARIFICATION"):
        draft.reviewed_at = now
        draft.reviewed_by = actor_email
        draft.reviewed_by_role = actor_role
        draft.reviewer_reason = reason.strip()
        if action_clean == "STAGE":
            draft.staged_at = now
            draft.staged_by = actor_email
            draft.staged_by_role = actor_role

    # Append immutable audit event
    audit_event = PolicyDraftAuditEvent(
        id=uuid.uuid4(),
        draft_id=draft.id,
        actor_identity=actor_email,
        actor_role=actor_role,
        previous_status=prev_status_str,
        new_status=target_status.value,
        action=action_clean,
        reason=reason.strip(),
        details_json={"notes": notes} if notes else None,
        created_at=now,
    )
    session.add(audit_event)
    await session.commit()

    return await get_draft_detail(session, draft_id)  # type: ignore[return-value]


# ==============================================================================
# Queue Dashboard Metrics and Filtering
# ==============================================================================

async def get_drafts_queue(
    session: AsyncSession,
    status_filter: Optional[str] = None,
    scheme_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[PolicyDraft], int, PolicyDraftQueueMetrics]:
    """Query policy drafts with filtering, pagination, and aggregate status metrics."""
    # 1. All drafts for metrics
    all_stmt = select(PolicyDraft).options(
        selectinload(PolicyDraft.scheme),
        selectinload(PolicyDraft.source_candidate),
    )
    all_res = await session.execute(all_stmt)
    all_drafts = all_res.scalars().all()

    metrics_dict = {
        "total": len(all_drafts),
        "DRAFT": 0,
        "AUTHORING": 0,
        "VALIDATING": 0,
        "TESTING": 0,
        "PENDING_REVIEW": 0,
        "IN_REVIEW": 0,
        "NEEDS_CLARIFICATION": 0,
        "STAGED": 0,
        "ARCHIVED": 0,
    }
    for d in all_drafts:
        st = d.lifecycle_status.value if isinstance(d.lifecycle_status, PolicyDraftLifecycleStatus) else str(d.lifecycle_status)
        if st in metrics_dict:
            metrics_dict[st] += 1

    metrics = PolicyDraftQueueMetrics(
        total_drafts=metrics_dict["total"],
        draft_status_count=metrics_dict["DRAFT"],
        authoring=metrics_dict["AUTHORING"],
        validating=metrics_dict["VALIDATING"],
        testing=metrics_dict["TESTING"],
        pending_review=metrics_dict["PENDING_REVIEW"],
        in_review=metrics_dict["IN_REVIEW"],
        needs_clarification=metrics_dict["NEEDS_CLARIFICATION"],
        staged=metrics_dict["STAGED"],
        archived=metrics_dict["ARCHIVED"],
    )

    # 2. Filtering
    filtered = all_drafts
    if status_filter and status_filter.upper() != "ALL":
        filtered = [
            d for d in filtered
            if (d.lifecycle_status.value if isinstance(d.lifecycle_status, PolicyDraftLifecycleStatus) else str(d.lifecycle_status)) == status_filter.upper()
        ]

    if scheme_filter and scheme_filter.upper() != "ALL":
        filtered = [
            d for d in filtered
            if d.scheme and d.scheme.scheme_code.upper() == scheme_filter.upper()
        ]

    total_filtered = len(filtered)
    filtered.sort(key=lambda d: d.created_at, reverse=True)
    paginated = filtered[skip : skip + limit]

    return paginated, total_filtered, metrics
