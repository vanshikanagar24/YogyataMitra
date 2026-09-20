"""Evaluation API Endpoints.

Provides statutory eligibility evaluation execution, Kleene-logic decisioning,
bilingual explainability, and immutable audit trace persistence and retrieval.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.api import (
    ErrorResponse,
    EvaluationRequest,
    EvaluationResponse,
    PersistedEvaluationResponse,
)
from app.services.evaluation_service import (
    CitizenNotFoundError,
    EvaluationNotFoundError,
    EvaluationService,
    PolicyVersionConflictError,
)
from app.services.policy_loader import SchemeNotFoundError
from app.services.policy_selector import PolicyVersionNotFoundError

router = APIRouter(prefix="/evaluations", tags=["Evaluations"])


@router.post(
    "",
    response_model=EvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute eligibility evaluation",
    description=(
        "Evaluates citizen, family, and asset facts against the statutory policy version "
        "effective as of evaluation_date. Executes using the generic deterministic rules engine, "
        "generates explainability traces, and persists an immutable audit record."
    ),
    responses={
        200: {"description": "Deterministic eligibility decision and explainability trace."},
        400: {"model": ErrorResponse, "description": "Invalid input parameters or syntax error."},
        404: {"model": ErrorResponse, "description": "Scheme or effective policy version not found."},
        409: {"model": ErrorResponse, "description": "Explicit policy version conflicts with statutory effective policy."},
        422: {"model": ErrorResponse, "description": "Validation error on request schema."},
    },
)
async def evaluate_eligibility(
    request: EvaluationRequest,
    db: AsyncSession = Depends(get_db),
) -> EvaluationResponse:
    """Execute statutory eligibility evaluation and persist audit trace."""
    service = EvaluationService(db)
    try:
        response = await service.evaluate(request)
        return response
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
    except CitizenNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/{evaluation_id}",
    response_model=PersistedEvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve persisted evaluation trace",
    description="Retrieve an immutable historical evaluation trace and input snapshot by its unique identifier.",
    responses={
        200: {"description": "Persisted evaluation trace and frozen input snapshot."},
        404: {"model": ErrorResponse, "description": "Evaluation record was not found."},
    },
)
async def get_evaluation_trace(
    evaluation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> PersistedEvaluationResponse:
    """Retrieve historical evaluation audit trace by ID."""
    service = EvaluationService(db)
    try:
        return await service.get_evaluation_by_id(evaluation_id)
    except EvaluationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
