"""Scheme Discovery API Endpoints.

Provides read-only discovery of statutory government welfare schemes
persisted in the PostgreSQL database. Zero hardcoded scheme lists.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.enums import SchemeStatus
from app.models.scheme import Scheme
from app.schemas.api import (
    ErrorResponse,
    PolicyVersionSummaryResponse,
    SchemeDetailResponse,
    SchemeSummaryResponse,
)

router = APIRouter(prefix="/schemes", tags=["Schemes"])


@router.get(
    "",
    response_model=List[SchemeSummaryResponse],
    status_code=status.HTTP_200_OK,
    summary="List all configured schemes",
    description="Retrieve all statutory welfare schemes configured in the platform directly from the database.",
    responses={
        200: {"description": "List of active or filtered statutory welfare schemes."},
    },
)
async def list_schemes(
    status_filter: Optional[SchemeStatus] = Query(
        None,
        alias="status",
        description="Filter schemes by operational status (e.g. ACTIVE)",
    ),
    db: AsyncSession = Depends(get_db),
) -> List[SchemeSummaryResponse]:
    """Retrieve schemes from the database, optionally filtered by status."""
    stmt = select(Scheme).order_by(Scheme.scheme_code.asc())
    if status_filter is not None:
        stmt = stmt.where(Scheme.status == status_filter)

    res = await db.execute(stmt)
    schemes = res.scalars().all()
    return [SchemeSummaryResponse.model_validate(s) for s in schemes]


@router.get(
    "/{scheme_code}",
    response_model=SchemeDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get scheme details",
    description="Retrieve detailed metadata and available policy version codes for a specific statutory scheme.",
    responses={
        200: {"description": "Detailed scheme metadata and policy version list."},
        404: {"model": ErrorResponse, "description": "Scheme code was not found."},
    },
)
async def get_scheme(
    scheme_code: str,
    db: AsyncSession = Depends(get_db),
) -> SchemeDetailResponse:
    """Retrieve detailed scheme information by scheme_code."""
    normalized_code = scheme_code.strip().upper()
    stmt = (
        select(Scheme)
        .options(selectinload(Scheme.policy_versions))
        .where(Scheme.scheme_code == normalized_code)
    )
    res = await db.execute(stmt)
    scheme = res.scalar_one_or_none()

    if not scheme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Statutory scheme with code '{scheme_code}' was not found.",
        )

    return SchemeDetailResponse(
        id=scheme.id,
        scheme_code=scheme.scheme_code,
        name_en=scheme.name_en,
        name_hi=scheme.name_hi,
        description_en=scheme.description_en,
        description_hi=scheme.description_hi,
        ministry=scheme.ministry,
        official_url=scheme.official_url,
        status=scheme.status,
        created_at=scheme.created_at,
        updated_at=scheme.updated_at,
        policy_versions=[
            PolicyVersionSummaryResponse(
                version_code=pv.version_code,
                effective_from=pv.effective_from,
                effective_to=pv.effective_to,
                rule_definition_hash=pv.rule_definition_hash,
            )
            for pv in scheme.policy_versions
        ],
    )
