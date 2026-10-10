"""Official Documents & Policy Provenance Service.

Provides audit-grade source registration, document versioning, cryptographic integrity (SHA-256),
policy-version bindings, rule-level provenance, and immutable audit trail tracking.
"""

from __future__ import annotations

from datetime import date, datetime
import hashlib
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple
import urllib.parse
import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import (
    DocumentVersionStatus,
    OfficialDocumentType,
    OfficialSourceType,
    PolicySourceBindingType,
    ProvenanceCompleteness,
    ProvenanceEventType,
)
from app.models.provenance import (
    OfficialDocument,
    OfficialDocumentVersion,
    OfficialSource,
    PolicySourceBinding,
    ProvenanceAuditEvent,
    RuleProvenance,
)
from app.models.scheme import PolicyVersion, RuleSet, Scheme

logger = logging.getLogger("yogyatamitra.services.provenance")

# Approved official government domain patterns for Indian welfare policy administration
OFFICIAL_GOV_DOMAIN_PATTERNS = [
    re.compile(r"^[a-zA-Z0-9.-]+\.gov\.in$"),
    re.compile(r"^[a-zA-Z0-9.-]+\.nic\.in$"),
    re.compile(r"^pmkisan\.gov\.in$"),
    re.compile(r"^maandhan\.in$"),
    re.compile(r"^pmkmy\.gov\.in$"),
    re.compile(r"^pmuy\.gov\.in$"),
    re.compile(r"^pmvishwakarma\.gov\.in$"),
    re.compile(r"^pmay-urban\.gov\.in$"),
    re.compile(r"^pmsvanidhi\.mohua\.gov\.in$"),
    re.compile(r"^nsap\.nic\.in$"),
    re.compile(r"^dea\.gov\.in$"),
    re.compile(r"^agriwelfare\.gov\.in$"),
]


# ==============================================================================
# Domain Exceptions
# ==============================================================================

class ProvenanceError(Exception):
    """Base exception for policy provenance and document integrity errors."""
    pass


class ProvenanceValidationError(ProvenanceError):
    """Raised when URL, hash, or provenance relationship fails validation."""
    pass


class ProvenanceNotFoundError(ProvenanceError):
    """Raised when a requested official source, document, or binding is not found."""
    pass


class ProvenanceConflictError(ProvenanceError):
    """Raised when an operation would violate provenance immutability or integrity."""
    pass


# ==============================================================================
# Validation Helpers
# ==============================================================================

def validate_official_url(url: str, required_domain: Optional[str] = None) -> bool:
    """Validate that an official source URL uses HTTPS, has valid syntax, and targets a legitimate domain."""
    if not url or not isinstance(url, str):
        raise ProvenanceValidationError("Official URL must be a non-empty string.")

    parsed = urllib.parse.urlparse(url.strip())
    if parsed.scheme.lower() != "https":
        raise ProvenanceValidationError(
            f"Official source URL must use secure HTTPS protocol. Found: '{parsed.scheme}' in {url}."
        )

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise ProvenanceValidationError(f"Invalid URL structure: missing hostname in '{url}'.")

    # Reject localhost, loopback, private IP ranges
    if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1") or hostname.endswith(".local"):
        raise ProvenanceValidationError(f"Private or local URLs are prohibited as official sources: '{url}'.")

    # Validate official domain
    is_official = any(pattern.match(hostname) for pattern in OFFICIAL_GOV_DOMAIN_PATTERNS)
    if not is_official:
        raise ProvenanceValidationError(
            f"Domain '{hostname}' is not recognized as an authoritative Government of India domain."
        )

    if required_domain and hostname != required_domain.lower() and not hostname.endswith("." + required_domain.lower()):
        raise ProvenanceValidationError(
            f"URL domain '{hostname}' does not match registered official source domain '{required_domain}'."
        )

    return True


def validate_document_hash(
    hash_value: Optional[str], algorithm: str = "SHA-256"
) -> bool:
    """Validate that a cryptographic document hash meets SHA-256 standards."""
    if algorithm.upper() != "SHA-256":
        raise ProvenanceValidationError(
            f"Unsupported hash algorithm '{algorithm}'. System requires SHA-256."
        )

    if hash_value is None:
        # None is permitted for metadata-only entries where physical artifact is not downloaded
        return True

    clean_hash = hash_value.strip().lower()
    if len(clean_hash) != 64 or not re.match(r"^[0-9a-f]{64}$", clean_hash):
        raise ProvenanceValidationError(
            f"Malformed document hash: must be a 64-character lowercase hexadecimal SHA-256 digest. Found: '{hash_value}'."
        )

    return True


def compute_file_sha256(file_path: Path) -> Tuple[str, int]:
    """Compute deterministic SHA-256 digest and byte size for a local document artifact."""
    if not file_path.exists() or not file_path.is_file():
        raise ProvenanceValidationError(f"Document artifact file does not exist: {file_path}")

    sha256 = hashlib.sha256()
    size = 0
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
            size += len(chunk)

    return sha256.hexdigest(), size


def sanitize_content_reference(ref: Optional[str]) -> Optional[str]:
    """Sanitize content reference to prevent server filesystem leakage in public responses.
    
    Returns None if the reference represents a local filesystem path.
    Preserves valid public HTTP/HTTPS URLs.
    """
    if not ref:
        return None
    ref_str = str(ref).strip()
    if ref_str.startswith("http://") or ref_str.startswith("https://"):
        return ref_str
    if (
        any(ref_str.startswith(p) for p in ("/", "\\", "file:", "."))
        or (len(ref_str) > 1 and ref_str[1] == ":")
        or ":\\" in ref_str
    ):
        return None
    return ref_str


# ==============================================================================
# Provenance Service Class
# ==============================================================================

class ProvenanceService:
    """Service orchestrating official document registry and policy provenance."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # --------------------------------------------------------------------------
    # Audit Logging
    # --------------------------------------------------------------------------

    async def record_audit_event(
        self,
        event_type: ProvenanceEventType,
        entity_type: str,
        entity_id: str,
        actor_id: Optional[str] = "SYSTEM",
        actor_role: Optional[str] = "SYSTEM_ADMIN",
        previous_state: Optional[Dict[str, Any]] = None,
        new_state: Optional[Dict[str, Any]] = None,
        reason: Optional[str] = None,
    ) -> ProvenanceAuditEvent:
        """Record an immutable provenance audit trail event."""
        event = ProvenanceAuditEvent(
            id=uuid.uuid4(),
            event_type=event_type,
            entity_type=entity_type,
            entity_id=str(entity_id),
            actor_id=actor_id,
            actor_role=actor_role,
            previous_state=previous_state,
            new_state=new_state,
            reason=reason,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    # --------------------------------------------------------------------------
    # I-A: Official Source Registry
    # --------------------------------------------------------------------------

    async def register_official_source(
        self,
        publisher_name: str,
        publisher_type: OfficialSourceType,
        official_domain: str,
        canonical_url: str,
        source_type: OfficialSourceType,
        scheme_code: Optional[str] = None,
        description: Optional[str] = None,
        actor_id: Optional[str] = "SYSTEM",
    ) -> OfficialSource:
        """Register or retrieve an authoritative government publisher / official portal."""
        # Validation
        validate_official_url(canonical_url, required_domain=official_domain)

        stmt = select(OfficialSource).where(
            OfficialSource.official_domain == official_domain.lower(),
            OfficialSource.publisher_name == publisher_name,
        )
        if scheme_code:
            stmt = stmt.where(OfficialSource.scheme_code == scheme_code.upper())
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            return existing

        source = OfficialSource(
            id=uuid.uuid4(),
            scheme_code=scheme_code.upper() if scheme_code else None,
            publisher_name=publisher_name,
            publisher_type=publisher_type,
            official_domain=official_domain.lower(),
            canonical_url=canonical_url,
            source_type=source_type,
            description=description,
            active=True,
        )
        self.session.add(source)
        await self.session.flush()

        await self.record_audit_event(
            event_type=ProvenanceEventType.DOCUMENT_REGISTERED,
            entity_type="OfficialSource",
            entity_id=str(source.id),
            actor_id=actor_id,
            new_state={
                "publisher_name": publisher_name,
                "domain": official_domain,
                "scheme_code": scheme_code,
            },
            reason="Official government publisher registered in provenance registry.",
        )

        return source

    # --------------------------------------------------------------------------
    # I-B: Official Document Registry
    # --------------------------------------------------------------------------

    async def register_official_document(
        self,
        official_source_id: uuid.UUID,
        scheme_code: str,
        document_title: str,
        document_type: OfficialDocumentType,
        issuing_authority: str,
        official_url: str,
        reference_number: Optional[str] = None,
        publication_date: Optional[date] = None,
        effective_from: Optional[date] = None,
        effective_to: Optional[date] = None,
        language: str = "en",
        description: Optional[str] = None,
        actor_id: Optional[str] = "SYSTEM",
    ) -> OfficialDocument:
        """Register an official document (guideline, gazette notification, framework)."""
        source = await self.session.get(OfficialSource, official_source_id)
        if not source:
            raise ProvenanceNotFoundError(f"OfficialSource '{official_source_id}' not found.")

        validate_official_url(official_url, required_domain=source.official_domain)

        # Check existing document by title & reference
        stmt = select(OfficialDocument).where(
            OfficialDocument.scheme_code == scheme_code.upper(),
            OfficialDocument.document_title == document_title,
        )
        if reference_number:
            stmt = stmt.where(OfficialDocument.reference_number == reference_number)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            return existing

        doc = OfficialDocument(
            id=uuid.uuid4(),
            official_source_id=official_source_id,
            scheme_code=scheme_code.upper(),
            document_title=document_title,
            document_type=document_type,
            issuing_authority=issuing_authority,
            reference_number=reference_number,
            publication_date=publication_date,
            effective_from=effective_from,
            effective_to=effective_to,
            official_url=official_url,
            language=language,
            description=description,
        )
        self.session.add(doc)
        await self.session.flush()

        await self.record_audit_event(
            event_type=ProvenanceEventType.DOCUMENT_REGISTERED,
            entity_type="OfficialDocument",
            entity_id=str(doc.id),
            actor_id=actor_id,
            new_state={
                "title": document_title,
                "scheme_code": scheme_code,
                "reference": reference_number,
            },
            reason="Official document registered under source.",
        )

        return doc

    # --------------------------------------------------------------------------
    # I-C & I-D: Document Versioning & Cryptographic Integrity
    # --------------------------------------------------------------------------

    async def add_document_version(
        self,
        document_id: uuid.UUID,
        version_label: str,
        official_url: str,
        document_hash: Optional[str] = None,
        hash_algorithm: str = "SHA-256",
        published_at: Optional[date] = None,
        effective_from: Optional[date] = None,
        effective_to: Optional[date] = None,
        content_reference: Optional[str] = None,
        byte_size: Optional[int] = None,
        mime_type: Optional[str] = "application/pdf",
        supersedes_version_id: Optional[uuid.UUID] = None,
        status: DocumentVersionStatus = DocumentVersionStatus.ACTIVE,
        provenance_completeness: ProvenanceCompleteness = ProvenanceCompleteness.COMPLETE,
        actor_id: Optional[str] = "SYSTEM",
    ) -> OfficialDocumentVersion:
        """Add an immutable official document version with SHA-256 integrity verification."""
        doc = await self.session.get(OfficialDocument, document_id)
        if not doc:
            raise ProvenanceNotFoundError(f"OfficialDocument '{document_id}' not found.")

        validate_official_url(official_url)
        validate_document_hash(document_hash, algorithm=hash_algorithm)

        # Check for duplicate active version label
        stmt = select(OfficialDocumentVersion).where(
            OfficialDocumentVersion.document_id == document_id,
            OfficialDocumentVersion.version_label == version_label,
        )
        res = await self.session.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing:
            if existing.status != status:
                existing.status = status
                await self.session.flush()
            return existing

        # If a local artifact file is provided, verify actual SHA-256
        actual_hash = document_hash
        actual_size = byte_size
        if content_reference:
            local_path = Path(content_reference)
            if local_path.exists() and local_path.is_file():
                computed_hash, computed_size = compute_file_sha256(local_path)
                if document_hash and document_hash.lower() != computed_hash.lower():
                    raise ProvenanceValidationError(
                        f"Document integrity mismatch: provided hash '{document_hash}' does not match "
                        f"actual file SHA-256 '{computed_hash}'."
                    )
                actual_hash = computed_hash
                actual_size = computed_size

        # If superseding an older version, transition older version to SUPERSEDED
        if supersedes_version_id:
            old_version = await self.session.get(OfficialDocumentVersion, supersedes_version_id)
            if not old_version:
                raise ProvenanceNotFoundError(f"Superseded version '{supersedes_version_id}' not found.")
            old_prev_state = {"status": old_version.status.value}
            old_version.status = DocumentVersionStatus.SUPERSEDED
            await self.session.flush()

            await self.record_audit_event(
                event_type=ProvenanceEventType.DOCUMENT_SUPERSEDED,
                entity_type="OfficialDocumentVersion",
                entity_id=str(supersedes_version_id),
                actor_id=actor_id,
                previous_state=old_prev_state,
                new_state={"status": DocumentVersionStatus.SUPERSEDED.value, "superseded_by": version_label},
                reason=f"Document version superseded by new revision '{version_label}'.",
            )

        doc_ver = OfficialDocumentVersion(
            id=uuid.uuid4(),
            document_id=document_id,
            version_label=version_label,
            document_hash=actual_hash,
            hash_algorithm=hash_algorithm,
            published_at=published_at,
            effective_from=effective_from,
            effective_to=effective_to,
            retrieved_at=datetime.now(),
            official_url=official_url,
            content_reference=content_reference,
            byte_size=actual_size,
            mime_type=mime_type,
            supersedes_version_id=supersedes_version_id,
            status=status,
            provenance_completeness=provenance_completeness,
        )
        self.session.add(doc_ver)
        await self.session.flush()

        await self.record_audit_event(
            event_type=ProvenanceEventType.DOCUMENT_VERSION_ADDED,
            entity_type="OfficialDocumentVersion",
            entity_id=str(doc_ver.id),
            actor_id=actor_id,
            new_state={
                "version_label": version_label,
                "document_hash": actual_hash,
                "status": status.value,
                "completeness": provenance_completeness.value,
            },
            reason="Official document version materialized.",
        )

        return doc_ver

    # --------------------------------------------------------------------------
    # I-E: Policy Version <-> Document Binding
    # --------------------------------------------------------------------------

    async def bind_policy_to_document(
        self,
        policy_version_id: uuid.UUID,
        document_version_id: uuid.UUID,
        binding_type: PolicySourceBindingType = PolicySourceBindingType.PRIMARY_SOURCE,
        citation: Optional[str] = None,
        notes: Optional[str] = None,
        actor_id: Optional[str] = "SYSTEM",
    ) -> PolicySourceBinding:
        """Bind an enacted PolicyVersion to a supporting OfficialDocumentVersion."""
        pv = await self.session.get(PolicyVersion, policy_version_id)
        if not pv:
            raise ProvenanceNotFoundError(f"PolicyVersion '{policy_version_id}' not found.")

        # Load scheme to verify cross-scheme consistency
        scheme = await self.session.get(Scheme, pv.scheme_id)
        if not scheme:
            raise ProvenanceNotFoundError(f"Parent Scheme for PolicyVersion '{policy_version_id}' not found.")

        dv = await self.session.get(OfficialDocumentVersion, document_version_id)
        if not dv:
            raise ProvenanceNotFoundError(f"OfficialDocumentVersion '{document_version_id}' not found.")

        doc = await self.session.get(OfficialDocument, dv.document_id)
        if not doc:
            raise ProvenanceNotFoundError(f"Parent OfficialDocument for version '{document_version_id}' not found.")

        # Validate scheme consistency
        if doc.scheme_code != scheme.scheme_code:
            raise ProvenanceValidationError(
                f"Cross-scheme binding rejected: PolicyVersion belongs to '{scheme.scheme_code}', "
                f"but Document belongs to '{doc.scheme_code}'."
            )

        # Check existing binding
        stmt = select(PolicySourceBinding).where(
            PolicySourceBinding.policy_version_id == policy_version_id,
            PolicySourceBinding.document_version_id == document_version_id,
        )
        res = await self.session.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing:
            return existing

        binding = PolicySourceBinding(
            id=uuid.uuid4(),
            policy_version_id=policy_version_id,
            document_version_id=document_version_id,
            binding_type=binding_type,
            citation=citation,
            notes=notes,
        )
        self.session.add(binding)
        await self.session.flush()

        await self.record_audit_event(
            event_type=ProvenanceEventType.POLICY_SOURCE_BOUND,
            entity_type="PolicySourceBinding",
            entity_id=str(binding.id),
            actor_id=actor_id,
            new_state={
                "policy_version_id": str(policy_version_id),
                "document_version_id": str(document_version_id),
                "binding_type": binding_type.value,
                "citation": citation,
            },
            reason="PolicyVersion bound to supporting OfficialDocumentVersion.",
        )

        return binding

    # --------------------------------------------------------------------------
    # I-F: Rule-Level Provenance
    # --------------------------------------------------------------------------

    async def bind_rule_provenance(
        self,
        rule_id: str,
        policy_version_id: uuid.UUID,
        document_version_id: uuid.UUID,
        citation: Optional[str] = None,
        source_locator: Optional[str] = None,
        provenance_type: str = "STATUTORY_RULE",
        notes: Optional[str] = None,
        actor_id: Optional[str] = "SYSTEM",
    ) -> RuleProvenance:
        """Bind an individual AST Rule to a specific clause or section in an official document."""
        pv = await self.session.get(PolicyVersion, policy_version_id)
        if not pv:
            raise ProvenanceNotFoundError(f"PolicyVersion '{policy_version_id}' not found.")

        dv = await self.session.get(OfficialDocumentVersion, document_version_id)
        if not dv:
            raise ProvenanceNotFoundError(f"OfficialDocumentVersion '{document_version_id}' not found.")

        # Check existing rule provenance
        stmt = select(RuleProvenance).where(
            RuleProvenance.rule_id == rule_id,
            RuleProvenance.policy_version_id == policy_version_id,
            RuleProvenance.document_version_id == document_version_id,
        )
        res = await self.session.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing:
            return existing

        rule_prov = RuleProvenance(
            id=uuid.uuid4(),
            rule_id=rule_id,
            policy_version_id=policy_version_id,
            document_version_id=document_version_id,
            citation=citation,
            source_locator=source_locator,
            provenance_type=provenance_type,
            notes=notes,
        )
        self.session.add(rule_prov)
        await self.session.flush()

        await self.record_audit_event(
            event_type=ProvenanceEventType.RULE_PROVENANCE_BOUND,
            entity_type="RuleProvenance",
            entity_id=str(rule_prov.id),
            actor_id=actor_id,
            new_state={
                "rule_id": rule_id,
                "policy_version_id": str(policy_version_id),
                "document_version_id": str(document_version_id),
                "locator": source_locator,
            },
            reason="Rule bound to official document section/clause locator.",
        )

        return rule_prov

    # --------------------------------------------------------------------------
    # I-G: Query & Navigation APIs
    # --------------------------------------------------------------------------

    async def get_scheme_provenance(self, scheme_code: str) -> Dict[str, Any]:
        """Navigate full statutory provenance for a scheme."""
        normalized = scheme_code.strip().upper()
        stmt = (
            select(Scheme)
            .where(Scheme.scheme_code == normalized)
            .options(
                selectinload(Scheme.policy_versions).selectinload(PolicyVersion.source_bindings).selectinload(PolicySourceBinding.document_version).selectinload(OfficialDocumentVersion.document).selectinload(OfficialDocument.official_source),
                selectinload(Scheme.policy_versions).selectinload(PolicyVersion.rule_provenances),
            )
        )
        res = await self.session.execute(stmt)
        scheme = res.scalar_one_or_none()
        if not scheme:
            raise ProvenanceNotFoundError(f"Scheme '{scheme_code}' not found.")

        # Query official sources
        src_stmt = select(OfficialSource).where(
            (OfficialSource.scheme_code == normalized) | (OfficialSource.scheme_code.is_(None))
        )
        src_res = await self.session.execute(src_stmt)
        sources = src_res.scalars().all()

        # Query official documents
        doc_stmt = (
            select(OfficialDocument)
            .where(OfficialDocument.scheme_code == normalized)
            .options(
                selectinload(OfficialDocument.versions),
                selectinload(OfficialDocument.official_source),
            )
        )
        doc_res = await self.session.execute(doc_stmt)
        docs = doc_res.scalars().all()

        policy_summaries = []
        for pv in scheme.policy_versions:
            bound_docs = [
                {
                    "document_title": b.document_version.document.document_title,
                    "version_label": b.document_version.version_label,
                    "reference_number": b.document_version.document.reference_number,
                    "official_url": b.document_version.official_url,
                    "binding_type": b.binding_type.value,
                    "citation": b.citation,
                    "document_hash": b.document_version.document_hash,
                    "hash_algorithm": b.document_version.hash_algorithm,
                    "completeness": b.document_version.provenance_completeness.value,
                }
                for b in pv.source_bindings
            ]
            policy_summaries.append({
                "policy_version_id": str(pv.id),
                "version_code": pv.version_code,
                "effective_from": pv.effective_from.isoformat(),
                "effective_to": pv.effective_to.isoformat() if pv.effective_to else None,
                "canonical_rule_hash": pv.rule_definition_hash,
                "source_title": pv.source_title,
                "source_url": pv.source_url,
                "bound_documents": bound_docs,
                "rule_provenance_count": len(pv.rule_provenances),
            })

        return {
            "scheme_code": scheme.scheme_code,
            "scheme_name_en": scheme.name_en,
            "scheme_name_hi": scheme.name_hi,
            "ministry": scheme.ministry,
            "official_url": scheme.official_url,
            "sources": [
                {
                    "id": str(s.id),
                    "publisher_name": s.publisher_name,
                    "publisher_type": s.publisher_type.value,
                    "official_domain": s.official_domain,
                    "canonical_url": s.canonical_url,
                }
                for s in sources
            ],
            "documents": [
                {
                    "id": str(d.id),
                    "document_title": d.document_title,
                    "document_type": d.document_type.value,
                    "issuing_authority": d.issuing_authority,
                    "reference_number": d.reference_number,
                    "official_url": d.official_url,
                    "versions": [
                        {
                            "id": str(v.id),
                            "version_label": v.version_label,
                            "document_hash": v.document_hash,
                            "hash_algorithm": v.hash_algorithm,
                            "status": v.status.value,
                            "completeness": v.provenance_completeness.value,
                            "content_reference": sanitize_content_reference(v.content_reference),
                            "byte_size": v.byte_size,
                        }
                        for v in d.versions
                    ],
                }
                for d in docs
            ],
            "policy_versions": policy_summaries,
        }

    async def get_policy_provenance(self, policy_version_id: uuid.UUID) -> Dict[str, Any]:
        """Navigate full provenance for a specific policy version."""
        stmt = (
            select(PolicyVersion)
            .where(PolicyVersion.id == policy_version_id)
            .options(
                selectinload(PolicyVersion.scheme),
                selectinload(PolicyVersion.rule_set),
                selectinload(PolicyVersion.source_bindings).selectinload(PolicySourceBinding.document_version).selectinload(OfficialDocumentVersion.document).selectinload(OfficialDocument.official_source),
                selectinload(PolicyVersion.rule_provenances).selectinload(RuleProvenance.document_version).selectinload(OfficialDocumentVersion.document),
            )
        )
        res = await self.session.execute(stmt)
        pv = res.scalar_one_or_none()
        if not pv:
            raise ProvenanceNotFoundError(f"PolicyVersion '{policy_version_id}' not found.")

        bound_docs = []
        for b in pv.source_bindings:
            dv = b.document_version
            doc = dv.document
            src = doc.official_source
            bound_docs.append({
                "binding_id": str(b.id),
                "binding_type": b.binding_type.value,
                "citation": b.citation,
                "notes": b.notes,
                "document": {
                    "id": str(doc.id),
                    "title": doc.document_title,
                    "type": doc.document_type.value,
                    "issuing_authority": doc.issuing_authority,
                    "reference_number": doc.reference_number,
                    "official_url": doc.official_url,
                },
                "version": {
                    "id": str(dv.id),
                    "version_label": dv.version_label,
                    "document_hash": dv.document_hash,
                    "hash_algorithm": dv.hash_algorithm,
                    "published_at": dv.published_at.isoformat() if dv.published_at else None,
                    "status": dv.status.value,
                    "completeness": dv.provenance_completeness.value,
                    "content_reference": sanitize_content_reference(dv.content_reference),
                    "byte_size": dv.byte_size,
                },
                "source": {
                    "publisher_name": src.publisher_name,
                    "publisher_type": src.publisher_type.value,
                    "domain": src.official_domain,
                    "canonical_url": src.canonical_url,
                },
            })

        rule_prov_list = [
            {
                "rule_id": rp.rule_id,
                "source_locator": rp.source_locator,
                "citation": rp.citation,
                "provenance_type": rp.provenance_type,
                "document_title": rp.document_version.document.document_title,
                "version_label": rp.document_version.version_label,
                "official_url": rp.document_version.official_url,
            }
            for rp in pv.rule_provenances
        ]

        return {
            "policy_version_id": str(pv.id),
            "scheme_code": pv.scheme.scheme_code,
            "scheme_name": pv.scheme.name_en,
            "version_code": pv.version_code,
            "effective_from": pv.effective_from.isoformat(),
            "effective_to": pv.effective_to.isoformat() if pv.effective_to else None,
            "ruleset_hash": pv.rule_definition_hash,
            "source_title": pv.source_title,
            "source_url": pv.source_url,
            "bound_documents": bound_docs,
            "rule_provenances": rule_prov_list,
        }

    async def get_rule_provenance(
        self, policy_version_id: uuid.UUID, rule_id: str
    ) -> Dict[str, Any]:
        """Navigate trace for a specific individual rule to its official source document and clause."""
        stmt = (
            select(RuleProvenance)
            .where(
                RuleProvenance.policy_version_id == policy_version_id,
                RuleProvenance.rule_id == rule_id,
            )
            .options(
                selectinload(RuleProvenance.policy_version).selectinload(PolicyVersion.scheme),
                selectinload(RuleProvenance.document_version).selectinload(OfficialDocumentVersion.document).selectinload(OfficialDocument.official_source),
            )
        )
        res = await self.session.execute(stmt)
        rp = res.scalar_one_or_none()

        if not rp:
            raise ProvenanceNotFoundError(
                f"Rule provenance for rule '{rule_id}' in PolicyVersion '{policy_version_id}' not found."
            )

        pv = rp.policy_version
        dv = rp.document_version
        doc = dv.document
        src = doc.official_source

        return {
            "rule_id": rp.rule_id,
            "source_locator": rp.source_locator,
            "citation": rp.citation,
            "provenance_type": rp.provenance_type,
            "notes": rp.notes,
            "policy_version": {
                "id": str(pv.id),
                "version_code": pv.version_code,
                "ruleset_hash": pv.rule_definition_hash,
                "scheme_code": pv.scheme.scheme_code,
            },
            "document": {
                "id": str(doc.id),
                "title": doc.document_title,
                "reference_number": doc.reference_number,
                "issuing_authority": doc.issuing_authority,
                "type": doc.document_type.value,
                "version_label": dv.version_label,
                "document_hash": dv.document_hash,
                "hash_algorithm": dv.hash_algorithm,
                "official_url": dv.official_url,
                "completeness": dv.provenance_completeness.value,
            },
            "official_source": {
                "publisher_name": src.publisher_name,
                "publisher_type": src.publisher_type.value,
                "official_domain": src.official_domain,
                "canonical_url": src.canonical_url,
            },
        }

    async def get_provenance_audit_trail(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Retrieve chronological immutable audit trail records."""
        stmt = select(ProvenanceAuditEvent).order_by(desc(ProvenanceAuditEvent.created_at)).limit(limit)
        if entity_type:
            stmt = stmt.where(ProvenanceAuditEvent.entity_type == entity_type)
        if entity_id:
            stmt = stmt.where(ProvenanceAuditEvent.entity_id == entity_id)

        res = await self.session.execute(stmt)
        events = res.scalars().all()

        return [
            {
                "id": str(e.id),
                "event_type": e.event_type.value,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "actor_id": e.actor_id,
                "actor_role": e.actor_role,
                "previous_state": e.previous_state,
                "new_state": e.new_state,
                "reason": e.reason,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ]
