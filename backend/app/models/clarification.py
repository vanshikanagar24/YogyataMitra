"""SQLAlchemy model for Clarification Requests in Phase E."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import ClarificationStatus

if TYPE_CHECKING:
    from app.models.citizen import Claim, Evidence
    from app.models.journey import EvaluationJourney


class ClarificationRequest(Base):
    """Represents an official officer request for citizen clarification on submitted evidence/claims."""

    __tablename__ = "clarification_requests"

    __table_args__ = (
        Index("ix_clarification_journey_id", "journey_id"),
        Index("ix_clarification_evidence_id", "evidence_id"),
        Index("ix_clarification_claim_id", "claim_id"),
        Index("ix_clarification_status", "status"),
        Index("ix_clarification_round", "journey_id", "round"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    journey_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluation_journeys.id", ondelete="CASCADE"),
        nullable=False,
    )
    claim_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="SET NULL"),
        nullable=True,
    )
    evidence_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence.id", ondelete="SET NULL"),
        nullable=True,
    )
    round: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False
    )
    requesting_officer: Mapped[str] = mapped_column(
        String(128), nullable=False
    )
    requesting_officer_role: Mapped[str] = mapped_column(
        String(64), default="OFFICER", nullable=False
    )
    request_reason: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    status: Mapped[ClarificationStatus] = mapped_column(
        Enum(ClarificationStatus, name="clarification_status_enum", native_enum=True),
        default=ClarificationStatus.OPEN,
        nullable=False,
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    response_text: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    responded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    replacement_evidence_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolution_notes: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_by: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True
    )
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
    journey: Mapped["EvaluationJourney"] = relationship(
        "EvaluationJourney", back_populates="clarification_requests"
    )
    claim: Mapped[Optional["Claim"]] = relationship("Claim")
    evidence: Mapped[Optional["Evidence"]] = relationship(
        "Evidence", foreign_keys=[evidence_id]
    )
    replacement_evidence: Mapped[Optional["Evidence"]] = relationship(
        "Evidence", foreign_keys=[replacement_evidence_id]
    )

    def __repr__(self) -> str:
        return (
            f"<ClarificationRequest(id={self.id}, journey_id={self.journey_id}, "
            f"round={self.round}, status={self.status.value})>"
        )
