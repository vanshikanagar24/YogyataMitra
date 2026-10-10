"""SQLAlchemy models for Schemes, Policy Versions, and Rule Sets."""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import SchemeStatus

if TYPE_CHECKING:
    from app.models.evaluation import EvaluationTrace
    from app.models.provenance import PolicySourceBinding, RuleProvenance


class Scheme(Base):
    """Represents a government welfare scheme/program."""

    __tablename__ = "schemes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scheme_code: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    name_hi: Mapped[str] = mapped_column(String(255), nullable=False)
    description_en: Mapped[str] = mapped_column(Text, nullable=False)
    description_hi: Mapped[str] = mapped_column(Text, nullable=False)
    ministry: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    official_url: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[SchemeStatus] = mapped_column(
        Enum(SchemeStatus, name="scheme_status_enum", native_enum=True),
        default=SchemeStatus.ACTIVE,
        nullable=False,
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
    policy_versions: Mapped[List["PolicyVersion"]] = relationship(
        "PolicyVersion",
        back_populates="scheme",
        cascade="all, delete-orphan",
        order_by="PolicyVersion.effective_from.desc()",
    )
    evaluation_traces: Mapped[List["EvaluationTrace"]] = relationship(
        "EvaluationTrace", back_populates="scheme"
    )

    def __repr__(self) -> str:
        return f"<Scheme(code={self.scheme_code!r}, status={self.status.value})>"


class PolicyVersion(Base):
    """Represents a time-bounded version of a scheme's governing policy/rules."""

    __tablename__ = "policy_versions"

    __table_args__ = (
        UniqueConstraint("scheme_id", "version_code", name="uq_scheme_version_code"),
        Index("ix_policy_version_lookup", "scheme_id", "effective_from", "effective_to"),
        CheckConstraint(
            "effective_to IS NULL OR effective_from <= effective_to",
            name="chk_policy_effective_dates",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scheme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schemes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    version_code: Mapped[str] = mapped_column(String(64), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    source_url: Mapped[str] = mapped_column(String(512), nullable=False)
    source_title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_document_identifier: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True
    )
    rule_definition_hash: Mapped[Optional[str]] = mapped_column(
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
    scheme: Mapped["Scheme"] = relationship("Scheme", back_populates="policy_versions")
    rule_set: Mapped[Optional["RuleSet"]] = relationship(
        "RuleSet",
        back_populates="policy_version",
        uselist=False,
        cascade="all, delete-orphan",
    )
    evaluation_traces: Mapped[List["EvaluationTrace"]] = relationship(
        "EvaluationTrace", back_populates="policy_version"
    )
    source_bindings: Mapped[List["PolicySourceBinding"]] = relationship(
        "PolicySourceBinding",
        back_populates="policy_version",
        cascade="all, delete-orphan",
    )
    rule_provenances: Mapped[List["RuleProvenance"]] = relationship(
        "RuleProvenance",
        back_populates="policy_version",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<PolicyVersion(scheme_id={self.scheme_id}, version={self.version_code!r}, from={self.effective_from})>"


class RuleSet(Base):
    """Declarative JSONB representation of rules associated with a PolicyVersion."""

    __tablename__ = "rule_sets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    policy_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("policy_versions.id", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
        index=True,
    )
    definition_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    schema_version: Mapped[str] = mapped_column(
        String(32), default="1.0", nullable=False
    )
    rule_set_version: Mapped[str] = mapped_column(
        String(32), default="1.0", nullable=False
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
    policy_version: Mapped["PolicyVersion"] = relationship(
        "PolicyVersion", back_populates="rule_set"
    )

    def __repr__(self) -> str:
        return f"<RuleSet(id={self.id}, policy_version_id={self.policy_version_id})>"
