"""SQLAlchemy models for Official Sources, Official Documents, and Policy Provenance."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
import uuid

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
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import (
    DocumentVersionStatus,
    OfficialDocumentType,
    OfficialSourceType,
    PolicySourceBindingType,
    ProvenanceCompleteness,
    ProvenanceEventType,
)

if TYPE_CHECKING:
    from app.models.scheme import PolicyVersion, Scheme


class OfficialSource(Base):
    """Canonical registry entity for an authoritative government publisher or portal."""

    __tablename__ = "official_sources"

    __table_args__ = (
        Index("ix_official_sources_scheme_code", "scheme_code"),
        Index("ix_official_sources_domain", "official_domain"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scheme_code: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True
    )
    publisher_name: Mapped[str] = mapped_column(String(255), nullable=False)
    publisher_type: Mapped[OfficialSourceType] = mapped_column(
        SAEnum(OfficialSourceType, name="official_source_type_enum", native_enum=True),
        nullable=False,
    )
    official_domain: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_url: Mapped[str] = mapped_column(String(512), nullable=False)
    source_type: Mapped[OfficialSourceType] = mapped_column(
        SAEnum(OfficialSourceType, name="official_source_type_enum", native_enum=True),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
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
    documents: Mapped[List["OfficialDocument"]] = relationship(
        "OfficialDocument",
        back_populates="official_source",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<OfficialSource(publisher={self.publisher_name!r}, domain={self.official_domain!r})>"


class OfficialDocument(Base):
    """Canonical registry entity for an official statutory document or guideline."""

    __tablename__ = "official_documents"

    __table_args__ = (
        Index("ix_official_documents_scheme_code", "scheme_code"),
        Index("ix_official_documents_source_id", "official_source_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    official_source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("official_sources.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    scheme_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    document_title: Mapped[str] = mapped_column(String(255), nullable=False)
    document_type: Mapped[OfficialDocumentType] = mapped_column(
        SAEnum(OfficialDocumentType, name="official_document_type_enum", native_enum=True),
        nullable=False,
    )
    issuing_authority: Mapped[str] = mapped_column(String(255), nullable=False)
    reference_number: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    publication_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    effective_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    official_url: Mapped[str] = mapped_column(String(512), nullable=False)
    language: Mapped[str] = mapped_column(String(16), default="en", nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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
    official_source: Mapped["OfficialSource"] = relationship(
        "OfficialSource", back_populates="documents"
    )
    versions: Mapped[List["OfficialDocumentVersion"]] = relationship(
        "OfficialDocumentVersion",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="OfficialDocumentVersion.created_at.desc()",
    )

    def __repr__(self) -> str:
        return f"<OfficialDocument(title={self.document_title!r}, ref={self.reference_number!r})>"


class OfficialDocumentVersion(Base):
    """Specific revision or edition of an official document with cryptographic integrity."""

    __tablename__ = "official_document_versions"

    __table_args__ = (
        UniqueConstraint("document_id", "version_label", name="uq_doc_version_label"),
        Index("ix_official_doc_versions_doc_id", "document_id"),
        Index("ix_official_doc_versions_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("official_documents.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    version_label: Mapped[str] = mapped_column(String(64), nullable=False)
    document_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )  # SHA-256 digest of stored artifact
    hash_algorithm: Mapped[str] = mapped_column(
        String(32), default="SHA-256", nullable=False
    )
    published_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    effective_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    retrieved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    official_url: Mapped[str] = mapped_column(String(512), nullable=False)
    content_reference: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True
    )  # Local storage path if artifact stored on disk; None if metadata-only
    byte_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    supersedes_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("official_document_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[DocumentVersionStatus] = mapped_column(
        SAEnum(DocumentVersionStatus, name="document_version_status_enum", native_enum=True),
        default=DocumentVersionStatus.ACTIVE,
        nullable=False,
    )
    provenance_completeness: Mapped[ProvenanceCompleteness] = mapped_column(
        SAEnum(ProvenanceCompleteness, name="provenance_completeness_enum", native_enum=True),
        default=ProvenanceCompleteness.COMPLETE,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    document: Mapped["OfficialDocument"] = relationship(
        "OfficialDocument", back_populates="versions"
    )
    superseded_by: Mapped[List["OfficialDocumentVersion"]] = relationship(
        "OfficialDocumentVersion",
        back_populates="supersedes_version",
        remote_side="OfficialDocumentVersion.supersedes_version_id",
    )
    supersedes_version: Mapped[Optional["OfficialDocumentVersion"]] = relationship(
        "OfficialDocumentVersion",
        remote_side="OfficialDocumentVersion.id",
        back_populates="superseded_by",
    )
    policy_bindings: Mapped[List["PolicySourceBinding"]] = relationship(
        "PolicySourceBinding",
        back_populates="document_version",
        cascade="all, delete-orphan",
    )
    rule_provenances: Mapped[List["RuleProvenance"]] = relationship(
        "RuleProvenance",
        back_populates="document_version",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<OfficialDocumentVersion(label={self.version_label!r}, status={self.status.value})>"


class PolicySourceBinding(Base):
    """Explicit link binding an active or historical PolicyVersion to supporting OfficialDocumentVersions."""

    __tablename__ = "policy_source_bindings"

    __table_args__ = (
        UniqueConstraint(
            "policy_version_id", "document_version_id", name="uq_policy_doc_binding"
        ),
        Index("ix_policy_source_bindings_pv", "policy_version_id"),
        Index("ix_policy_source_bindings_dv", "document_version_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    policy_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("policy_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    document_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("official_document_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    binding_type: Mapped[PolicySourceBindingType] = mapped_column(
        SAEnum(PolicySourceBindingType, name="policy_source_binding_type_enum", native_enum=True),
        default=PolicySourceBindingType.PRIMARY_SOURCE,
        nullable=False,
    )
    citation: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    policy_version: Mapped["PolicyVersion"] = relationship(
        "PolicyVersion", back_populates="source_bindings"
    )
    document_version: Mapped["OfficialDocumentVersion"] = relationship(
        "OfficialDocumentVersion", back_populates="policy_bindings"
    )

    def __repr__(self) -> str:
        return f"<PolicySourceBinding(pv={self.policy_version_id}, dv={self.document_version_id}, type={self.binding_type.value})>"


class RuleProvenance(Base):
    """Fine-grained provenance anchoring an individual AST Rule to an official source clause."""

    __tablename__ = "rule_provenances"

    __table_args__ = (
        UniqueConstraint(
            "rule_id",
            "policy_version_id",
            "document_version_id",
            name="uq_rule_policy_doc_prov",
        ),
        Index("ix_rule_prov_rule_policy", "rule_id", "policy_version_id"),
        Index("ix_rule_prov_doc_ver", "document_version_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    rule_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    policy_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("policy_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    document_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("official_document_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    citation: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_locator: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True
    )  # e.g., Clause 4.1(e), Rule 4(1), Section 3
    provenance_type: Mapped[str] = mapped_column(
        String(64), default="STATUTORY_RULE", nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    policy_version: Mapped["PolicyVersion"] = relationship(
        "PolicyVersion", back_populates="rule_provenances"
    )
    document_version: Mapped["OfficialDocumentVersion"] = relationship(
        "OfficialDocumentVersion", back_populates="rule_provenances"
    )

    def __repr__(self) -> str:
        return f"<RuleProvenance(rule={self.rule_id!r}, locator={self.source_locator!r})>"


class ProvenanceAuditEvent(Base):
    """Immutable audit trail for all modifications and lifecycle transitions of official provenance."""

    __tablename__ = "provenance_audit_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_type: Mapped[ProvenanceEventType] = mapped_column(
        SAEnum(ProvenanceEventType, name="provenance_event_type_enum", native_enum=True),
        nullable=False,
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    actor_role: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    previous_state: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True
    )
    new_state: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<ProvenanceAuditEvent(event={self.event_type.value}, entity={self.entity_type}, id={self.entity_id})>"
