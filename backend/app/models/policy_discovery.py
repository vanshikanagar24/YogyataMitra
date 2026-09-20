"""SQLAlchemy ORM models for AI-Assisted Policy Discovery Candidates and Audit Trail.

Represents candidate policy statements discovered by AI from official government sources,
awaiting human inspection and determination (APPROVE, REJECT, or REQUEST_CLARIFICATION).

NON-NEGOTIABLE SAFETY BOUNDARY:
- PolicyDiscoveryCandidate is strictly inert data awaiting human review.
- It is NOT a PolicyVersion, NOT a RuleSet, and NOT executable policy.
- Approval accepts candidate for future policy-authoring consideration; it does NOT activate statutory rules.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.scheme import Scheme


# ------------------------------------------------------------------------------
# Controlled Enumerations for Policy Discovery
# ------------------------------------------------------------------------------

class CandidateType(str, Enum):
    """Controlled classification of discovered policy candidate intelligence."""
    ELIGIBILITY_CONDITION = "ELIGIBILITY_CONDITION"
    EXCLUSION = "EXCLUSION"
    DEFINITIONS = "DEFINITIONS"
    DOCUMENTATION_REQUIREMENT = "DOCUMENTATION_REQUIREMENT"
    PROCEDURAL_REQUIREMENT = "PROCEDURAL_REQUIREMENT"
    BENEFIT_PARAMETER = "BENEFIT_PARAMETER"
    EFFECTIVE_DATE = "EFFECTIVE_DATE"
    AMENDMENT = "AMENDMENT"
    CLARIFICATION = "CLARIFICATION"
    SOURCE_REFERENCE = "SOURCE_REFERENCE"


class ProvenanceStatus(str, Enum):
    """Source provenance assurance status separating domain recognition from human review."""
    UNVERIFIED = "UNVERIFIED"
    OFFICIAL_DOMAIN_MATCH = "OFFICIAL_DOMAIN_MATCH"
    SOURCE_RETRIEVED = "SOURCE_RETRIEVED"
    PROVENANCE_REVIEW_REQUIRED = "PROVENANCE_REVIEW_REQUIRED"
    REVIEWED_BY_AUTHORIZED_REVIEWER = "REVIEWED_BY_AUTHORIZED_REVIEWER"
    # Legacy subtypes retained for backward compatibility
    OFFICIAL_GAZETTE = "OFFICIAL_GAZETTE"
    OFFICIAL_PORTAL = "OFFICIAL_PORTAL"
    OFFICIAL_CIRCULAR = "OFFICIAL_CIRCULAR"
    SECONDARY_OFFICIAL = "SECONDARY_OFFICIAL"
    UNKNOWN = "UNKNOWN"
    CONFLICT_DETECTED = "CONFLICT_DETECTED"


class CandidateReviewStatus(str, Enum):
    """Strict lifecycle review states for discovered policy candidates."""
    DISCOVERED = "DISCOVERED"
    EXTRACTED = "EXTRACTED"
    PENDING_REVIEW = "PENDING_REVIEW"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    ARCHIVED = "ARCHIVED"


class EffectiveDateStatus(str, Enum):
    """Resolution status of candidate statutory effective date."""
    CONFIRMED = "CONFIRMED"
    PROSPECTIVE = "PROSPECTIVE"
    RETROSPECTIVE = "RETROSPECTIVE"
    UNKNOWN = "UNKNOWN"
    AMENDMENT_PENDING = "AMENDMENT_PENDING"


class DuplicateStatus(str, Enum):
    """Duplicate candidate detection status."""
    UNIQUE = "UNIQUE"
    POSSIBLE_DUPLICATE = "POSSIBLE_DUPLICATE"
    CONFIRMED_DUPLICATE = "CONFIRMED_DUPLICATE"


# ------------------------------------------------------------------------------
# Policy Discovery Candidate Model
# ------------------------------------------------------------------------------

class PolicyDiscoveryCandidate(Base):
    """Represents a proposed piece of policy intelligence discovered by AI.
    
    A candidate is non-executable proposal data awaiting authorized officer review.
    """

    __tablename__ = "policy_discovery_candidates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scheme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schemes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    candidate_type: Mapped[CandidateType] = mapped_column(
        SAEnum(CandidateType, name="candidate_type_enum", native_enum=True),
        nullable=False,
        index=True,
    )
    candidate_text_en: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_text_hi: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_concept: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )

    # Source Provenance
    source_url: Mapped[str] = mapped_column(String(512), nullable=False)
    source_title: Mapped[str] = mapped_column(String(256), nullable=False)
    source_publisher: Mapped[str] = mapped_column(String(256), nullable=False)
    source_document_identifier: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True
    )
    source_publication_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source_effective_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source_excerpt: Mapped[str] = mapped_column(Text, nullable=False)

    # AI Discovery Telemetry
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    adversarial_flag_detected: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    discovered_by: Mapped[str] = mapped_column(
        String(128), nullable=False, default="AI_POLICY_DISCOVERY_AGENT"
    )
    ai_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    ai_model: Mapped[str] = mapped_column(String(64), nullable=False)
    ai_run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    extraction_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    uncertainty_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    questions_for_reviewer: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    # Status & Flags
    provenance_status: Mapped[ProvenanceStatus] = mapped_column(
        SAEnum(ProvenanceStatus, name="provenance_status_enum", native_enum=True),
        default=ProvenanceStatus.UNKNOWN,
        nullable=False,
        index=True,
    )
    effective_date_status: Mapped[EffectiveDateStatus] = mapped_column(
        SAEnum(EffectiveDateStatus, name="effective_date_status_enum", native_enum=True),
        default=EffectiveDateStatus.UNKNOWN,
        nullable=False,
    )
    conflict_detected: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    conflict_details_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    duplicate_status: Mapped[DuplicateStatus] = mapped_column(
        SAEnum(DuplicateStatus, name="duplicate_status_enum", native_enum=True),
        default=DuplicateStatus.UNIQUE,
        nullable=False,
    )
    duplicate_of_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("policy_discovery_candidates.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Human Review Lifecycle
    review_status: Mapped[CandidateReviewStatus] = mapped_column(
        SAEnum(CandidateReviewStatus, name="candidate_review_status_enum", native_enum=True),
        default=CandidateReviewStatus.PENDING_REVIEW,
        nullable=False,
        index=True,
    )
    reviewer_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    reviewer_role: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reviewer_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    scheme: Mapped["Scheme"] = relationship("Scheme")
    review_events: Mapped[List["PolicyDiscoveryReviewEvent"]] = relationship(
        "PolicyDiscoveryReviewEvent",
        back_populates="candidate",
        cascade="all, delete-orphan",
        order_by="PolicyDiscoveryReviewEvent.created_at.asc()",
    )

    def __repr__(self) -> str:
        return (
            f"<PolicyDiscoveryCandidate(id={self.id}, concept={self.normalized_concept!r}, "
            f"type={self.candidate_type.value}, status={self.review_status.value})>"
        )


# ------------------------------------------------------------------------------
# Policy Discovery Review Audit Event Model
# ------------------------------------------------------------------------------

class PolicyDiscoveryReviewEvent(Base):
    """Immutable append-only audit event capturing every transition and determination."""

    __tablename__ = "policy_discovery_review_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("policy_discovery_candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_identity: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_status: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    new_status: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    details_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    candidate: Mapped["PolicyDiscoveryCandidate"] = relationship(
        "PolicyDiscoveryCandidate", back_populates="review_events"
    )

    def __repr__(self) -> str:
        return (
            f"<PolicyDiscoveryReviewEvent(id={self.id}, candidate_id={self.candidate_id}, "
            f"action={self.action!r}, actor={self.actor_identity!r})>"
        )
