"""SQLAlchemy models for Officer Assignment, Workload, and SLA Tracking."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
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
from app.models.enums import AssignmentStatus

if TYPE_CHECKING:
    from app.models.journey import EvaluationJourney


class OfficerAssignment(Base):
    """Represents an operational verification assignment of an evaluation journey to an officer."""

    __tablename__ = "officer_assignments"

    __table_args__ = (
        Index("ix_officer_assignment_journey_id", "journey_id"),
        Index("ix_officer_assignment_officer_identity", "officer_identity"),
        Index("ix_officer_assignment_is_active", "is_active"),
        Index("ix_officer_assignment_status", "status"),
        Index("ix_officer_assignment_due_at", "due_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    journey_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluation_journeys.id", ondelete="CASCADE"),
        nullable=False,
    )
    officer_identity: Mapped[str] = mapped_column(
        String(128), nullable=False
    )
    officer_name: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True
    )
    assigned_by: Mapped[str] = mapped_column(
        String(128), default="SYSTEM_BALANCER", nullable=False
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    due_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    sla_duration_hours: Mapped[int] = mapped_column(
        Integer, default=48, nullable=False
    )
    status: Mapped[AssignmentStatus] = mapped_column(
        Enum(AssignmentStatus, name="assignment_status_enum", native_enum=True),
        default=AssignmentStatus.ASSIGNED,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    reassigned_to_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("officer_assignments.id", ondelete="SET NULL"),
        nullable=True,
    )
    reassignment_reason: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
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
        "EvaluationJourney", back_populates="assignments"
    )
    reassigned_to: Mapped[Optional["OfficerAssignment"]] = relationship(
        "OfficerAssignment", remote_side=[id]
    )

    def __repr__(self) -> str:
        return (
            f"<OfficerAssignment(id={self.id}, journey_id={self.journey_id}, "
            f"officer={self.officer_identity!r}, status={self.status.value}, active={self.is_active})>"
        )
