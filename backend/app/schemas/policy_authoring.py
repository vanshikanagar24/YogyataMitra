"""Pydantic schemas for Policy Authoring, Compilation, Static Validation, Testing, and Diff."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ------------------------------------------------------------------------------
# Request Schemas
# ------------------------------------------------------------------------------

class PolicyDraftCreateRequest(BaseModel):
    """Payload to initialize a new policy draft."""
    scheme_code: str = Field(..., description="Target scheme code (PM_KISAN or SSY)")
    policy_title: str = Field(..., min_length=3, max_length=255, description="Official policy title")
    description: str = Field(..., min_length=5, description="Scope and legislative intent description")
    source_candidate_id: Optional[uuid.UUID] = Field(
        None, description="Optional approved Phase 15 discovery candidate UUID"
    )
    effective_from: Optional[date] = Field(None, description="Prospective statutory effective start date")
    effective_to: Optional[date] = Field(None, description="Prospective statutory sunset/end date")
    parent_policy_version_id: Optional[uuid.UUID] = Field(
        None, description="Optional parent PolicyVersion UUID for baseline diffing"
    )
    authored_rules_json: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Initial root rule AST or empty dict"
    )


class PolicyDraftUpdateRequest(BaseModel):
    """Payload to update an existing draft in DRAFT, AUTHORING, or NEEDS_CLARIFICATION state."""
    policy_title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = Field(None, min_length=5)
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    authored_rules_json: Optional[Dict[str, Any]] = None
    change_summary: Optional[str] = Field(
        None, description="Brief explanation of changes made in this revision"
    )


class ImportCandidateRequest(BaseModel):
    """Payload to import an approved discovery candidate into an existing draft."""
    candidate_id: uuid.UUID = Field(..., description="UUID of an APPROVED policy discovery candidate")


class DraftTransitionRequest(BaseModel):
    """Payload to transition a policy draft lifecycle state."""
    action: str = Field(..., description="Action name e.g. START_AUTHORING, SUBMIT_FOR_REVIEW, STAGE, REJECT")
    reason: str = Field(..., min_length=5, description="Mandatory justification reason (at least 5 characters)")
    notes: Optional[str] = Field(None, description="Optional supervisory or review notes")


class PolicyDraftTestCreateRequest(BaseModel):
    """Payload to add a human-authored test case."""
    name: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    test_type: str = Field(default="HUMAN_AUTHORED")
    facts_json: Dict[str, Any] = Field(..., description="Simulated citizen facts context")
    expected_result: str = Field(..., description="Expected outcome: ELIGIBLE, INELIGIBLE, or UNKNOWN")


# ------------------------------------------------------------------------------
# Response Schemas
# ------------------------------------------------------------------------------

class PolicyDraftAuditEventResponse(BaseModel):
    """Immutable audit trail event for policy draft lifecycle."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    draft_id: uuid.UUID
    actor_identity: str
    actor_role: str
    previous_status: Optional[str] = None
    new_status: str
    action: str
    reason: str
    details_json: Optional[Dict[str, Any]] = None
    created_at: datetime


class PolicyDraftRevisionResponse(BaseModel):
    """Snapshot revision of authored rules."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    draft_id: uuid.UUID
    revision_number: int
    author_id: str
    author_role: str
    change_summary: Optional[str] = None
    previous_rule_hash: Optional[str] = None
    new_rule_hash: Optional[str] = None
    created_at: datetime


class PolicyDraftTestResponse(BaseModel):
    """Deterministic test case specification and execution result."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    draft_id: uuid.UUID
    name: str
    description: Optional[str] = None
    test_type: str
    facts_json: Dict[str, Any]
    expected_result: str
    actual_result: Optional[str] = None
    status: str
    execution_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ValidationFinding(BaseModel):
    """Individual static analysis or structural finding."""
    code: str
    message: str
    rule_id: Optional[str] = None
    field_path: Optional[str] = None


class ValidationReportResponse(BaseModel):
    """Results of deterministic AST validation and static policy checks."""
    is_valid: bool
    errors: List[ValidationFinding] = Field(default_factory=list)
    warnings: List[ValidationFinding] = Field(default_factory=list)
    info: List[ValidationFinding] = Field(default_factory=list)
    rule_count: int = 0
    validated_at: datetime


class CompilationResponse(BaseModel):
    """Output of deterministic compilation and canonical hashing."""
    is_compiled: bool
    rule_hash: str
    canonical_rules_json: Dict[str, Any]
    compiled_at: datetime


class TestRunSummaryResponse(BaseModel):
    """Summary of test suite execution."""
    total_tests: int
    passed_tests: int
    failed_tests: int
    test_status: str
    executed_at: datetime
    results: List[PolicyDraftTestResponse]


class PolicyRuleDiffItem(BaseModel):
    """Single rule-level difference."""
    rule_id: str
    diff_type: str  # ADDED, REMOVED, MODIFIED
    description_en: Optional[str] = None
    description_hi: Optional[str] = None
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    human_explanation: str


class PolicyDiffResponse(BaseModel):
    """Human-readable and structural comparison against baseline policy."""
    parent_version_code: Optional[str] = None
    parent_rule_hash: Optional[str] = None
    draft_rule_hash: Optional[str] = None
    added_rules: List[PolicyRuleDiffItem] = Field(default_factory=list)
    removed_rules: List[PolicyRuleDiffItem] = Field(default_factory=list)
    modified_rules: List[PolicyRuleDiffItem] = Field(default_factory=list)
    metadata_changes: List[Dict[str, Any]] = Field(default_factory=list)
    human_summary: str


class PolicyDraftResponse(BaseModel):
    """Core policy draft representation."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scheme_id: uuid.UUID
    scheme_code: Optional[str] = None
    scheme_name: Optional[str] = None
    policy_title: str
    description: str
    lifecycle_status: str
    source_candidate_id: Optional[uuid.UUID] = None

    # Provenance
    source_url: Optional[str] = None
    source_title: Optional[str] = None
    source_publisher: Optional[str] = None
    source_document_identifier: Optional[str] = None
    source_publication_date: Optional[datetime] = None
    source_effective_date: Optional[datetime] = None
    source_retrieved_at: Optional[datetime] = None
    source_excerpt: Optional[str] = None
    provenance_status: Optional[str] = None
    adversarial_flag_detected: bool = False
    candidate_type: Optional[str] = None

    # AST and Rules
    authored_rules_json: Dict[str, Any]
    canonical_rules_json: Optional[Dict[str, Any]] = None
    rule_hash: Optional[str] = None
    schema_version: str
    compiler_version: str

    # Temporality
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None

    # Parent baseline
    parent_policy_version_id: Optional[uuid.UUID] = None
    change_summary: Optional[str] = None

    # Verification
    validation_status: str
    validation_details_json: Optional[Dict[str, Any]] = None
    test_status: str
    test_summary_json: Optional[Dict[str, Any]] = None

    # Authorship and Audit
    author_id: str
    author_role: str
    created_at: datetime
    updated_at: datetime
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    reviewed_by_role: Optional[str] = None
    reviewer_reason: Optional[str] = None
    staged_at: Optional[datetime] = None
    staged_by: Optional[str] = None
    staged_by_role: Optional[str] = None


class PolicyDraftDetailResponse(PolicyDraftResponse):
    """Detailed draft dossier with child collections."""
    audit_events: List[PolicyDraftAuditEventResponse] = Field(default_factory=list)
    revisions: List[PolicyDraftRevisionResponse] = Field(default_factory=list)
    tests: List[PolicyDraftTestResponse] = Field(default_factory=list)


class PolicyDraftQueueMetrics(BaseModel):
    """Aggregated queue metrics for draft dashboard."""
    total_drafts: int
    draft_status_count: int
    authoring: int
    validating: int
    testing: int
    pending_review: int
    in_review: int
    needs_clarification: int
    staged: int
    archived: int


class PolicyDraftListResponse(BaseModel):
    """Paginated list of policy drafts with queue metrics."""
    drafts: List[PolicyDraftResponse]
    total: int
    metrics: PolicyDraftQueueMetrics
