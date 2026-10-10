"""Official Documents & Policy Provenance API Endpoints.

Provides read-only access to statutory source authorities, official documents,
cryptographic document hashes, policy-version bindings, and rule-level provenances.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.provenance import (
    OfficialDocument,
    OfficialDocumentVersion,
    OfficialSource,
)
from app.schemas.api import ErrorResponse
from app.schemas.provenance import (
    BoundDocumentSummary,
    OfficialDocumentResponse,
    OfficialDocumentVersionResponse,
    OfficialSourceResponse,
    PolicyVersionProvenanceSummary,
    ProvenanceAuditEventResponse,
    RuleProvenanceDetail,
    SchemeProvenanceResponse,
)
from app.services.provenance_service import (
    ProvenanceNotFoundError,
    ProvenanceService,
    ProvenanceValidationError,
)

router = APIRouter(prefix="/provenance", tags=["Provenance"])


@router.get(
    "/schemes/{scheme_code}",
    response_model=SchemeProvenanceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get full statutory provenance for a scheme",
    description="Retrieve all official publishing sources, statutory documents, document versions, and policy bindings.",
    responses={
        200: {"description": "Statutory provenance graph successfully retrieved."},
        404: {"model": ErrorResponse, "description": "Scheme code was not found."},
    },
)
async def get_scheme_provenance(
    scheme_code: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve full statutory provenance for a given scheme."""
    service = ProvenanceService(db)
    try:
        return await service.get_scheme_provenance(scheme_code)
    except ProvenanceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/policies/{policy_version_id}",
    status_code=status.HTTP_200_OK,
    summary="Get provenance for a specific policy version",
    description="Retrieve official document versions, document hashes vs ruleset hash, and rule provenances.",
    responses={
        200: {"description": "Policy version provenance details."},
        404: {"model": ErrorResponse, "description": "Policy version ID was not found."},
    },
)
async def get_policy_provenance(
    policy_version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve official provenance for a specific PolicyVersion."""
    service = ProvenanceService(db)
    try:
        return await service.get_policy_provenance(policy_version_id)
    except ProvenanceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/rules/{policy_version_id}/{rule_id}",
    response_model=RuleProvenanceDetail,
    status_code=status.HTTP_200_OK,
    summary="Get rule-level official provenance",
    description="Trace an individual AST rule to its official document, clause/section locator, and source authority.",
    responses={
        200: {"description": "Rule-level official provenance successfully resolved."},
        404: {"model": ErrorResponse, "description": "Rule or policy version was not found."},
    },
)
async def get_rule_provenance(
    policy_version_id: uuid.UUID,
    rule_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve rule-level provenance for a specific rule under a PolicyVersion."""
    service = ProvenanceService(db)
    try:
        return await service.get_rule_provenance(policy_version_id, rule_id)
    except ProvenanceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/documents/{document_id}",
    response_model=OfficialDocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get official document metadata and version history",
    description="Retrieve official document details, reference numbers, issuing authority, and all registered versions.",
    responses={
        200: {"description": "Official document details."},
        404: {"model": ErrorResponse, "description": "Document ID was not found."},
    },
)
async def get_official_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> OfficialDocument:
    """Retrieve an official document by UUID."""
    stmt = (
        select(OfficialDocument)
        .where(OfficialDocument.id == document_id)
        .options(selectinload(OfficialDocument.versions))
    )
    res = await db.execute(stmt)
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"OfficialDocument '{document_id}' was not found.",
        )
    return doc


@router.get(
    "/sources",
    response_model=List[OfficialSourceResponse],
    status_code=status.HTTP_200_OK,
    summary="List official government publishers and portals",
    description="List registered official government authorities, filterable by scheme_code.",
)
async def list_official_sources(
    scheme_code: Optional[str] = Query(None, description="Optional scheme code filter"),
    db: AsyncSession = Depends(get_db),
) -> List[OfficialSource]:
    """List registered official sources with optional scheme filtering."""
    stmt = select(OfficialSource)
    if scheme_code:
        stmt = stmt.where(
            (OfficialSource.scheme_code == scheme_code.strip().upper())
            | (OfficialSource.scheme_code.is_(None))
        )
    stmt = stmt.order_by(OfficialSource.publisher_name)
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get(
    "/audit-trail",
    response_model=List[ProvenanceAuditEventResponse],
    status_code=status.HTTP_200_OK,
    summary="List provenance audit trail events",
    description="Retrieve immutable chronological audit records of provenance changes and document versioning.",
)
async def get_provenance_audit_trail(
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    entity_id: Optional[str] = Query(None, description="Filter by entity ID"),
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Retrieve immutable provenance audit events."""
    service = ProvenanceService(db)
    return await service.get_provenance_audit_trail(
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
    )
