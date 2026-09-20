"""Service layer for AI Policy Discovery, Candidate Queue, and Human Review Determinations.

Implements:
- AI discovery orchestration for PM-KISAN and SSY schemes
- Deterministic duplicate candidate detection
- Source conflict detection and flags
- Strict candidate lifecycle state machine
- Mandatory justification enforcement
- Append-only review audit trail logging
- Non-negotiable boundary: Candidate is non-executable proposal intelligence; never modifies AST/RuleSet.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.policy_discovery import (
    CandidateReviewStatus,
    CandidateType,
    DuplicateStatus,
    EffectiveDateStatus,
    PolicyDiscoveryCandidate,
    PolicyDiscoveryReviewEvent,
    ProvenanceStatus,
)
from app.models.scheme import Scheme
from app.services.ai.discovery_provider import (
    BasePolicyDiscoveryProvider,
    ExtractedCandidatePayload,
    PolicyDiscoveryProviderError,
    get_policy_discovery_provider,
)

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Legal State Transitions Map (STRICT - NO SHORTCUTS)
# ------------------------------------------------------------------------------

# The ONLY allowed transitions per Phase 15 Master Specification:
# PENDING_REVIEW -> IN_REVIEW (START_REVIEW)
# IN_REVIEW -> APPROVED (APPROVE)
# IN_REVIEW -> REJECTED (REJECT)
# IN_REVIEW -> NEEDS_CLARIFICATION (REQUEST_CLARIFICATION)
# NEEDS_CLARIFICATION -> IN_REVIEW (START_REVIEW)
# APPROVED -> ARCHIVED (ARCHIVE)
# REJECTED -> ARCHIVED (ARCHIVE)
# ARCHIVED -> no transitions (Terminal)
LEGAL_TRANSITIONS: Dict[Tuple[CandidateReviewStatus, str], CandidateReviewStatus] = {
    (CandidateReviewStatus.PENDING_REVIEW, "START_REVIEW"): CandidateReviewStatus.IN_REVIEW,
    (CandidateReviewStatus.IN_REVIEW, "APPROVE"): CandidateReviewStatus.APPROVED,
    (CandidateReviewStatus.IN_REVIEW, "REJECT"): CandidateReviewStatus.REJECTED,
    (CandidateReviewStatus.IN_REVIEW, "REQUEST_CLARIFICATION"): CandidateReviewStatus.NEEDS_CLARIFICATION,
    (CandidateReviewStatus.NEEDS_CLARIFICATION, "START_REVIEW"): CandidateReviewStatus.IN_REVIEW,
    (CandidateReviewStatus.APPROVED, "ARCHIVE"): CandidateReviewStatus.ARCHIVED,
    (CandidateReviewStatus.REJECTED, "ARCHIVE"): CandidateReviewStatus.ARCHIVED,
}


# ------------------------------------------------------------------------------
# Adversarial Content Detection & Provenance Helpers
# ------------------------------------------------------------------------------

ADVERSARIAL_INSTRUCTION_PATTERNS = [
    "ignore previous instructions",
    "ignore all previous instructions",
    "ignore prior instructions",
    "approve this rule",
    "approve this candidate",
    "bypass verification",
    "bypass review",
    "system prompt",
    "override security",
    "disregard guidelines",
    "you are now an administrator",
    "grant access immediately",
]


def detect_adversarial_content(text: str) -> bool:
    """Scan text for prompt injection and adversarial manipulation attempts."""
    if not text:
        return False
    t_lower = text.lower()
    return any(pattern in t_lower for pattern in ADVERSARIAL_INSTRUCTION_PATTERNS)


def compute_source_provenance(
    source_url: str,
    source_title: str,
    source_publisher: str,
    source_excerpt: str,
) -> ProvenanceStatus:
    """Determine provenance assurance level.
    
    CRITICAL DISTINCTION:
    - Official domain match (.gov.in / .nic.in) only confirms the host domain.
    - It does NOT verify statutory correctness, genuine enactment, or human endorsement.
    - Missing publisher or excerpt requires provenance review.
    - Non-official domains are UNVERIFIED.
    """
    if not source_title or not source_publisher or not source_excerpt:
        return ProvenanceStatus.PROVENANCE_REVIEW_REQUIRED

    url_lower = (source_url or "").lower().strip()
    parsed = urlparse(url_lower)
    hostname = parsed.hostname or ""
    if hostname.endswith(".gov.in") or hostname.endswith(".nic.in") or hostname in ("gov.in", "nic.in"):
        return ProvenanceStatus.OFFICIAL_DOMAIN_MATCH

    return ProvenanceStatus.UNVERIFIED


# ------------------------------------------------------------------------------
# Discovery Orchestration
# ------------------------------------------------------------------------------

async def discover_candidates_for_scheme(
    session: AsyncSession,
    scheme_code: str,
    actor_email: str,
    actor_role: str,
    provider: Optional[BasePolicyDiscoveryProvider] = None,
) -> List[PolicyDiscoveryCandidate]:
    """Execute AI discovery workflow for a scheme, detect duplicates, and persist candidates.
    
    Reliability & Security Invariants:
    - If AI provider fails, times out, or errors: surfaces HTTP 502 without creating candidates.
    - Never falls back to mock when an AI provider is configured.
    - Preserves source_excerpt verbatim (never destructively strips evidence).
    - Flags adversarial instruction content without allowing it to influence state.
    - Enforces non-executable candidate boundary.
    """
    # 1. Verify scheme exists
    s_stmt = select(Scheme).where(Scheme.scheme_code == scheme_code.upper().strip())
    s_res = await session.execute(s_stmt)
    scheme = s_res.scalar_one_or_none()
    if not scheme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Statutory scheme '{scheme_code}' not found in database",
        )

    if not provider:
        provider = get_policy_discovery_provider()

    # 2. Discover sources with safe error propagation (NO SILENT MOCK FALLBACK)
    try:
        sources = await provider.discover_sources(scheme.scheme_code)
    except Exception as exc:
        sanitized = str(exc).replace(getattr(settings, "GEMINI_API_KEY", "") or "___NOKEY___", "[REDACTED_API_KEY]")
        logger.error(
            "AI policy discovery provider '%s' failed during source discovery for scheme '%s': %s",
            provider.provider_name,
            scheme.scheme_code,
            sanitized,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI discovery provider failure ({provider.provider_name}): Discovery could not be completed. Zero candidate records created.",
        )

    if not sources:
        return []

    # 3. Extract candidate statements with safe error propagation
    try:
        extracted_payloads = await provider.extract_candidates(scheme.scheme_code, sources)
    except Exception as exc:
        sanitized = str(exc).replace(getattr(settings, "GEMINI_API_KEY", "") or "___NOKEY___", "[REDACTED_API_KEY]")
        logger.error(
            "AI policy discovery provider '%s' failed during candidate extraction for scheme '%s': %s",
            provider.provider_name,
            scheme.scheme_code,
            sanitized,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI extraction provider failure ({provider.provider_name}): Candidate extraction could not be completed. Zero candidate records created.",
        )

    if not extracted_payloads:
        return []

    # 4. Process each candidate: Duplicate Detection, Verbatim Preservation & Persistence
    now = datetime.now(timezone.utc)
    created_candidates: List[PolicyDiscoveryCandidate] = []

    for payload in extracted_payloads:
        # Check deterministic duplicate: same scheme + same normalized_concept + same candidate_type
        dup_stmt = (
            select(PolicyDiscoveryCandidate)
            .where(
                PolicyDiscoveryCandidate.scheme_id == scheme.id,
                PolicyDiscoveryCandidate.normalized_concept == payload.normalized_concept,
                PolicyDiscoveryCandidate.candidate_type == payload.candidate_type,
            )
            .order_by(desc(PolicyDiscoveryCandidate.created_at))
            .limit(1)
        )
        dup_res = await session.execute(dup_stmt)
        existing_candidate = dup_res.scalars().first()

        dup_status = DuplicateStatus.UNIQUE
        dup_of_id = None
        if existing_candidate:
            dup_status = DuplicateStatus.POSSIBLE_DUPLICATE
            dup_of_id = existing_candidate.id

        # Preserve verbatim source excerpt without destructive stripping
        verbatim_excerpt = payload.source_excerpt

        # Detect adversarial instruction content (prompt injection)
        has_adversarial = (
            detect_adversarial_content(verbatim_excerpt)
            or detect_adversarial_content(payload.candidate_text_en)
            or detect_adversarial_content(payload.title)
        )

        # Compute provenance assurance level
        prov_status = compute_source_provenance(
            source_url=payload.source_url,
            source_title=payload.source_title,
            source_publisher=payload.source_publisher,
            source_excerpt=verbatim_excerpt,
        )

        candidate_id = uuid.uuid4()
        candidate = PolicyDiscoveryCandidate(
            id=candidate_id,
            scheme_id=scheme.id,
            title=payload.title,
            candidate_type=payload.candidate_type,
            candidate_text_en=payload.candidate_text_en,
            candidate_text_hi=payload.candidate_text_hi,
            normalized_concept=payload.normalized_concept,
            source_url=payload.source_url,
            source_title=payload.source_title,
            source_publisher=payload.source_publisher,
            source_document_identifier=payload.source_document_identifier,
            source_publication_date=payload.source_publication_date,
            source_effective_date=payload.source_effective_date,
            source_excerpt=verbatim_excerpt,  # VERBATIM preservation
            discovered_at=now,
            retrieved_at=now,
            adversarial_flag_detected=has_adversarial,
            discovered_by=actor_email,
            ai_provider=provider.provider_name,
            ai_model=provider.model_name,
            ai_run_id=f"run-{uuid.uuid4().hex[:12]}",
            extraction_confidence=payload.extraction_confidence,
            confidence_explanation=payload.confidence_explanation,
            uncertainty_notes=payload.uncertainty_notes,
            questions_for_reviewer=payload.questions_for_reviewer,
            provenance_status=prov_status,
            effective_date_status=payload.effective_date_status,
            conflict_detected=payload.conflict_detected,
            conflict_details_json=payload.conflict_details_json,
            duplicate_status=dup_status,
            duplicate_of_id=dup_of_id,
            review_status=CandidateReviewStatus.PENDING_REVIEW,
        )
        session.add(candidate)

        # Initial audit event
        audit_event = PolicyDiscoveryReviewEvent(
            id=uuid.uuid4(),
            candidate_id=candidate_id,
            actor_identity=actor_email,
            actor_role=actor_role,
            previous_status=None,
            new_status=CandidateReviewStatus.PENDING_REVIEW.value,
            action="DISCOVER",
            reason="Discovered by automated AI policy discovery agent from official source.",
            details_json={
                "source_url": payload.source_url,
                "confidence": payload.extraction_confidence,
                "ai_provider": provider.provider_name,
                "adversarial_flag_detected": has_adversarial,
            },
            created_at=now,
        )
        session.add(audit_event)
        created_candidates.append(candidate)

    await session.commit()

    # Re-query with scheme loaded
    ids = [c.id for c in created_candidates]
    ret_stmt = (
        select(PolicyDiscoveryCandidate)
        .options(
            selectinload(PolicyDiscoveryCandidate.scheme),
            selectinload(PolicyDiscoveryCandidate.review_events),
        )
        .where(PolicyDiscoveryCandidate.id.in_(ids))
    )
    res = await session.execute(ret_stmt)
    return list(res.scalars().all())


async def get_candidates_queue(
    session: AsyncSession,
    status_filter: Optional[str] = None,
    scheme_filter: Optional[str] = None,
    candidate_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[PolicyDiscoveryCandidate], int, Dict[str, int]]:
    """Query candidate queue with filtering, pagination, and aggregate status metrics."""
    # 1. Query all candidates for metrics
    all_stmt = select(PolicyDiscoveryCandidate).options(
        selectinload(PolicyDiscoveryCandidate.scheme),
        selectinload(PolicyDiscoveryCandidate.review_events),
    )
    all_res = await session.execute(all_stmt)
    all_candidates = all_res.scalars().all()

    metrics = {
        "total_candidates": len(all_candidates),
        "pending_review": 0,
        "in_review": 0,
        "needs_clarification": 0,
        "approved": 0,
        "rejected": 0,
        "archived": 0,
        "conflict_detected": 0,
    }
    for c in all_candidates:
        st = c.review_status.value if isinstance(c.review_status, CandidateReviewStatus) else str(c.review_status)
        if st == CandidateReviewStatus.PENDING_REVIEW.value:
            metrics["pending_review"] += 1
        elif st == CandidateReviewStatus.IN_REVIEW.value:
            metrics["in_review"] += 1
        elif st == CandidateReviewStatus.NEEDS_CLARIFICATION.value:
            metrics["needs_clarification"] += 1
        elif st == CandidateReviewStatus.APPROVED.value:
            metrics["approved"] += 1
        elif st == CandidateReviewStatus.REJECTED.value:
            metrics["rejected"] += 1
        elif st == CandidateReviewStatus.ARCHIVED.value:
            metrics["archived"] += 1

        if c.conflict_detected:
            metrics["conflict_detected"] += 1

    # 2. Filtered query
    filtered = all_candidates
    if status_filter and status_filter.upper() != "ALL":
        filtered = [
            c for c in filtered
            if (c.review_status.value if isinstance(c.review_status, CandidateReviewStatus) else str(c.review_status)) == status_filter.upper()
        ]

    if scheme_filter and scheme_filter.upper() != "ALL":
        filtered = [
            c for c in filtered
            if c.scheme and c.scheme.scheme_code.upper() == scheme_filter.upper()
        ]

    if candidate_type and candidate_type.upper() != "ALL":
        filtered = [
            c for c in filtered
            if (c.candidate_type.value if isinstance(c.candidate_type, CandidateType) else str(c.candidate_type)) == candidate_type.upper()
        ]

    total_filtered = len(filtered)
    # Sort descending by created_at
    filtered.sort(key=lambda c: c.created_at, reverse=True)
    paginated = filtered[skip : skip + limit]

    return paginated, total_filtered, metrics


async def get_candidate_detail(
    session: AsyncSession, candidate_id: uuid.UUID
) -> Optional[PolicyDiscoveryCandidate]:
    """Retrieve full candidate dossier with scheme and review events."""
    stmt = (
        select(PolicyDiscoveryCandidate)
        .options(
            selectinload(PolicyDiscoveryCandidate.scheme),
            selectinload(PolicyDiscoveryCandidate.review_events),
        )
        .where(PolicyDiscoveryCandidate.id == candidate_id)
    )
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def record_candidate_review(
    session: AsyncSession,
    candidate_id: uuid.UUID,
    action: str,
    reason: str,
    actor_email: str,
    actor_role: str,
    notes: Optional[str] = None,
) -> PolicyDiscoveryCandidate:
    """Record an official reviewer determination on a discovered policy candidate."""
    candidate = await get_candidate_detail(session, candidate_id)
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy discovery candidate '{candidate_id}' not found",
        )

    # Check terminal state
    if candidate.review_status == CandidateReviewStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Candidate is in terminal ARCHIVED state and cannot be modified",
        )

    action_clean = action.upper().strip()

    # Validate state transition
    curr_status = candidate.review_status
    if isinstance(curr_status, str):
        curr_status = CandidateReviewStatus(curr_status)

    target_status = LEGAL_TRANSITIONS.get((curr_status, action_clean))
    if not target_status:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Illegal transition: Cannot perform action '{action_clean}' from state '{curr_status.value}'",
        )

    # Mandatory substantive reason enforcement for all transitions
    if not reason or len(reason.strip()) < 5:
        raise HTTPException(
            status_code=422,
            detail=f"Mandatory substantive reason (minimum 5 characters) required for review transition '{action_clean}'",
        )

    now = datetime.now(timezone.utc)
    prev_status_str = curr_status.value

    # Update candidate fields
    candidate.review_status = target_status
    candidate.reviewer_id = actor_email
    candidate.reviewer_role = actor_role
    candidate.reviewed_at = now
    candidate.reviewer_reason = reason.strip() if reason else None
    candidate.updated_at = now

    # Append immutable audit event
    audit_event = PolicyDiscoveryReviewEvent(
        id=uuid.uuid4(),
        candidate_id=candidate.id,
        actor_identity=actor_email,
        actor_role=actor_role,
        previous_status=prev_status_str,
        new_status=target_status.value,
        action=action_clean,
        reason=reason.strip() if reason else "Status transitioned by reviewer.",
        details_json={"notes": notes} if notes else None,
        created_at=now,
    )
    session.add(audit_event)
    await session.commit()

    # Return refreshed candidate
    return await get_candidate_detail(session, candidate_id)  # type: ignore[return-value]


async def get_candidate_history(
    session: AsyncSession, candidate_id: uuid.UUID
) -> List[PolicyDiscoveryReviewEvent]:
    """Retrieve chronological append-only audit events for a policy candidate."""
    stmt = (
        select(PolicyDiscoveryReviewEvent)
        .where(PolicyDiscoveryReviewEvent.candidate_id == candidate_id)
        .order_by(PolicyDiscoveryReviewEvent.created_at.asc())
    )
    res = await session.execute(stmt)
    return list(res.scalars().all())
