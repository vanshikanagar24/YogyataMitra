"""SQLAlchemy model for persistent evaluation traces and audit history."""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import EligibilityResult


class EvaluationTrace(Base):
    """Represents a persistent trace and audit snapshot of an eligibility evaluation."""

    __tablename__ = "evaluation_traces"

    __table_args__ = (
        Index(
            "ix_eval_trace_lookup",
            "citizen_id",
            "scheme_id",
            "policy_version_id",
            "evaluation_date",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    citizen_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("citizens.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    scheme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schemes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    policy_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("policy_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    journey_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluation_journeys.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    evaluated_by: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    evaluation_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    input_snapshot_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    result_state: Mapped[EligibilityResult] = mapped_column(
        Enum(EligibilityResult, name="eligibility_result_enum", native_enum=True),
        nullable=False,
        index=True,
    )
    trace_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    rule_definition_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    trace_schema_version: Mapped[str] = mapped_column(
        String(16), server_default="1.0.0", default="1.0.0", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    citizen = relationship("Citizen", back_populates="evaluation_traces")
    scheme = relationship("Scheme", back_populates="evaluation_traces")
    policy_version = relationship("PolicyVersion", back_populates="evaluation_traces")
    journey = relationship("EvaluationJourney", back_populates="evaluation_traces", foreign_keys=[journey_id])

    def __repr__(self) -> str:
        return f"<EvaluationTrace(id={self.id}, scheme_id={self.scheme_id}, result={self.result_state.value})>"
