"""API Router for Controlled Policy Authoring, Static Validation, Testing, and Diff (Phase 16).

Provides internal officer endpoints for:
- Querying and filtering the policy draft queue with aggregate metrics
- Creating new policy drafts from scratch or from approved discovery candidates
- Updating draft metadata and authored rule ASTs with automatic revision snapshots
- Performing deterministic static AST validation and invariant checks
- Compiling drafts into canonical JSON and computing canonical SHA-256 rule hashes
- Auto-generating boundary and Strong Kleene test cases
- Executing deterministic test suites against EvaluationContext
- Computing policy diffs against parent or active PolicyVersion baselines
- Executing lifecycle state machine transitions with mandatory justifications and strict RBAC
- Inspecting chronological revisions and audit trail events

Strictly protected by internal officer RBAC (OFFICER and SUPERVISOR roles only).
Citizen access is unconditionally rejected with HTTP 403.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_officer, require_role
from app.core.database import get_db
from app.models.policy_draft import (
    PolicyDraft,
    PolicyDraftAuditEvent,
    PolicyDraftLifecycleStatus,
    PolicyDraftRevision,
    PolicyDraftTest,
    PolicyDraftTestStatus,
    PolicyDraftTestType,
    PolicyDraftValidationStatus,
)
from app.schemas.policy_authoring import (
    CompilationResponse,
    DraftTransitionRequest,
    ImportCandidateRequest,
    PolicyDiffResponse,
    PolicyDraftAuditEventResponse,
    PolicyDraftCreateRequest,
    PolicyDraftDetailResponse,
    PolicyDraftListResponse,
    PolicyDraftResponse,
    PolicyDraftRevisionResponse,
    PolicyDraftTestCreateRequest,
    PolicyDraftTestResponse,
    PolicyDraftUpdateRequest,
    TestRunSummaryResponse,
    ValidationReportResponse,
)
from app.services.policy_compiler_service import (
    compile_draft_ruleset,
    validate_draft_static_invariants,
)
from app.services.policy_diff_service import compute_policy_diff
from app.services.policy_draft_service import (
    create_policy_draft,
    get_draft_detail,
    get_drafts_queue,
    import_candidate_into_draft,
    record_draft_transition,
    update_policy_draft,
)
from app.services.policy_test_service import (
    generate_draft_test_cases,
    run_draft_test_suite,
)

logger = logging.getLogger("yogyatamitra.api.policy_authoring")

router = APIRouter(prefix="/officer/policy-authoring", tags=["Controlled Policy Authoring & Compilation"])


# ==============================================================================
# Serialization Helpers
# ==============================================================================

def _serialize_draft(d: PolicyDraft) -> PolicyDraftResponse:
    """Helper to convert ORM PolicyDraft to PolicyDraftResponse."""
    return PolicyDraftResponse(
        id=d.id,
        scheme_id=d.scheme_id,
        scheme_code=d.scheme.scheme_code if d.scheme else None,
        scheme_name=d.scheme.name_en if d.scheme else None,
        policy_title=d.policy_title,
        description=d.description,
        lifecycle_status=d.lifecycle_status.value if hasattr(d.lifecycle_status, "value") else str(d.lifecycle_status),
        source_candidate_id=d.source_candidate_id,
        source_url=d.source_url,
        source_title=d.source_title,
        source_publisher=d.source_publisher,
        source_document_identifier=d.source_document_identifier,
        source_publication_date=d.source_publication_date,
        source_effective_date=d.source_effective_date,
        source_retrieved_at=d.source_retrieved_at,
        source_excerpt=d.source_excerpt,
        provenance_status=d.provenance_status,
        adversarial_flag_detected=d.adversarial_flag_detected,
        candidate_type=d.candidate_type,
        authored_rules_json=d.authored_rules_json or {},
        canonical_rules_json=d.canonical_rules_json,
        rule_hash=d.rule_hash,
        schema_version=d.schema_version,
        compiler_version=d.compiler_version,
        effective_from=d.effective_from,
        effective_to=d.effective_to,
        parent_policy_version_id=d.parent_policy_version_id,
        change_summary=d.change_summary,
        validation_status=d.validation_status.value if hasattr(d.validation_status, "value") else str(d.validation_status),
        validation_details_json=d.validation_details_json,
        test_status=d.test_status.value if hasattr(d.test_status, "value") else str(d.test_status),
        test_summary_json=d.test_summary_json,
        author_id=d.author_id,
        author_role=d.author_role,
        created_at=d.created_at,
        updated_at=d.updated_at,
        submitted_at=d.submitted_at,
        reviewed_at=d.reviewed_at,
        reviewed_by=d.reviewed_by,
        reviewed_by_role=d.reviewed_by_role,
        reviewer_reason=d.reviewer_reason,
        staged_at=d.staged_at,
        staged_by=d.staged_by,
        staged_by_role=d.staged_by_role,
    )


def _serialize_draft_detail(d: PolicyDraft) -> PolicyDraftDetailResponse:
    """Helper to convert ORM PolicyDraft and child collections to PolicyDraftDetailResponse."""
    base = _serialize_draft(d)

    events_resp = [
        PolicyDraftAuditEventResponse(
            id=ev.id,
            draft_id=ev.draft_id,
            actor_identity=ev.actor_identity,
            actor_role=ev.actor_role,
            previous_status=ev.previous_status,
            new_status=ev.new_status,
            action=ev.action,
            reason=ev.reason,
            details_json=ev.details_json,
            created_at=ev.created_at,
        )
        for ev in (d.audit_events or [])
    ]

    revisions_resp = [
        PolicyDraftRevisionResponse(
            id=r.id,
            draft_id=r.draft_id,
            revision_number=r.revision_number,
            author_id=r.author_id,
            author_role=r.author_role,
            change_summary=r.change_summary,
            previous_rule_hash=r.previous_rule_hash,
            new_rule_hash=r.new_rule_hash,
            created_at=r.created_at,
        )
        for r in (d.revisions or [])
    ]

    tests_resp = [
        PolicyDraftTestResponse(
            id=t.id,
            draft_id=t.draft_id,
            name=t.name,
            description=t.description,
            test_type=t.test_type.value if hasattr(t.test_type, "value") else str(t.test_type),
            facts_json=t.facts_json,
            expected_result=t.expected_result,
            actual_result=t.actual_result,
            status=t.status.value if hasattr(t.status, "value") else str(t.status),
            execution_notes=t.execution_notes,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in (d.tests or [])
    ]

    return PolicyDraftDetailResponse(
        **base.model_dump(),
        audit_events=events_resp,
        revisions=revisions_resp,
        tests=tests_resp,
    )


# ==============================================================================
# Endpoints
# ==============================================================================

@router.get("/drafts", response_model=PolicyDraftListResponse)
async def list_policy_drafts(
    status: Optional[str] = Query(None, description="Filter by lifecycle status (or ALL)"),
    scheme: Optional[str] = Query(None, description="Filter by scheme code (e.g. PM_KISAN or SSY)"),
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(50, ge=1, le=100, description="Page limit"),
    officer: Dict[str, Any] = Depends(require_role(["OFFICER", "SUPERVISOR"])),
    db: AsyncSession = Depends(get_db),
) -> PolicyDraftListResponse:
    """List policy drafts with lifecycle status filtering and aggregated queue metrics."""
    drafts, total_count, metrics = await get_drafts_queue(
        session=db,
        status_filter=status,
        scheme_filter=scheme,
        skip=skip,
        limit=limit,
    )
    serialized = [_serialize_draft(d) for d in drafts]
    return PolicyDraftListResponse(
        drafts=serialized,
        total=total_count,
        metrics=metrics,
    )


@router.post("/drafts", response_model=PolicyDraftDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_draft(
    payload: PolicyDraftCreateRequest,
    officer: Dict[str, Any] = Depends(require_role(["OFFICER", "SUPERVISOR"])),
    db: AsyncSession = Depends(get_db),
) -> PolicyDraftDetailResponse:
    """Create a new policy draft in initial DRAFT lifecycle state."""
    draft = await create_policy_draft(
        session=db,
        payload=payload,
        actor_email=officer["email"],
        actor_role=officer["role"],
    )
    return _serialize_draft_detail(draft)


@router.get("/drafts/{draft_id}", response_model=PolicyDraftDetailResponse)
async def get_draft(
    draft_id: uuid.UUID,
    officer: Dict[str, Any] = Depends(require_role(["OFFICER", "SUPERVISOR"])),
    db: AsyncSession = Depends(get_db),
) -> PolicyDraftDetailResponse:
    """Get complete policy draft dossier including revisions, tests, and audit events."""
    draft = await get_draft_detail(db, draft_id)
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy draft '{draft_id}' not found.",
        )
    return _serialize_draft_detail(draft)


@router.patch("/drafts/{draft_id}", response_model=PolicyDraftDetailResponse)
async def update_draft(
    draft_id: uuid.UUID,
    payload: PolicyDraftUpdateRequest,
    officer: Dict[str, Any] = Depends(require_role(["OFFICER", "SUPERVISOR"])),
    db: AsyncSession = Depends(get_db),
) -> PolicyDraftDetailResponse:
    """Update draft title, description, prospective dates, or authored AST."""
    draft = await update_policy_draft(
        session=db,
        draft_id=draft_id,
        payload=payload,
        actor_email=officer["email"],
        actor_role=officer["role"],
    )
    return _serialize_draft_detail(draft)


@router.post("/drafts/{draft_id}/import-candidate", response_model=PolicyDraftDetailResponse)
async def import_candidate(
    draft_id: uuid.UUID,
    payload: ImportCandidateRequest,
    officer: Dict[str, Any] = Depends(require_role(["OFFICER", "SUPERVISOR"])),
    db: AsyncSession = Depends(get_db),
) -> PolicyDraftDetailResponse:
    """Import an APPROVED Phase 15 discovery candidate into an existing draft."""
    draft = await import_candidate_into_draft(
        session=db,
        draft_id=draft_id,
        candidate_id=payload.candidate_id,
        actor_email=officer["email"],
        actor_role=officer["role"],
    )
    return _serialize_draft_detail(draft)


@router.post("/drafts/{draft_id}/validate", response_model=ValidationReportResponse)
async def validate_draft(
    draft_id: uuid.UUID,
    officer: Dict[str, Any] = Depends(require_role(["OFFICER", "SUPERVISOR"])),
    db: AsyncSession = Depends(get_db),
) -> ValidationReportResponse:
    """Execute deterministic static AST analysis, circular dependency, date, and overlap checks."""
    draft = await get_draft_detail(db, draft_id)
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy draft '{draft_id}' not found.",
        )

    report = await validate_draft_static_invariants(db, draft)

    # Persist validation outcome to draft
    draft.validation_status = (
        PolicyDraftValidationStatus.VALID if report.is_valid else PolicyDraftValidationStatus.INVALID
    )
    draft.validation_details_json = report.model_dump(mode="json")
    draft.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return report


@router.post("/drafts/{draft_id}/compile", response_model=CompilationResponse)
async def compile_draft(
    draft_id: uuid.UUID,
    officer: Dict[str, Any] = Depends(require_role(["OFFICER", "SUPERVISOR"])),
    db: AsyncSession = Depends(get_db),
) -> CompilationResponse:
    """Deterministically compile authored rule AST into canonical representation and SHA-256 hash."""
    draft = await get_draft_detail(db, draft_id)
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy draft '{draft_id}' not found.",
        )

    try:
        compilation = compile_draft_ruleset(draft)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(err),
        )

    # Persist compiled output to draft
    draft.canonical_rules_json = compilation.canonical_rules_json
    draft.rule_hash = compilation.rule_hash
    draft.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return compilation


@router.post("/drafts/{draft_id}/generate-tests", response_model=List[PolicyDraftTestResponse])
async def generate_tests_for_draft(
    draft_id: uuid.UUID,
    officer: Dict[str, Any] = Depends(require_role(["OFFICER", "SUPERVISOR"])),
    db: AsyncSession = Depends(get_db),
) -> List[PolicyDraftTestResponse]:
    """Auto-generate deterministic boundary test cases and Strong Kleene UNKNOWN tests from draft AST."""
    draft = await get_draft_detail(db, draft_id)
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy draft '{draft_id}' not found.",
        )

    rules_json = draft.authored_rules_json or {}
    if not rules_json or not rules_json.get("node_type"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Draft has no valid authored rules to generate test cases from.",
        )

    generated = generate_draft_test_cases(draft)
    now = datetime.now(timezone.utc)

    created_tests: List[PolicyDraftTest] = []
    for spec in generated:
        test = PolicyDraftTest(
            id=uuid.uuid4(),
            draft_id=draft.id,
            name=spec["name"],
            description=spec.get("description"),
            test_type=PolicyDraftTestType.AUTO_GENERATED,
            facts_json=spec["facts_json"],
            expected_result=spec["expected_result"],
            status=PolicyDraftTestStatus.NOT_TESTED,
            created_at=now,
            updated_at=now,
        )
        db.add(test)
        created_tests.append(test)

    # Invalidate previous test status
    draft.test_status = PolicyDraftTestStatus.NOT_TESTED
    await db.commit()

    return [PolicyDraftTestResponse.model_validate(t) for t in created_tests]


@router.get("/drafts/{draft_id}/tests", response_model=List[PolicyDraftTestResponse])
async def list_draft_tests(
    draft_id: uuid.UUID,
    officer: Dict[str, Any] = Depends(require_role(["OFFICER", "SUPERVISOR"])),
    db: AsyncSession = Depends(get_db),
) -> List[PolicyDraftTestResponse]:
    """List all registered test cases for a draft."""
    draft = await get_draft_detail(db, draft_id)
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy draft '{draft_id}' not found.",
        )

    stmt = (
        select(PolicyDraftTest)
        .where(PolicyDraftTest.draft_id == draft_id)
        .order_by(PolicyDraftTest.created_at.asc())
    )
    res = await db.execute(stmt)
    tests = res.scalars().all()
    return [PolicyDraftTestResponse.model_validate(t) for t in tests]


@router.post("/drafts/{draft_id}/tests", response_model=PolicyDraftTestResponse, status_code=status.HTTP_201_CREATED)
async def add_human_test(
    draft_id: uuid.UUID,
    payload: PolicyDraftTestCreateRequest,
    officer: Dict[str, Any] = Depends(require_role(["OFFICER", "SUPERVISOR"])),
    db: AsyncSession = Depends(get_db),
) -> PolicyDraftTestResponse:
    """Add a human-authored synthetic test case to the draft test suite."""
    draft = await get_draft_detail(db, draft_id)
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy draft '{draft_id}' not found.",
        )

    now = datetime.now(timezone.utc)
    test = PolicyDraftTest(
        id=uuid.uuid4(),
        draft_id=draft.id,
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
        test_type=PolicyDraftTestType.HUMAN_AUTHORED,
        facts_json=payload.facts_json,
        expected_result=payload.expected_result.upper().strip(),
        status=PolicyDraftTestStatus.NOT_TESTED,
        created_at=now,
        updated_at=now,
    )
    db.add(test)

    # Invalidate overall test status
    draft.test_status = PolicyDraftTestStatus.NOT_TESTED
    await db.commit()

    return PolicyDraftTestResponse.model_validate(test)


@router.post("/drafts/{draft_id}/test", response_model=TestRunSummaryResponse)
async def execute_test_suite(
    draft_id: uuid.UUID,
    officer: Dict[str, Any] = Depends(require_role(["OFFICER", "SUPERVISOR"])),
    db: AsyncSession = Depends(get_db),
) -> TestRunSummaryResponse:
    """Run all registered tests against draft rules using the deterministic evaluator."""
    draft = await get_draft_detail(db, draft_id)
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy draft '{draft_id}' not found.",
        )

    try:
        summary = await run_draft_test_suite(db, draft)
        return summary
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(err),
        )


@router.get("/drafts/{draft_id}/diff", response_model=PolicyDiffResponse)
async def get_policy_diff(
    draft_id: uuid.UUID,
    officer: Dict[str, Any] = Depends(require_role(["OFFICER", "SUPERVISOR"])),
    db: AsyncSession = Depends(get_db),
) -> PolicyDiffResponse:
    """Compute structural and metadata diff against parent or active PolicyVersion."""
    draft = await get_draft_detail(db, draft_id)
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy draft '{draft_id}' not found.",
        )

    return await compute_policy_diff(db, draft)


@router.post("/drafts/{draft_id}/transitions", response_model=PolicyDraftDetailResponse)
async def transition_draft(
    draft_id: uuid.UUID,
    payload: DraftTransitionRequest,
    officer: Dict[str, Any] = Depends(require_role(["OFFICER", "SUPERVISOR"])),
    db: AsyncSession = Depends(get_db),
) -> PolicyDraftDetailResponse:
    """Execute lifecycle transition with mandatory substantive reason and separation of duties."""
    updated = await record_draft_transition(
        session=db,
        draft_id=draft_id,
        action=payload.action,
        reason=payload.reason,
        actor_email=officer["email"],
        actor_role=officer["role"],
        notes=payload.notes,
    )
    return _serialize_draft_detail(updated)


@router.get("/drafts/{draft_id}/history", response_model=Dict[str, Any])
async def get_draft_history(
    draft_id: uuid.UUID,
    officer: Dict[str, Any] = Depends(require_role(["OFFICER", "SUPERVISOR"])),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve full chronological revision snapshots and immutable audit events."""
    draft = await get_draft_detail(db, draft_id)
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy draft '{draft_id}' not found.",
        )

    audit_events = [
        PolicyDraftAuditEventResponse.model_validate(ev).model_dump(mode="json")
        for ev in (draft.audit_events or [])
    ]
    revisions = [
        PolicyDraftRevisionResponse.model_validate(rev).model_dump(mode="json")
        for rev in (draft.revisions or [])
    ]

    return {
        "draft_id": str(draft.id),
        "audit_events": audit_events,
        "revisions": revisions,
    }
