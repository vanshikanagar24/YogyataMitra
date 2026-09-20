"""SQLAlchemy models for EvaluationJourney and JourneyTransitionRecord."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import JourneyState

if TYPE_CHECKING:
    from app.models.citizen import Citizen, Claim
    from app.models.evaluation import EvaluationTrace
    from app.models.scheme import Scheme


class EvaluationJourney(Base):
    """Represents an end-to-end citizen welfare evaluation session/journey."""

    __tablename__ = "evaluation_journeys"

    __table_args__ = (
        Index("ix_journey_citizen_scheme", "citizen_id", "scheme_id"),
        Index("ix_journey_state", "state"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    citizen_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("citizens.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scheme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schemes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    state: Mapped[JourneyState] = mapped_column(
        Enum(JourneyState, name="journey_state_enum", native_enum=True),
        default=JourneyState.DRAFT,
        nullable=False,
    )
    latest_evaluation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluation_traces.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
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
    citizen: Mapped["Citizen"] = relationship("Citizen")
    scheme: Mapped["Scheme"] = relationship("Scheme")
    latest_evaluation: Mapped[Optional["EvaluationTrace"]] = relationship(
        "EvaluationTrace", foreign_keys=[latest_evaluation_id]
    )
    claims: Mapped[List["Claim"]] = relationship(
        "Claim", back_populates="journey", cascade="all, delete-orphan"
    )
    transitions: Mapped[List["JourneyTransitionRecord"]] = relationship(
        "JourneyTransitionRecord",
        back_populates="journey",
        cascade="all, delete-orphan",
        order_by="JourneyTransitionRecord.created_at.asc()",
    )

    def __repr__(self) -> str:
        return f"<EvaluationJourney(id={self.id}, state={self.state.value})>"


class JourneyTransitionRecord(Base):
    """Immutable audit record tracking an evaluated state transition in a journey."""

    __tablename__ = "journey_transition_records"

    __table_args__ = (
        Index("ix_journey_transition_journey_id", "journey_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    journey_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluation_journeys.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_state: Mapped[JourneyState] = mapped_column(
        Enum(JourneyState, name="journey_state_enum", native_enum=True),
        nullable=False,
    )
    to_state: Mapped[JourneyState] = mapped_column(
        Enum(JourneyState, name="journey_state_enum", native_enum=True),
        nullable=False,
    )
    actor: Mapped[str] = mapped_column(
        String(64), default="CITIZEN", nullable=False
    )
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    journey: Mapped["EvaluationJourney"] = relationship(
        "EvaluationJourney", back_populates="transitions"
    )

    def __repr__(self) -> str:
        return (
            f"<JourneyTransitionRecord({self.from_state.value} -> {self.to_state.value}, "
            f"actor={self.actor!r})>"
        )
