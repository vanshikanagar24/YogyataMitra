"""Pydantic schemas for Official Document & Policy Provenance API."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.models.enums import (
    DocumentVersionStatus,
    OfficialDocumentType,
    OfficialSourceType,
    PolicySourceBindingType,
    ProvenanceCompleteness,
    ProvenanceEventType,
)


class OfficialSourceResponse(BaseModel):
    """Authoritative government publisher or official portal representation."""
    id: uuid.UUID
    scheme_code: Optional[str] = None
    publisher_name: str
    publisher_type: OfficialSourceType
    official_domain: str
    canonical_url: str
    source_type: OfficialSourceType
    description: Optional[str] = None
    active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OfficialDocumentVersionResponse(BaseModel):
    """Materialized official document version representation."""
    id: uuid.UUID
    document_id: uuid.UUID
    version_label: str
    document_hash: Optional[str] = None
    hash_algorithm: str
    published_at: Optional[date] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    retrieved_at: Optional[datetime] = None
    official_url: str
    content_reference: Optional[str] = None
    byte_size: Optional[int] = None
    mime_type: Optional[str] = None
    supersedes_version_id: Optional[uuid.UUID] = None
    status: DocumentVersionStatus
    provenance_completeness: ProvenanceCompleteness
    created_at: datetime

    @field_serializer("content_reference")
    def serialize_content_reference(self, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        v_str = str(v).strip()
        if v_str.startswith("http://") or v_str.startswith("https://"):
            return v_str
        if (
            any(v_str.startswith(p) for p in ("/", "\\", "file:", "."))
            or (len(v_str) > 1 and v_str[1] == ":")
            or ":\\" in v_str
        ):
            return None
        return v_str

    model_config = ConfigDict(from_attributes=True)


class OfficialDocumentResponse(BaseModel):
    """Statutory policy document registry entity."""
    id: uuid.UUID
    official_source_id: uuid.UUID
    scheme_code: str
    document_title: str
    document_type: OfficialDocumentType
    issuing_authority: str
    reference_number: Optional[str] = None
    publication_date: Optional[date] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    official_url: str
    language: str
    description: Optional[str] = None
    versions: List[OfficialDocumentVersionResponse] = Field(default_factory=list)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BoundDocumentSummary(BaseModel):
    """Summary of an official document version bound to a policy version."""
    document_title: str
    version_label: str
    reference_number: Optional[str] = None
    official_url: str
    binding_type: PolicySourceBindingType
    citation: Optional[str] = None
    document_hash: Optional[str] = None
    hash_algorithm: str
    completeness: ProvenanceCompleteness


class PolicyVersionProvenanceSummary(BaseModel):
    """Provenance overview for a PolicyVersion."""
    policy_version_id: str
    version_code: str
    effective_from: str
    effective_to: Optional[str] = None
    canonical_rule_hash: Optional[str] = None
    source_title: str
    source_url: str
    bound_documents: List[BoundDocumentSummary] = Field(default_factory=list)
    rule_provenance_count: int


class SchemeProvenanceResponse(BaseModel):
    """Complete statutory provenance graph for a scheme."""
    scheme_code: str
    scheme_name_en: str
    scheme_name_hi: str
    ministry: Optional[str] = None
    official_url: str
    sources: List[Dict[str, Any]]
    documents: List[Dict[str, Any]]
    policy_versions: List[PolicyVersionProvenanceSummary]


class RuleProvenanceDetail(BaseModel):
    """Fine-grained provenance detail for an AST rule."""
    rule_id: str
    source_locator: Optional[str] = None
    citation: Optional[str] = None
    provenance_type: str
    notes: Optional[str] = None
    policy_version: Dict[str, Any]
    document: Dict[str, Any]
    official_source: Dict[str, Any]


class ProvenanceAuditEventResponse(BaseModel):
    """Immutable audit trail record for provenance changes."""
    id: str
    event_type: ProvenanceEventType
    entity_type: str
    entity_id: str
    actor_id: Optional[str] = None
    actor_role: Optional[str] = None
    previous_state: Optional[Dict[str, Any]] = None
    new_state: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None
    created_at: str
