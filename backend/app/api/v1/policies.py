"""Policy Discovery API Endpoints.

Provides read-only access to time-bounded statutory policy versions,
effective date ranges, canonical rule hashes, and source provenance metadata.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.scheme import PolicyVersion, Scheme
from app.schemas.api import ErrorResponse, PolicyVersionDetailResponse

router = APIRouter(prefix="/schemes/{scheme_code}/policies", tags=["Policies"])


@router.get(
    "",
    response_model=List[PolicyVersionDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="List policy versions for a scheme",
    description="Retrieve all historical and active statutory policy versions, provenance, and canonical hashes for a scheme.",
    responses={
        200: {"description": "List of policy versions with provenance and canonical hashes."},
        404: {"model": ErrorResponse, "description": "Scheme code was not found."},
    },
)
async def list_scheme_policies(
    scheme_code: str,
    db: AsyncSession = Depends(get_db),
) -> List[PolicyVersionDetailResponse]:
    """Retrieve all policy versions for a given scheme."""
    normalized_code = scheme_code.strip().upper()

    scheme_stmt = select(Scheme).where(Scheme.scheme_code == normalized_code)
    scheme_res = await db.execute(scheme_stmt)
    scheme = scheme_res.scalar_one_or_none()

    if not scheme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Statutory scheme with code '{scheme_code}' was not found.",
        )

    pv_stmt = (
        select(PolicyVersion)
        .options(selectinload(PolicyVersion.rule_set))
        .where(PolicyVersion.scheme_id == scheme.id)
        .order_by(PolicyVersion.effective_from.desc())
    )
    pv_res = await db.execute(pv_stmt)
    policy_versions = pv_res.scalars().all()

    return [
        PolicyVersionDetailResponse(
            id=pv.id,
            scheme_code=scheme.scheme_code,
            version_code=pv.version_code,
            effective_from=pv.effective_from,
            effective_to=pv.effective_to,
            source_url=pv.source_url,
            source_title=pv.source_title,
            source_document_identifier=pv.source_document_identifier,
            rule_definition_hash=pv.rule_definition_hash,
            ruleset_schema_version=pv.rule_set.schema_version if pv.rule_set else None,
            ruleset_version=pv.rule_set.rule_set_version if pv.rule_set else None,
            created_at=pv.created_at,
        )
        for pv in policy_versions
    ]


@router.get(
    "/{version_code}",
    response_model=PolicyVersionDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get policy version details",
    description="Retrieve specific policy version metadata, statutory clause provenance, and canonical rule hash.",
    responses={
        200: {"description": "Detailed policy version and provenance metadata."},
        404: {"model": ErrorResponse, "description": "Scheme code or policy version code was not found."},
    },
)
async def get_policy_version_detail(
    scheme_code: str,
    version_code: str,
    db: AsyncSession = Depends(get_db),
) -> PolicyVersionDetailResponse:
    """Retrieve a single policy version by scheme_code and version_code."""
    normalized_scheme = scheme_code.strip().upper()
    requested_version = version_code.strip()

    scheme_stmt = select(Scheme).where(Scheme.scheme_code == normalized_scheme)
    scheme_res = await db.execute(scheme_stmt)
    scheme = scheme_res.scalar_one_or_none()

    if not scheme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Statutory scheme with code '{scheme_code}' was not found.",
        )

    pv_stmt = (
        select(PolicyVersion)
        .options(selectinload(PolicyVersion.rule_set))
        .where(
            PolicyVersion.scheme_id == scheme.id,
            PolicyVersion.version_code == requested_version,
        )
    )
    pv_res = await db.execute(pv_stmt)
    pv = pv_res.scalar_one_or_none()

    if not pv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy version '{version_code}' for scheme '{scheme_code}' was not found.",
        )

    return PolicyVersionDetailResponse(
        id=pv.id,
        scheme_code=scheme.scheme_code,
        version_code=pv.version_code,
        effective_from=pv.effective_from,
        effective_to=pv.effective_to,
        source_url=pv.source_url,
        source_title=pv.source_title,
        source_document_identifier=pv.source_document_identifier,
        rule_definition_hash=pv.rule_definition_hash,
        ruleset_schema_version=pv.rule_set.schema_version if pv.rule_set else None,
        ruleset_version=pv.rule_set.rule_set_version if pv.rule_set else None,
        created_at=pv.created_at,
    )
