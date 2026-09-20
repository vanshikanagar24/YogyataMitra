"""SQLAlchemy ORM models for Human Review and Append-Only Audit Trail."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import HumanReviewStatus

if TYPE_CHECKING:
    from app.models.evaluation import EvaluationTrace
    from app.models.journey import EvaluationJourney


class HumanReview(Base):
    """Represents an official human verification review case for an evaluation journey."""

    __tablename__ = "human_reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    journey_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluation_journeys.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evaluation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluation_traces.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reviewer_identity: Mapped[str] = mapped_column(
        String(128), nullable=False
    )
    reviewer_role: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    status: Mapped[HumanReviewStatus] = mapped_column(
        Enum(HumanReviewStatus, name="human_review_status_enum", native_enum=True),
        default=HumanReviewStatus.PENDING,
        nullable=False,
        index=True,
    )
    decision: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )
    reason: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    details_json: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True
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
    journey: Mapped["EvaluationJourney"] = relationship("EvaluationJourney")
    evaluation: Mapped[Optional["EvaluationTrace"]] = relationship("EvaluationTrace")
    audit_events: Mapped[List["HumanReviewAuditEvent"]] = relationship(
        "HumanReviewAuditEvent",
        back_populates="review",
        cascade="all, delete-orphan",
        order_by="HumanReviewAuditEvent.created_at.asc()",
    )

    def __repr__(self) -> str:
        return (
            f"<HumanReview(id={self.id}, journey_id={self.journey_id}, "
            f"status={self.status.value}, reviewer={self.reviewer_identity!r})>"
        )


class HumanReviewAuditEvent(Base):
    """Immutable append-only audit record capturing every reviewer action on a case."""

    __tablename__ = "human_review_audit_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("human_reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    journey_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluation_journeys.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_identity: Mapped[str] = mapped_column(
        String(128), nullable=False
    )
    actor_role: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    action: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    previous_status: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )
    new_status: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    reason: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    details_json: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    review: Mapped["HumanReview"] = relationship(
        "HumanReview", back_populates="audit_events"
    )

    def __repr__(self) -> str:
        return (
            f"<HumanReviewAuditEvent(id={self.id}, action={self.action!r}, "
            f"actor={self.actor_identity!r}, new_status={self.new_status!r})>"
        )
