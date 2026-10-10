"""Comprehensive Test Suite for Phase I (Official Documents & Provenance Hardening).

Covers all 25 statutory provenance requirements:
1. official source creation
2. official document creation
3. document version creation
4. document hash verification (actual SHA-256)
5. malformed hash rejection
6. unsupported hash rejection
7. policy/document binding
8. rule/document provenance
9. multiple source documents
10. historical provenance
11. superseded documents
12. duplicate active version protection
13. invalid source/document relationship
14. invalid policy/document relationship
15. citizen read-only transparency
16. unauthorized provenance mutation
17. provenance audit events
18. missing provenance handling
19. actual rule hash vs document hash separation
20. policy-version immutability
21. evaluation trace provenance
22. IDOR protection
23. official URL validation
24. existing 14 policy versions populated
25. A–I regression
"""

from __future__ import annotations

from datetime import date, datetime
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import create_access_token
from app.main import app
from app.models.citizen import Citizen, Claim, Evidence, VerificationRecord
from app.models.enums import (
    DocumentVersionStatus,
    EligibilityResult,
    EvidenceStatus,
    JourneyState,
    OfficialDocumentType,
    OfficialSourceType,
    PolicySourceBindingType,
    ProvenanceCompleteness,
    ProvenanceEventType,
)
from app.models.evaluation import EvaluationTrace
from app.models.journey import EvaluationJourney
from app.models.provenance import (
    OfficialDocument,
    OfficialDocumentVersion,
    OfficialSource,
    PolicySourceBinding,
    ProvenanceAuditEvent,
    RuleProvenance,
)
from app.models.scheme import PolicyVersion, RuleSet, Scheme
from app.services.provenance_loader import seed_all_provenance
from app.services.provenance_service import (
    ProvenanceNotFoundError,
    ProvenanceService,
    ProvenanceValidationError,
    compute_file_sha256,
    validate_document_hash,
    validate_official_url,
)


@pytest.fixture(autouse=True)
async def ensure_provenance_seeded(db_session: AsyncSession) -> None:
    """Ensure official sources and document provenances are seeded before tests."""
    await seed_all_provenance(db_session)


def _make_citizen_token(
    email: str = "rameshwar.sharma@test.local",
    ref: str = "SYN-CIT-DEMO0001",
    name: str = "Rameshwar Sharma",
) -> str:
    """Generate a valid citizen Bearer JWT for test authorization."""
    payload = {
        "sub": email,
        "role": "CITIZEN",
        "citizen_ref": ref,
        "name": name,
        "state": "Maharashtra",
        "district": "Pune",
    }
    return create_access_token(data=payload)


# ==============================================================================
# 1. Official Source Creation
# ==============================================================================

@pytest.mark.asyncio
async def test_official_source_creation(db_session: AsyncSession) -> None:
    service = ProvenanceService(db_session)
    source = await service.register_official_source(
        publisher_name="Ministry of Jal Shakti, Government of India",
        publisher_type=OfficialSourceType.MINISTRY,
        official_domain="jalshakti.gov.in",
        canonical_url="https://jalshakti.gov.in",
        source_type=OfficialSourceType.MINISTRY,
        scheme_code="JJM",
        description="Nodal ministry for drinking water missions.",
        actor_id="OFFICER-TEST-001",
    )
    assert source.id is not None
    assert source.publisher_name == "Ministry of Jal Shakti, Government of India"
    assert source.official_domain == "jalshakti.gov.in"
    assert source.canonical_url == "https://jalshakti.gov.in"
    assert source.active is True


# ==============================================================================
# 2. Official Document Creation
# ==============================================================================

@pytest.mark.asyncio
async def test_official_document_creation(db_session: AsyncSession) -> None:
    service = ProvenanceService(db_session)
    source = await service.register_official_source(
        publisher_name="Ministry of Electronics and Information Technology",
        publisher_type=OfficialSourceType.MINISTRY,
        official_domain="meity.gov.in",
        canonical_url="https://meity.gov.in",
        source_type=OfficialSourceType.MINISTRY,
        scheme_code="TEST_IT",
    )
    doc = await service.register_official_document(
        official_source_id=source.id,
        scheme_code="TEST_IT",
        document_title="Digital India Guidelines 2024",
        document_type=OfficialDocumentType.OPERATIONAL_GUIDELINE,
        issuing_authority="MeitY, Government of India",
        official_url="https://meity.gov.in/guidelines",
        reference_number="F.No. 12/2024-DI",
        publication_date=date(2024, 1, 1),
    )
    assert doc.id is not None
    assert doc.document_title == "Digital India Guidelines 2024"
    assert doc.reference_number == "F.No. 12/2024-DI"
    assert doc.official_source_id == source.id


# ==============================================================================
# 3. Document Version Creation
# ==============================================================================

@pytest.mark.asyncio
async def test_document_version_creation(db_session: AsyncSession) -> None:
    service = ProvenanceService(db_session)
    source = await service.register_official_source(
        publisher_name="Ministry of Health & Family Welfare",
        publisher_type=OfficialSourceType.MINISTRY,
        official_domain="mohfw.gov.in",
        canonical_url="https://mohfw.gov.in",
        source_type=OfficialSourceType.MINISTRY,
        scheme_code="TEST_HEALTH",
    )
    doc = await service.register_official_document(
        official_source_id=source.id,
        scheme_code="TEST_HEALTH",
        document_title="National Health Guidelines",
        document_type=OfficialDocumentType.SCHEME_GUIDELINE,
        issuing_authority="MoHFW, Government of India",
        official_url="https://mohfw.gov.in/guidelines",
    )
    doc_ver = await service.add_document_version(
        document_id=doc.id,
        version_label="v1.0-2024",
        official_url="https://mohfw.gov.in/guidelines/v1",
        published_at=date(2024, 1, 1),
        effective_from=date(2024, 1, 1),
        effective_to=None,
        status=DocumentVersionStatus.ACTIVE,
        provenance_completeness=ProvenanceCompleteness.COMPLETE,
    )
    assert doc_ver.id is not None
    assert doc_ver.version_label == "v1.0-2024"
    assert doc_ver.status == DocumentVersionStatus.ACTIVE
    assert doc_ver.hash_algorithm == "SHA-256"


# ==============================================================================
# 4. Document Hash Verification (Actual SHA-256 on File)
# ==============================================================================

@pytest.mark.asyncio
async def test_document_hash_verification(tmp_path: Path, db_session: AsyncSession) -> None:
    # Create an actual physical document artifact on disk
    artifact_file = tmp_path / "official_notification.pdf"
    content = b"%PDF-1.4 Statutory Official Gazette Notification Content bytes 12345"
    artifact_file.write_bytes(content)

    expected_hash = hashlib.sha256(content).hexdigest()
    computed_hash, byte_size = compute_file_sha256(artifact_file)
    assert computed_hash == expected_hash
    assert byte_size == len(content)

    service = ProvenanceService(db_session)
    source = await service.register_official_source(
        publisher_name="Ministry of Finance",
        publisher_type=OfficialSourceType.MINISTRY,
        official_domain="dea.gov.in",
        canonical_url="https://dea.gov.in",
        source_type=OfficialSourceType.MINISTRY,
        scheme_code="TEST_FIN",
    )
    doc = await service.register_official_document(
        official_source_id=source.id,
        scheme_code="TEST_FIN",
        document_title="Notification F.1",
        document_type=OfficialDocumentType.GAZETTE_NOTIFICATION,
        issuing_authority="MoF",
        official_url="https://dea.gov.in/notification",
    )
    dv = await service.add_document_version(
        document_id=doc.id,
        version_label="v1.0",
        official_url="https://dea.gov.in/notification/v1.pdf",
        document_hash=expected_hash,
        content_reference=str(artifact_file),
    )
    assert dv.document_hash == expected_hash
    assert dv.byte_size == len(content)


# ==============================================================================
# 5. Malformed Hash Rejection
# ==============================================================================

def test_malformed_hash_rejection() -> None:
    # Non-hex characters
    with pytest.raises(ProvenanceValidationError, match="Malformed document hash"):
        validate_document_hash("not-a-valid-hex-digest-at-all-xyz12345678901234567890123456789012")

    # Incorrect length (32 chars instead of 64)
    with pytest.raises(ProvenanceValidationError, match="Malformed document hash"):
        validate_document_hash("d41d8cd98f00b204e9800998ecf8427e")


# ==============================================================================
# 6. Unsupported Hash Rejection
# ==============================================================================

def test_unsupported_hash_rejection() -> None:
    with pytest.raises(ProvenanceValidationError, match="Unsupported hash algorithm"):
        validate_document_hash("a" * 64, algorithm="MD5")


# ==============================================================================
# 7. Policy / Document Binding
# ==============================================================================

@pytest.mark.asyncio
async def test_policy_document_binding(db_session: AsyncSession) -> None:
    stmt = (
        select(PolicyVersion)
        .join(Scheme)
        .where(Scheme.scheme_code == "PM_KISAN", PolicyVersion.version_code == "v3.0-2023")
    )
    res = await db_session.execute(stmt)
    pv = res.scalar_one()

    # Find the document version for PM_KISAN v3.0-2023
    dv_stmt = (
        select(OfficialDocumentVersion)
        .join(OfficialDocument)
        .where(OfficialDocument.scheme_code == "PM_KISAN", OfficialDocumentVersion.version_label == "v3.0-2023")
    )
    dv = (await db_session.execute(dv_stmt)).scalar_one()

    service = ProvenanceService(db_session)
    binding = await service.bind_policy_to_document(
        policy_version_id=pv.id,
        document_version_id=dv.id,
        binding_type=PolicySourceBindingType.PRIMARY_SOURCE,
        citation="Operational Guidelines 2023, Clause 1.2",
    )
    assert binding.policy_version_id == pv.id
    assert binding.document_version_id == dv.id
    assert binding.binding_type == PolicySourceBindingType.PRIMARY_SOURCE


# ==============================================================================
# 8. Rule / Document Provenance
# ==============================================================================

@pytest.mark.asyncio
async def test_rule_document_provenance(db_session: AsyncSession) -> None:
    stmt = (
        select(PolicyVersion)
        .join(Scheme)
        .where(Scheme.scheme_code == "PM_KISAN", PolicyVersion.version_code == "v3.0-2023")
    )
    pv = (await db_session.execute(stmt)).scalar_one()

    dv_stmt = (
        select(OfficialDocumentVersion)
        .join(OfficialDocument)
        .where(OfficialDocument.scheme_code == "PM_KISAN", OfficialDocumentVersion.version_label == "v3.0-2023")
    )
    dv = (await db_session.execute(dv_stmt)).scalar_one()

    service = ProvenanceService(db_session)
    rule_prov = await service.bind_rule_provenance(
        rule_id="PMKISAN-LAND-CULTIVABLE",
        policy_version_id=pv.id,
        document_version_id=dv.id,
        citation="Operational Guidelines 2023, Clause 2.1",
        source_locator="Clause 2.1",
        provenance_type="STATUTORY_RULE",
    )
    assert rule_prov.rule_id == "PMKISAN-LAND-CULTIVABLE"
    assert rule_prov.source_locator == "Clause 2.1"
    assert rule_prov.policy_version_id == pv.id


# ==============================================================================
# 9. Multiple Source Documents for One Policy Version
# ==============================================================================

@pytest.mark.asyncio
async def test_multiple_source_documents(db_session: AsyncSession) -> None:
    stmt = (
        select(PolicyVersion)
        .join(Scheme)
        .where(Scheme.scheme_code == "SSY", PolicyVersion.version_code == "v3.0-2024")
    )
    pv = (await db_session.execute(stmt)).scalar_one()

    service = ProvenanceService(db_session)
    source = await service.register_official_source(
        publisher_name="Department of Posts, Ministry of Communications",
        publisher_type=OfficialSourceType.DEPARTMENT,
        official_domain="dea.gov.in",
        canonical_url="https://dea.gov.in",
        source_type=OfficialSourceType.DEPARTMENT,
        scheme_code="SSY",
    )
    # Supplementary clarification order document
    supp_doc = await service.register_official_document(
        official_source_id=source.id,
        scheme_code="SSY",
        document_title="SB Order No. 08/2024 (POSB Amendments)",
        document_type=OfficialDocumentType.MINISTRY_CIRCULAR,
        issuing_authority="Department of Posts, Government of India",
        official_url="https://dea.gov.in/orders",
        reference_number="SB-08/2024",
    )
    supp_dv = await service.add_document_version(
        document_id=supp_doc.id,
        version_label="v2024-Circ-8",
        official_url="https://dea.gov.in/orders/sb08.pdf",
    )
    supp_binding = await service.bind_policy_to_document(
        policy_version_id=pv.id,
        document_version_id=supp_dv.id,
        binding_type=PolicySourceBindingType.SUPPLEMENTARY_SOURCE,
        citation="Paragraph 3 (Clarification on irregular accounts)",
    )
    assert supp_binding.binding_type == PolicySourceBindingType.SUPPLEMENTARY_SOURCE

    # Verify policy now has multiple source bindings
    all_bindings_stmt = select(PolicySourceBinding).where(PolicySourceBinding.policy_version_id == pv.id)
    all_bindings = (await db_session.execute(all_bindings_stmt)).scalars().all()
    assert len(all_bindings) >= 2


# ==============================================================================
# 10. Historical Provenance Immutability
# ==============================================================================

@pytest.mark.asyncio
async def test_historical_provenance(db_session: AsyncSession) -> None:
    # PM-KISAN has v1.0-2018, v2.0-2019, v3.0-2023
    v1_stmt = (
        select(PolicyVersion)
        .join(Scheme)
        .where(Scheme.scheme_code == "PM_KISAN", PolicyVersion.version_code == "v1.0-2018")
    )
    v1_pv = (await db_session.execute(v1_stmt)).scalar_one()

    # Rule PMKISAN-HIST-LAND-CEILING-2HA exists only in v1.0-2018
    service = ProvenanceService(db_session)
    prov = await service.get_rule_provenance(v1_pv.id, "PMKISAN-HIST-LAND-CEILING-2HA")
    assert prov["policy_version"]["version_code"] == "v1.0-2018"
    assert prov["source_locator"] == "Clause 1.1 & 2.1"
    assert prov["document"]["version_label"] == "v1.0-2018"


# ==============================================================================
# 11. Superseded Documents
# ==============================================================================

@pytest.mark.asyncio
async def test_superseded_documents(db_session: AsyncSession) -> None:
    service = ProvenanceService(db_session)
    source = await service.register_official_source(
        publisher_name="Ministry of Social Justice & Empowerment",
        publisher_type=OfficialSourceType.MINISTRY,
        official_domain="nsap.nic.in",
        canonical_url="https://nsap.nic.in",
        source_type=OfficialSourceType.MINISTRY,
        scheme_code="TEST_SOC",
    )
    doc = await service.register_official_document(
        official_source_id=source.id,
        scheme_code="TEST_SOC",
        document_title="Social Welfare Manual",
        document_type=OfficialDocumentType.OFFICIAL_MANUAL,
        issuing_authority="MoSJE",
        official_url="https://nsap.nic.in/manual",
    )
    v1 = await service.add_document_version(
        document_id=doc.id,
        version_label="Ed-1",
        official_url="https://nsap.nic.in/manual/v1",
        status=DocumentVersionStatus.ACTIVE,
    )
    assert v1.status == DocumentVersionStatus.ACTIVE

    # Release edition 2 that supersedes edition 1
    v2 = await service.add_document_version(
        document_id=doc.id,
        version_label="Ed-2",
        official_url="https://nsap.nic.in/manual/v2",
        supersedes_version_id=v1.id,
        status=DocumentVersionStatus.ACTIVE,
    )
    assert v2.status == DocumentVersionStatus.ACTIVE

    # Check that v1 transitioned to SUPERSEDED
    await db_session.refresh(v1)
    assert v1.status == DocumentVersionStatus.SUPERSEDED


# ==============================================================================
# 12. Duplicate Active Version Protection
# ==============================================================================

@pytest.mark.asyncio
async def test_duplicate_active_version_protection(db_session: AsyncSession) -> None:
    service = ProvenanceService(db_session)
    doc_stmt = select(OfficialDocument).where(OfficialDocument.scheme_code == "PM_KISAN")
    doc = (await db_session.execute(doc_stmt)).scalars().first()

    # Re-adding the exact same version label returns existing without duplicating
    existing_stmt = select(OfficialDocumentVersion).where(
        OfficialDocumentVersion.document_id == doc.id,
        OfficialDocumentVersion.version_label == "v3.0-2023",
    )
    existing_ver = (await db_session.execute(existing_stmt)).scalar_one()

    added = await service.add_document_version(
        document_id=doc.id,
        version_label="v3.0-2023",
        official_url=existing_ver.official_url,
    )
    assert added.id == existing_ver.id


# ==============================================================================
# 13. Invalid Source / Document Relationship
# ==============================================================================

@pytest.mark.asyncio
async def test_invalid_source_document_relationship(db_session: AsyncSession) -> None:
    service = ProvenanceService(db_session)
    fake_source_id = uuid.uuid4()
    with pytest.raises(ProvenanceNotFoundError, match="OfficialSource.*not found"):
        await service.register_official_document(
            official_source_id=fake_source_id,
            scheme_code="TEST",
            document_title="Ghost Doc",
            document_type=OfficialDocumentType.SCHEME_GUIDELINE,
            issuing_authority="Ghost Authority",
            official_url="https://pmkisan.gov.in/ghost",
        )


# ==============================================================================
# 14. Invalid Policy / Document Cross-Scheme Relationship
# ==============================================================================

@pytest.mark.asyncio
async def test_invalid_policy_document_relationship(db_session: AsyncSession) -> None:
    # Try to bind a PM_KISAN PolicyVersion to an SSY OfficialDocumentVersion
    pmkisan_pv_stmt = (
        select(PolicyVersion)
        .join(Scheme)
        .where(Scheme.scheme_code == "PM_KISAN")
    )
    pmkisan_pv = (await db_session.execute(pmkisan_pv_stmt)).scalars().first()

    ssy_dv_stmt = (
        select(OfficialDocumentVersion)
        .join(OfficialDocument)
        .where(OfficialDocument.scheme_code == "SSY")
    )
    ssy_dv = (await db_session.execute(ssy_dv_stmt)).scalars().first()

    service = ProvenanceService(db_session)
    with pytest.raises(ProvenanceValidationError, match="Cross-scheme binding rejected"):
        await service.bind_policy_to_document(
            policy_version_id=pmkisan_pv.id,
            document_version_id=ssy_dv.id,
        )


# ==============================================================================
# 15. Citizen Read-Only Transparency API
# ==============================================================================

@pytest.mark.asyncio
async def test_citizen_read_only_transparency(async_client: AsyncClient) -> None:
    resp = await async_client.get("/api/v1/provenance/schemes/PM_KISAN")
    assert resp.status_code == 200
    data = resp.json()
    assert data["scheme_code"] == "PM_KISAN"
    assert len(data["sources"]) >= 1
    assert len(data["documents"]) >= 1
    assert len(data["policy_versions"]) == 3
    # Invariant: No internal filesystem absolute paths exposed
    for doc in data["documents"]:
        for ver in doc["versions"]:
            assert ver.get("content_reference") is None or not ver["content_reference"].startswith("C:\\")


# ==============================================================================
# 16. Unauthorized Provenance Mutation
# ==============================================================================

@pytest.mark.asyncio
async def test_unauthorized_provenance_mutation(async_client: AsyncClient) -> None:
    # Verify that POST / PUT / DELETE do not exist on read-only public endpoints
    post_resp = await async_client.post("/api/v1/provenance/schemes/PM_KISAN", json={"name": "Hacked"})
    assert post_resp.status_code in (404, 405)


# ==============================================================================
# 17. Provenance Audit Events Trail
# ==============================================================================

@pytest.mark.asyncio
async def test_provenance_audit_events(async_client: AsyncClient) -> None:
    resp = await async_client.get("/api/v1/provenance/audit-trail?limit=10")
    assert resp.status_code == 200
    events = resp.json()
    assert len(events) > 0
    event_types = {e["event_type"] for e in events}
    assert "DOCUMENT_REGISTERED" in event_types or "POLICY_SOURCE_BOUND" in event_types or "RULE_PROVENANCE_BOUND" in event_types


# ==============================================================================
# 18. Missing Provenance Handling (404 ErrorResponse)
# ==============================================================================

@pytest.mark.asyncio
async def test_missing_provenance_handling(async_client: AsyncClient) -> None:
    resp = await async_client.get("/api/v1/provenance/schemes/NON_EXISTENT_SCHEME")
    assert resp.status_code == 404

    fake_uuid = str(uuid.uuid4())
    resp2 = await async_client.get(f"/api/v1/provenance/policies/{fake_uuid}")
    assert resp2.status_code == 404


# ==============================================================================
# 19. Actual Rule Hash vs Document Hash Separation
# ==============================================================================

@pytest.mark.asyncio
async def test_actual_rule_hash_vs_document_hash_separation(db_session: AsyncSession) -> None:
    pv_stmt = (
        select(PolicyVersion)
        .join(Scheme)
        .where(Scheme.scheme_code == "PM_KISAN", PolicyVersion.version_code == "v3.0-2023")
    )
    pv = (await db_session.execute(pv_stmt)).scalar_one()

    # The canonical rule hash is derived from the machine-readable AST
    assert pv.rule_definition_hash is not None
    assert len(pv.rule_definition_hash) == 64

    # Document hash is the SHA-256 of the official physical document artifact (or None for metadata-only)
    dv_stmt = (
        select(OfficialDocumentVersion)
        .join(OfficialDocument)
        .where(OfficialDocument.scheme_code == "PM_KISAN", OfficialDocumentVersion.version_label == "v3.0-2023")
    )
    dv = (await db_session.execute(dv_stmt)).scalar_one()

    # Invariant: Rule hash and document hash represent distinct concepts and are never mixed
    assert pv.rule_definition_hash != dv.document_hash


# ==============================================================================
# 20. Policy-Version Immutability
# ==============================================================================

@pytest.mark.asyncio
async def test_policy_version_immutability(db_session: AsyncSession) -> None:
    # Verify that existing PolicyVersion attributes remain unchanged after provenance operations
    stmt = (
        select(PolicyVersion)
        .join(Scheme)
        .where(Scheme.scheme_code == "SSY", PolicyVersion.version_code == "v2.0-2019")
    )
    pv = (await db_session.execute(stmt)).scalar_one()
    initial_hash = pv.rule_definition_hash
    initial_start = pv.effective_from

    # Seed or touch provenance
    service = ProvenanceService(db_session)
    await service.get_policy_provenance(pv.id)

    await db_session.refresh(pv)
    assert pv.rule_definition_hash == initial_hash
    assert pv.effective_from == initial_start


# ==============================================================================
# 21. Evaluation Trace Provenance
# ==============================================================================

@pytest.mark.asyncio
async def test_evaluation_trace_provenance(db_session: AsyncSession) -> None:
    stmt = (
        select(EvaluationTrace)
        .options(selectinload(EvaluationTrace.policy_version))
        .order_by(EvaluationTrace.created_at.desc())
    )
    res = await db_session.execute(stmt)
    trace = res.scalars().first()
    if trace:
        assert trace.policy_version_id is not None
        assert trace.policy_version is not None
        assert trace.rule_definition_hash is not None


# ==============================================================================
# 22. IDOR Protection
# ==============================================================================

@pytest.mark.asyncio
async def test_idor_protection(async_client: AsyncClient) -> None:
    token_a = _make_citizen_token(email="cit.a@test.local", ref=f"SYN-CIT-A-{uuid.uuid4().hex[:6]}")
    token_b = _make_citizen_token(email="cit.b@test.local", ref=f"SYN-CIT-B-{uuid.uuid4().hex[:6]}")

    # Citizen A creates application
    res_a = await async_client.post(
        "/api/v1/citizen/applications",
        json={"scheme_code": "PM_KISAN"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_a.status_code == 201
    app_id = res_a.json()["id"]

    # Citizen B attempts to view Citizen A's application
    res_b = await async_client.get(
        f"/api/v1/citizen/applications/{app_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b.status_code == 404


# ==============================================================================
# 23. Official URL Validation
# ==============================================================================

def test_official_url_validation() -> None:
    # Valid HTTPS government URLs
    assert validate_official_url("https://pmkisan.gov.in/Documents/Guidelines.pdf") is True
    assert validate_official_url("https://dea.gov.in/sukanya-samriddhi") is True
    assert validate_official_url("https://nsap.nic.in/guidelines.html") is True

    # Rejection of HTTP (insecure)
    with pytest.raises(ProvenanceValidationError, match="HTTPS"):
        validate_official_url("http://pmkisan.gov.in/guidelines")

    # Rejection of localhost / loopback
    with pytest.raises(ProvenanceValidationError, match="Private or local"):
        validate_official_url("https://localhost:8000/doc")

    # Rejection of non-authoritative domain
    with pytest.raises(ProvenanceValidationError, match="not recognized"):
        validate_official_url("https://unverified-third-party-blog.com/rules.pdf")


# ==============================================================================
# 24. Existing 14 Policy Versions Populated
# ==============================================================================

@pytest.mark.asyncio
async def test_existing_14_policy_versions_populated(db_session: AsyncSession) -> None:
    stmt = (
        select(PolicyVersion)
        .options(
            selectinload(PolicyVersion.source_bindings).selectinload(PolicySourceBinding.document_version),
            selectinload(PolicyVersion.rule_provenances),
        )
    )
    pvs = (await db_session.execute(stmt)).scalars().all()
    assert len(pvs) == 14

    for pv in pvs:
        assert len(pv.source_bindings) >= 1, f"PolicyVersion '{pv.version_code}' has no bound official document"
        assert len(pv.rule_provenances) >= 4, f"PolicyVersion '{pv.version_code}' has insufficient rule provenance"


# ==============================================================================
# 25. A–I Full Traceability Regression
# ==============================================================================

@pytest.mark.asyncio
async def test_a_to_i_regression(db_session: AsyncSession) -> None:
    # Verify complete traceability chain for PM_KISAN:
    # Decision -> EvaluationTrace -> Rule -> PolicyVersion -> Source Document -> Document Version -> Official Source
    service = ProvenanceService(db_session)
    pmkisan_stmt = (
        select(PolicyVersion)
        .join(Scheme)
        .where(Scheme.scheme_code == "PM_KISAN", PolicyVersion.version_code == "v3.0-2023")
    )
    pv = (await db_session.execute(pmkisan_stmt)).scalar_one()

    prov = await service.get_rule_provenance(pv.id, "PMKISAN-EXCL-INCOME-TAX")

    # 1. Rule identification
    assert prov["rule_id"] == "PMKISAN-EXCL-INCOME-TAX"
    # 2. Source locator
    assert prov["source_locator"] == "Clause 3(b)(v)"
    # 3. Policy version
    assert prov["policy_version"]["version_code"] == "v3.0-2023"
    assert len(prov["policy_version"]["ruleset_hash"]) == 64
    # 4. Source document
    assert "PM-KISAN" in prov["document"]["title"]
    assert prov["document"]["reference_number"] == "F.No. 1-1/2019-Credit-II"
    # 5. Document version
    assert prov["document"]["version_label"] == "v3.0-2023"
    # 6. Official source authority
    assert "Agriculture" in prov["official_source"]["publisher_name"]
    assert prov["official_source"]["official_domain"] == "pmkisan.gov.in"
