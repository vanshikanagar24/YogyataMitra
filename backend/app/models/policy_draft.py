"""SQLAlchemy ORM models for Controlled Policy Authoring, Compilation, and Review.

NON-NEGOTIABLE SAFETY BOUNDARIES:
- A PolicyDraft is strictly proposed, non-active policy data.
- It is NOT evaluated by citizen journeys and NOT executed by citizen APIs.
- Even in STAGED status, a draft is NOT an active policy version.
- Activation is explicitly NOT implemented in Phase 16.
- AI is not part of the compilation or execution pipeline.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.policy_discovery import PolicyDiscoveryCandidate
    from app.models.scheme import PolicyVersion, Scheme


# ------------------------------------------------------------------------------
# Controlled Enumerations for Policy Authoring
# ------------------------------------------------------------------------------

class PolicyDraftLifecycleStatus(str, Enum):
    """Controlled lifecycle states for policy drafts."""
    DRAFT = "DRAFT"
    AUTHORING = "AUTHORING"
    VALIDATING = "VALIDATING"
    TESTING = "TESTING"
    PENDING_REVIEW = "PENDING_REVIEW"
    IN_REVIEW = "IN_REVIEW"
    REJECTED = "REJECTED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    STAGED = "STAGED"
    ARCHIVED = "ARCHIVED"


class PolicyDraftValidationStatus(str, Enum):
    """Status of static analysis and AST validation."""
    NOT_VALIDATED = "NOT_VALIDATED"
    VALID = "VALID"
    INVALID = "INVALID"


class PolicyDraftTestStatus(str, Enum):
    """Aggregate execution status of draft test suite."""
    NOT_TESTED = "NOT_TESTED"
    PASSED = "PASSED"
    FAILED = "FAILED"


class PolicyDraftTestType(str, Enum):
    """Classification of test origin."""
    AUTO_GENERATED = "AUTO_GENERATED"
    HUMAN_AUTHORED = "HUMAN_AUTHORED"


# ------------------------------------------------------------------------------
# Policy Draft Model
# ------------------------------------------------------------------------------

class PolicyDraft(Base):
    """Represents a formal policy proposal in the authoring pipeline.
    
    A draft moves through authoring, validation, testing, and supervisor review
    to reach STAGED. It does NOT activate.
    """

    __tablename__ = "policy_drafts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scheme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schemes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    policy_title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    lifecycle_status: Mapped[PolicyDraftLifecycleStatus] = mapped_column(
        SAEnum(PolicyDraftLifecycleStatus, name="policy_draft_lifecycle_status_enum", native_enum=True),
        default=PolicyDraftLifecycleStatus.DRAFT,
        nullable=False,
        index=True,
    )

    # Optional reference to Phase 15 approved discovery candidate
    source_candidate_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("policy_discovery_candidates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Source Provenance snapshot
    source_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    source_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_publisher: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_document_identifier: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    source_publication_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    source_effective_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    source_retrieved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    source_excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    provenance_status: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    adversarial_flag_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    candidate_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Authored AST and Canonical Compiled Output
    authored_rules_json: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    canonical_rules_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    rule_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    schema_version: Mapped[str] = mapped_column(String(32), default="1.0", nullable=False)
    compiler_version: Mapped[str] = mapped_column(String(32), default="1.0", nullable=False)

    # Temporality
    effective_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Parent version comparison (for diff)
    parent_policy_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("policy_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    change_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Static Validation and Testing Reports
    validation_status: Mapped[PolicyDraftValidationStatus] = mapped_column(
        SAEnum(PolicyDraftValidationStatus, name="policy_draft_validation_status_enum", native_enum=True),
        default=PolicyDraftValidationStatus.NOT_VALIDATED,
        nullable=False,
    )
    validation_details_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    test_status: Mapped[PolicyDraftTestStatus] = mapped_column(
        SAEnum(PolicyDraftTestStatus, name="policy_draft_test_status_enum", native_enum=True),
        default=PolicyDraftTestStatus.NOT_TESTED,
        nullable=False,
    )
    test_summary_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Authorship and Audit Tracking
    author_id: Mapped[str] = mapped_column(String(255), nullable=False)
    author_role: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reviewed_by_role: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    reviewer_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    staged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    staged_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    staged_by_role: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Relationships
    scheme: Mapped["Scheme"] = relationship("Scheme")
    source_candidate: Mapped[Optional["PolicyDiscoveryCandidate"]] = relationship("PolicyDiscoveryCandidate")
    parent_policy_version: Mapped[Optional["PolicyVersion"]] = relationship("PolicyVersion")
    audit_events: Mapped[List["PolicyDraftAuditEvent"]] = relationship(
        "PolicyDraftAuditEvent",
        back_populates="draft",
        cascade="all, delete-orphan",
        order_by="PolicyDraftAuditEvent.created_at.asc()",
    )
    revisions: Mapped[List["PolicyDraftRevision"]] = relationship(
        "PolicyDraftRevision",
        back_populates="draft",
        cascade="all, delete-orphan",
        order_by="PolicyDraftRevision.revision_number.asc()",
    )
    tests: Mapped[List["PolicyDraftTest"]] = relationship(
        "PolicyDraftTest",
        back_populates="draft",
        cascade="all, delete-orphan",
        order_by="PolicyDraftTest.created_at.asc()",
    )

    def __repr__(self) -> str:
        return f"<PolicyDraft(id={self.id}, title={self.policy_title!r}, status={self.lifecycle_status.value})>"


# ------------------------------------------------------------------------------
# Append-Only Audit Trail
# ------------------------------------------------------------------------------

class PolicyDraftAuditEvent(Base):
    """Application-level append-only audit trail protected by authorization.
    
    Records lifecycle transitions and supervisory determinations without mutation or deletion.
    """

    __tablename__ = "policy_draft_audit_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    draft_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("policy_drafts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_identity: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_status: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    new_status: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    details_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    draft: Mapped["PolicyDraft"] = relationship("PolicyDraft", back_populates="audit_events")

    def __repr__(self) -> str:
        return f"<PolicyDraftAuditEvent(id={self.id}, action={self.action}, to={self.new_status})>"


# ------------------------------------------------------------------------------
# Versioned Ruleset Revision History
# ------------------------------------------------------------------------------

class PolicyDraftRevision(Base):
    """Versioned snapshot of authored rules for full traceability across edits."""

    __tablename__ = "policy_draft_revisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    draft_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("policy_drafts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    author_id: Mapped[str] = mapped_column(String(255), nullable=False)
    author_role: Mapped[str] = mapped_column(String(64), nullable=False)
    change_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    previous_rule_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    new_rule_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    rules_snapshot_json: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    draft: Mapped["PolicyDraft"] = relationship("PolicyDraft", back_populates="revisions")

    def __repr__(self) -> str:
        return f"<PolicyDraftRevision(id={self.id}, rev={self.revision_number}, hash={self.new_rule_hash})>"


# ------------------------------------------------------------------------------
# Test Specifications and Results
# ------------------------------------------------------------------------------

class PolicyDraftTest(Base):
    """Deterministic test case associated with a policy draft."""

    __tablename__ = "policy_draft_tests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    draft_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("policy_drafts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    test_type: Mapped[PolicyDraftTestType] = mapped_column(
        SAEnum(PolicyDraftTestType, name="policy_draft_test_type_enum", native_enum=True),
        default=PolicyDraftTestType.AUTO_GENERATED,
        nullable=False,
    )
    facts_json: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    expected_result: Mapped[str] = mapped_column(String(32), nullable=False)  # ELIGIBLE, INELIGIBLE, UNKNOWN
    actual_result: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)  # PENDING, PASSED, FAILED
    execution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    draft: Mapped["PolicyDraft"] = relationship("PolicyDraft", back_populates="tests")

    def __repr__(self) -> str:
        return f"<PolicyDraftTest(id={self.id}, name={self.name!r}, status={self.status})>"
