"""SQLAlchemy models for Citizen, Claim, Evidence, and VerificationRecord."""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import ClaimStatus, EvidenceStatus, VerificationStatus

if TYPE_CHECKING:
    from app.models.evaluation import EvaluationTrace
    from app.models.journey import EvaluationJourney


class Citizen(Base):
    """Represents a synthetic citizen profile (no real PII or Aadhaar data)."""

    __tablename__ = "citizens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    synthetic_reference: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    display_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    district: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
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
    claims: Mapped[List["Claim"]] = relationship(
        "Claim", back_populates="citizen", cascade="all, delete-orphan"
    )
    evaluation_traces: Mapped[List["EvaluationTrace"]] = relationship(
        "EvaluationTrace", back_populates="citizen"
    )

    def __repr__(self) -> str:
        return f"<Citizen(ref={self.synthetic_reference!r})>"


class Claim(Base):
    """Represents an asserted attribute or fact provided about a citizen."""

    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    citizen_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("citizens.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    claim_type: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    value_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source: Mapped[str] = mapped_column(
        String(64), default="SELF_DECLARATION", nullable=False
    )
    status: Mapped[ClaimStatus] = mapped_column(
        Enum(ClaimStatus, name="claim_status_enum", native_enum=True),
        default=ClaimStatus.CLAIMED,
        nullable=False,
    )
    claimed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    journey_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluation_journeys.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    citizen: Mapped["Citizen"] = relationship("Citizen", back_populates="claims")
    journey: Mapped[Optional["EvaluationJourney"]] = relationship(
        "EvaluationJourney", back_populates="claims"
    )
    evidence_items: Mapped[List["Evidence"]] = relationship(
        "Evidence", back_populates="claim", cascade="all, delete-orphan"
    )
    verification_records: Mapped[List["VerificationRecord"]] = relationship(
        "VerificationRecord", back_populates="claim"
    )

    def __repr__(self) -> str:
        return f"<Claim(id={self.id}, type={self.claim_type!r}, status={self.status.value})>"


class Evidence(Base):
    """Represents supporting documentary or electronic material submitted for a claim."""

    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    claim_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evidence_type: Mapped[str] = mapped_column(
        String(128), index=True, nullable=False
    )
    storage_reference: Mapped[str] = mapped_column(String(512), nullable=False)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    status: Mapped[EvidenceStatus] = mapped_column(
        Enum(EvidenceStatus, name="evidence_status_enum", native_enum=True),
        default=EvidenceStatus.PENDING,
        nullable=False,
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rejected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    claim: Mapped["Claim"] = relationship("Claim", back_populates="evidence_items")
    verification_records: Mapped[List["VerificationRecord"]] = relationship(
        "VerificationRecord", back_populates="evidence"
    )

    def __repr__(self) -> str:
        return f"<Evidence(id={self.id}, type={self.evidence_type!r}, status={self.status.value})>"


class VerificationRecord(Base):
    """Represents an audit-preserving record of a verification determination."""

    __tablename__ = "verification_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    evidence_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidence.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    claim_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    verification_method: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus, name="verification_status_enum", native_enum=True),
        default=VerificationStatus.PENDING,
        nullable=False,
    )
    verified_by: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    details_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    evidence: Mapped[Optional["Evidence"]] = relationship(
        "Evidence", back_populates="verification_records"
    )
    claim: Mapped[Optional["Claim"]] = relationship(
        "Claim", back_populates="verification_records"
    )

    def __repr__(self) -> str:
        return f"<VerificationRecord(id={self.id}, method={self.verification_method!r}, status={self.status.value})>"
