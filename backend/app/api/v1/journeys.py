"""Citizen Journey & Evidence Workflow Endpoints.

Provides stateful lifecycle management for citizen welfare entitlement journeys:
- Creation, retrieval, and explicit state progression
- Factual claims registration and querying
- Evidence submission and multi-actor verification
- Statutory evaluation trigger and state synchronization
"""

from __future__ import annotations

from typing import List
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.citizen import Claim, Evidence
from app.models.journey import EvaluationJourney
from app.schemas.api import ErrorResponse
from app.schemas.journey import (
    EvidenceVerificationRequest,
    JourneyClaimCreateRequest,
    JourneyClaimResponse,
    JourneyCreateRequest,
    JourneyDetailResponse,
    JourneyEvaluateRequest,
    JourneyEvaluationResponse,
    JourneyEvidenceCreateRequest,
    JourneyEvidenceResponse,
    JourneyResponse,
    JourneyTransitionRecordResponse,
    JourneyTransitionRequest,
    JourneyVerificationRecordResponse,
)
from app.services.evaluation_service import (
    CitizenNotFoundError,
    EvaluationNotFoundError,
    PolicyVersionConflictError,
)
from app.services.journey_service import (
    ClaimNotFoundError,
    EvidenceNotFoundError,
    InvalidEvidenceTransitionError,
    InvalidJourneyTransitionError,
    JourneyNotFoundError,
    JourneyService,
)
from app.services.policy_loader import SchemeNotFoundError
from app.services.policy_selector import PolicyVersionNotFoundError

router = APIRouter(prefix="/journeys", tags=["Journeys"])


# ==============================================================================
# Helper Transformers
# ==============================================================================

def to_journey_evidence_response(evidence: Evidence) -> JourneyEvidenceResponse:
    """Transform Evidence model to JourneyEvidenceResponse."""
    return JourneyEvidenceResponse(
        id=evidence.id,
        claim_id=evidence.claim_id,
        evidence_type=evidence.evidence_type,
        storage_reference=evidence.storage_reference,
        metadata_json=evidence.metadata_json,
        status=evidence.status,
        rejection_reason=evidence.rejection_reason,
        submitted_at=evidence.submitted_at,
        verified_at=evidence.verified_at,
        rejected_at=evidence.rejected_at,
        verification_records=[
            JourneyVerificationRecordResponse.model_validate(vr)
            for vr in (evidence.verification_records or [])
        ],
    )


def to_journey_claim_response(claim: Claim) -> JourneyClaimResponse:
    """Transform Claim model to JourneyClaimResponse."""
    return JourneyClaimResponse(
        id=claim.id,
        journey_id=claim.journey_id,
        citizen_id=claim.citizen_id,
        claim_type=claim.claim_type,
        value_json=claim.value_json,
        source=claim.source,
        status=claim.status,
        claimed_at=claim.claimed_at,
        updated_at=claim.updated_at,
        evidence_items=[
            to_journey_evidence_response(e)
            for e in (claim.evidence_items or [])
        ],
    )


def to_journey_response(journey: EvaluationJourney) -> JourneyResponse:
    """Transform EvaluationJourney to summary JourneyResponse."""
    return JourneyResponse(
        id=journey.id,
        citizen_id=journey.citizen_id,
        citizen_ref=journey.citizen.synthetic_reference if journey.citizen else "",
        scheme_id=journey.scheme_id,
        scheme_code=journey.scheme.scheme_code if journey.scheme else "",
        state=journey.state,
        latest_evaluation_id=journey.latest_evaluation_id,
        created_at=journey.created_at,
        updated_at=journey.updated_at,
    )


def to_journey_detail_response(journey: EvaluationJourney) -> JourneyDetailResponse:
    """Transform EvaluationJourney to detailed JourneyDetailResponse."""
    return JourneyDetailResponse(
        id=journey.id,
        citizen_id=journey.citizen_id,
        citizen_ref=journey.citizen.synthetic_reference if journey.citizen else "",
        scheme_id=journey.scheme_id,
        scheme_code=journey.scheme.scheme_code if journey.scheme else "",
        state=journey.state,
        latest_evaluation_id=journey.latest_evaluation_id,
        created_at=journey.created_at,
        updated_at=journey.updated_at,
        claims=[to_journey_claim_response(c) for c in (journey.claims or [])],
        transitions=[
            JourneyTransitionRecordResponse.model_validate(t)
            for t in (journey.transitions or [])
        ],
    )


# ==============================================================================
# Journey Endpoints
# ==============================================================================

@router.post(
    "",
    response_model=JourneyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate a new citizen evaluation journey",
    description="Creates a new journey for a citizen under a specific statutory scheme. Initial state is DRAFT (or FACTS_COLLECTED if initial facts provided).",
    responses={
        201: {"description": "Journey successfully created."},
        404: {"model": ErrorResponse, "description": "Scheme not found."},
        422: {"model": ErrorResponse, "description": "Validation error on payload."},
    },
)
async def create_journey(
    request: JourneyCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> JourneyResponse:
    """Create a new evaluation journey."""
    service = JourneyService(db)
    try:
        journey = await service.create_journey(request)
        return to_journey_response(journey)
    except SchemeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/{journey_id}",
    response_model=JourneyDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve evaluation journey details",
    description="Fetches journey details including claims, nested evidence items, and transition history.",
    responses={
        200: {"description": "Journey details found and returned."},
        404: {"model": ErrorResponse, "description": "Journey not found."},
    },
)
async def get_journey(
    journey_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> JourneyDetailResponse:
    """Retrieve full journey details by ID."""
    service = JourneyService(db)
    try:
        journey = await service.get_journey(journey_id)
        return to_journey_detail_response(journey)
    except JourneyNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/{journey_id}/transitions",
    response_model=JourneyResponse,
    status_code=status.HTTP_200_OK,
    summary="Transition journey lifecycle state",
    description="Advances or moves the journey to a new lifecycle state according to statutory state transition rules.",
    responses={
        200: {"description": "State transition recorded successfully."},
        400: {"model": ErrorResponse, "description": "Illegal state transition attempted."},
        404: {"model": ErrorResponse, "description": "Journey not found."},
    },
)
async def transition_journey(
    journey_id: uuid.UUID,
    request: JourneyTransitionRequest,
    db: AsyncSession = Depends(get_db),
) -> JourneyResponse:
    """Execute a lifecycle state transition."""
    service = JourneyService(db)
    try:
        journey = await service.transition_journey(journey_id, request)
        return to_journey_response(journey)
    except JourneyNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except InvalidJourneyTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/{journey_id}/history",
    response_model=List[JourneyTransitionRecordResponse],
    status_code=status.HTTP_200_OK,
    summary="Retrieve journey transition audit log",
    description="Returns chronological audit log of all state transitions undergone by this journey.",
    responses={
        200: {"description": "Audit history returned."},
        404: {"model": ErrorResponse, "description": "Journey not found."},
    },
)
async def get_journey_history(
    journey_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> List[JourneyTransitionRecordResponse]:
    """Retrieve transition audit records for a journey."""
    service = JourneyService(db)
    try:
        records = await service.get_journey_history(journey_id)
        return [JourneyTransitionRecordResponse.model_validate(r) for r in records]
    except JourneyNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# ==============================================================================
# Claims & Evidence Endpoints
# ==============================================================================

@router.post(
    "/{journey_id}/claims",
    response_model=JourneyClaimResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a claim under a journey",
    description="Attaches an asserted factual claim to the journey. Automatically advances DRAFT journeys to FACTS_COLLECTED.",
    responses={
        201: {"description": "Claim registered successfully."},
        400: {"model": ErrorResponse, "description": "Journey in invalid state for claim addition."},
        404: {"model": ErrorResponse, "description": "Journey not found."},
    },
)
async def add_claim(
    journey_id: uuid.UUID,
    request: JourneyClaimCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> JourneyClaimResponse:
    """Register a factual claim."""
    service = JourneyService(db)
    try:
        claim = await service.add_claim(journey_id, request)
        return to_journey_claim_response(claim)
    except JourneyNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except InvalidJourneyTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/{journey_id}/claims",
    response_model=List[JourneyClaimResponse],
    status_code=status.HTTP_200_OK,
    summary="List all claims attached to a journey",
    description="Retrieves all registered claims with nested evidence items and verification records.",
    responses={
        200: {"description": "List of claims returned."},
        404: {"model": ErrorResponse, "description": "Journey not found."},
    },
)
async def get_claims(
    journey_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> List[JourneyClaimResponse]:
    """List journey claims."""
    service = JourneyService(db)
    try:
        claims = await service.get_claims(journey_id)
        return [to_journey_claim_response(c) for c in claims]
    except JourneyNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/{journey_id}/claims/{claim_id}/evidence",
    response_model=JourneyEvidenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit evidence supporting a claim",
    description="Attaches a document reference or verification artifact to a claim. Initial status is PENDING.",
    responses={
        201: {"description": "Evidence submitted successfully."},
        400: {"model": ErrorResponse, "description": "Journey in completed state."},
        404: {"model": ErrorResponse, "description": "Journey or claim not found."},
    },
)
async def add_evidence(
    journey_id: uuid.UUID,
    claim_id: uuid.UUID,
    request: JourneyEvidenceCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> JourneyEvidenceResponse:
    """Attach evidence to a claim."""
    service = JourneyService(db)
    try:
        evidence = await service.add_evidence(journey_id, claim_id, request)
        return to_journey_evidence_response(evidence)
    except JourneyNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ClaimNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except InvalidJourneyTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/{journey_id}/evidence/{evidence_id}/verify",
    response_model=JourneyEvidenceResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify or reject an evidence item",
    description=(
        "Updates evidence status to VERIFIED or REJECTED and creates an immutable VerificationRecord. "
        "Strict separation of concerns: Evidence verification status NEVER mutates factual claims."
    ),
    responses={
        200: {"description": "Evidence verification recorded successfully."},
        400: {"model": ErrorResponse, "description": "Invalid status or missing rejection reason."},
        404: {"model": ErrorResponse, "description": "Evidence not found."},
    },
)
async def verify_evidence(
    journey_id: uuid.UUID,
    evidence_id: uuid.UUID,
    request: EvidenceVerificationRequest,
    db: AsyncSession = Depends(get_db),
) -> JourneyEvidenceResponse:
    """Record verification or rejection of an evidence item."""
    service = JourneyService(db)
    try:
        evidence = await service.verify_evidence(journey_id, evidence_id, request)
        return to_journey_evidence_response(evidence)
    except JourneyNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except EvidenceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except InvalidEvidenceTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ==============================================================================
# Journey Evaluation Endpoint
# ==============================================================================

@router.post(
    "/{journey_id}/evaluate",
    response_model=JourneyEvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute statutory evaluation for a journey",
    description=(
        "Assembles facts from journey claims (with optional overrides), runs the deterministic "
        "rules engine, persists the evaluation trace, updates journey state, and returns "
        "comprehensive eligibility findings and actionable next steps."
    ),
    responses={
        200: {"description": "Evaluation executed and journey updated."},
        400: {"model": ErrorResponse, "description": "Invalid journey state or evaluation error."},
        404: {"model": ErrorResponse, "description": "Journey, scheme, or policy version not found."},
        409: {"model": ErrorResponse, "description": "Policy version conflict."},
    },
)
async def evaluate_journey(
    journey_id: uuid.UUID,
    request: JourneyEvaluateRequest,
    db: AsyncSession = Depends(get_db),
) -> JourneyEvaluationResponse:
    """Execute statutory evaluation on the journey."""
    service = JourneyService(db)
    try:
        return await service.evaluate_journey(journey_id, request)
    except JourneyNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except SchemeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except PolicyVersionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except PolicyVersionConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except (InvalidJourneyTransitionError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
