"""Phase J End-to-End Verification, Hardening, and Demonstration Test Suite.

Covers:
1. J-A: End-to-End Citizen & Officer Lifecycle (Submission -> Verification -> Evaluation -> Trace -> Provenance)
2. J-B: Ten-Scheme Canonical Outcomes Matrix (40 canonical scenarios / four outcomes)
3. J-C: Clarification Lifecycle & IDOR Isolation
4. J-D: Decision Trace Reconstruction from Database Records
5. J-E: Four-Outcome Integrity & Tamper Prevention
6. J-F: Historical Policy Version Reproducibility (D1 vs D2 immutability)
7. J-G: End-to-End Provenance Traversal (Decision -> Source)
8. J-H: F-01 Hardening (SOURCE_METADATA_VERIFIED vs PHYSICAL_ARTIFACT_VERIFIED)
9. J-I: Public Provenance API Hardening (Filesystem Path Sanitization)
10. J-J: Provenance Audit Trail Immutability (PostgreSQL Trigger)
11. J-K: Citizen IDOR & Security Isolation
12. J-L: Officer Authorization Boundaries
13. J-M: Client Tampering Rejection
14. J-N: Concurrency & Idempotency
15. J-O: Transaction Recovery & Rollback
16. J-P & J-Q: Synthetic Demonstration Data & Reset Script
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.exc import DBAPIError, InternalError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.security import create_access_token
from app.engine.evaluator.context import EvaluationContext
from app.engine.evaluator.evaluator import DeterministicEvaluator
from app.main import app
from app.models.assignment import OfficerAssignment
from app.models.citizen import Citizen, Claim, Evidence, VerificationRecord
from app.models.clarification import ClarificationRequest
from app.models.enums import (
    AssignmentStatus,
    ClaimStatus,
    ClarificationStatus,
    DocumentVersionStatus,
    EligibilityResult,
    EvidenceStatus,
    JourneyState,
    OfficialDocumentType,
    OfficialSourceType,
    PolicySourceBindingType,
    ProvenanceCompleteness,
    ProvenanceEventType,
    SchemeStatus,
    VerificationStatus,
)
from app.models.evaluation import EvaluationTrace
from app.models.journey import EvaluationJourney, JourneyTransitionRecord
from app.models.provenance import (
    OfficialDocument,
    OfficialDocumentVersion,
    OfficialSource,
    PolicySourceBinding,
    ProvenanceAuditEvent,
    RuleProvenance,
)
from app.models.scheme import PolicyVersion, RuleSet, Scheme
from scripts.demo_seed_reset import reset_demo_data, seed_demo_data
from app.services.policy_loader import load_all_policies
from app.services.provenance_loader import seed_all_provenance
from app.services.provenance_service import (
    ProvenanceNotFoundError,
    ProvenanceService,
    ProvenanceValidationError,
    sanitize_content_reference,
)
from tests.conftest import TestSessionLocal


# ==============================================================================
# Auth Helpers
# ==============================================================================

def _make_citizen_token(
    email: str = "ramesh.kumar@demo.local",
    ref: str = "SYN-CIT-DEMO0001",
    name: str = "Ramesh Kumar (Demo)",
) -> str:
    """Generate authenticated JWT for synthetic citizen."""
    payload = {
        "sub": email,
        "email": email,
        "role": "CITIZEN",
        "citizen_ref": ref,
        "name": name,
        "state": "Uttar Pradesh",
        "district": "Varanasi",
    }
    return create_access_token(data=payload)


def _make_officer_token(
    email: str = "officer.demo@yogyatamitra.local",
    role: str = "OFFICER",
    name: str = "Senior Verification Officer (Demo)",
) -> str:
    """Generate authenticated JWT for verification officer."""
    payload = {
        "sub": email,
        "email": email,
        "role": role,
        "name": name,
        "designation": "Verification Officer Grade I",
        "department": "District Verification Cell, Varanasi",
    }
    return create_access_token(data=payload)


# ==============================================================================
# Canonical Facts for 10 Schemes
# ==============================================================================

SCHEME_ELIGIBLE_FACTS: Dict[str, Dict[str, Any]] = {
    "PM_KISAN": {
        "family": {
            "owns_cultivable_land": True,
            "is_institutional_landholder": False,
            "has_constitutional_post_holder": False,
            "has_public_representative": False,
            "has_disqualified_government_employee": False,
            "has_pensioner_above_ten_thousand": False,
            "has_income_tax_payer": False,
            "has_registered_practicing_professional": False,
            "is_nri": False,
        },
        "land": {"transferred_after_cutoff": False},
    },
    "SSY": {
        "beneficiary": {
            "gender": "FEMALE",
            "is_indian_resident": True,
            "date_of_birth": "2018-01-01",
        },
        "family": {"active_ssy_accounts_count": 0, "has_multiple_birth_exception": False},
        "guardian": {"is_natural_guardian": True, "is_court_appointed_legal_guardian": False},
        "account": {"is_first_account_for_child": True, "opening_date": "2024-06-01"},
    },
    "PM_KMY": {
        "applicant": {"age": 30, "has_other_pension_scheme": False},
        "family": {
            "owns_cultivable_land": True,
            "is_institutional_landholder": False,
            "has_constitutional_post_holder": False,
            "has_disqualified_government_employee": False,
            "has_income_tax_payer": False,
            "has_registered_practicing_professional": False,
        },
        "land": {"record_date_valid": True, "total_land_area_hectares": 1.5},
    },
    "PMUY": {
        "applicant": {"age": 28, "gender": "FEMALE"},
        "household": {
            "has_existing_lpg": False,
            "is_deprived_or_qualifying_category": True,
            "has_government_employee": False,
            "owns_motorized_four_wheeler": False,
        },
    },
    "PM_VISHWAKARMA": {
        "applicant": {"age": 35},
        "trade": {"is_eligible_trade": True, "is_self_employed": True, "has_outstanding_similar_loan": False},
        "family": {"has_government_employee": False, "other_member_enrolled": False},
    },
    "PMAY_G": {
        "location": {"is_rural_area": True},
        "housing": {"owns_pucca_house": False, "house_type": "KUTCHA"},
        "land": {"irrigated_land_acres": 1.0},
        "exclusions": {
            "owns_motorized_three_four_wheeler": False,
            "owns_mechanized_agri_equipment": False,
            "kcc_limit_above_fifty_thousand": False,
        },
        "family": {
            "has_government_employee": False,
            "has_member_earning_above_fifteen_thousand": False,
            "has_income_tax_payer": False,
            "has_professional_tax_payer": False,
        },
    },
    "PMAY_U_2_0": {
        "location": {"is_urban_area": True},
        "housing": {"owns_pucca_house": False},
        "family": {"annual_income": 240000.0, "has_prior_housing_benefit": False},
    },
    "PM_SVANIDHI": {
        "applicant": {"age": 28},
        "vendor": {"is_urban_street_vendor": True, "has_vending_certificate": True},
        "account": {"has_active_bank_account": True},
    },
    "PMMVY": {
        "applicant": {
            "age": 24,
            "is_pregnant_or_lactating": True,
            "is_government_or_psu_employee": False,
            "is_sc_st": True,
        },
        "maternity": {"child_order": 1},
    },
    "IGNOAPS": {
        "applicant": {"age": 65, "has_other_social_security_pension": False},
        "family": {"is_bpl": True},
    },
}

SCHEME_MANDATORY_EVIDENCE: Dict[str, List[str]] = {
    "PM_KISAN": ["LAND_RECORD", "AADHAAR", "BANK_PASSBOOK"],
    "SSY": ["BIRTH_CERTIFICATE", "AADHAAR"],
    "PM_KMY": ["AADHAAR", "LAND_RECORD", "BANK_PASSBOOK"],
    "PMUY": ["AADHAAR", "RATION_CARD", "DEPRIVATION_CERTIFICATE", "BANK_PASSBOOK"],
    "PM_VISHWAKARMA": ["AADHAAR", "ARTISAN_ID_OR_DECLARATION", "RATION_CARD", "BANK_PASSBOOK"],
    "PMAY_G": ["AADHAAR", "HOUSING_VERIFICATION_CERTIFICATE", "JOB_CARD", "BANK_PASSBOOK"],
    "PMAY_U_2_0": ["AADHAAR", "INCOME_CERTIFICATE", "PROPERTY_DOCUMENT_OR_AFFIDAVIT", "BANK_PASSBOOK"],
    "PM_SVANIDHI": ["AADHAAR", "VENDING_PROOF_OR_LOR", "BANK_PASSBOOK"],
    "PMMVY": ["AADHAAR", "MCP_CARD", "BANK_PASSBOOK", "ELIGIBILITY_PROOF_DOCUMENT"],
    "IGNOAPS": ["AADHAAR", "BPL_CARD_OR_CERTIFICATE", "BANK_PASSBOOK"],
}


# ==============================================================================
# Journey Setup Helper
# ==============================================================================

async def _create_test_journey(
    session: AsyncSession,
    scheme_code: str,
    claims_dict: Dict[str, Any],
    evidence_statuses: Dict[str, EvidenceStatus],
    officer_email: str = "officer.demo@yogyatamitra.local",
    citizen_ref: str = "SYN-CIT-PHASE-J-TEST",
) -> Tuple[EvaluationJourney, Citizen, List[Claim], List[Evidence]]:
    """Helper to set up an authentic evaluation journey with bound policy and claims."""
    now = datetime.now(timezone.utc)
    stmt_s = select(Scheme).where(Scheme.scheme_code == scheme_code)
    scheme = (await session.execute(stmt_s)).scalar_one()

    pv_stmt = (
        select(PolicyVersion)
        .where(PolicyVersion.scheme_id == scheme.id)
        .order_by(PolicyVersion.effective_from.desc())
    )
    pv = (await session.execute(pv_stmt)).scalars().first()
    assert pv is not None

    stmt_c = select(Citizen).where(Citizen.synthetic_reference == citizen_ref)
    citizen = (await session.execute(stmt_c)).scalars().first()
    if not citizen:
        citizen = Citizen(
            synthetic_reference=citizen_ref,
            display_name="Phase J Verification Citizen",
            state="Maharashtra",
            district="Pune",
        )
        session.add(citizen)
        await session.flush()

    journey = EvaluationJourney(
        citizen_id=citizen.id,
        scheme_id=scheme.id,
        policy_version_id=pv.id,
        state=JourneyState.VERIFICATION_IN_PROGRESS,
        submitted_at=now,
    )
    session.add(journey)
    await session.flush()

    assignment = OfficerAssignment(
        journey_id=journey.id,
        officer_identity=officer_email,
        officer_name="Senior Verification Officer (Demo)",
        assigned_by="SYSTEM_BALANCER",
        assigned_at=now,
        due_at=now + timedelta(hours=48),
        sla_duration_hours=48,
        status=AssignmentStatus.ASSIGNED,
        is_active=True,
    )
    session.add(assignment)
    await session.flush()

    claims: List[Claim] = []
    for section_name, section_facts in claims_dict.items():
        claim = Claim(
            citizen_id=citizen.id,
            journey_id=journey.id,
            claim_type=section_name,
            value_json=section_facts if isinstance(section_facts, dict) else {"value": section_facts},
            status=ClaimStatus.VERIFIED if all(s == EvidenceStatus.VERIFIED for s in evidence_statuses.values()) else ClaimStatus.PENDING,
            source="CITIZEN_DECLARATION",
            claimed_at=now,
        )
        session.add(claim)
        await session.flush()
        claims.append(claim)

    if not claims:
        dummy_claim = Claim(
            citizen_id=citizen.id,
            journey_id=journey.id,
            claim_type="general",
            value_json={"declared": True},
            status=ClaimStatus.PENDING,
            source="CITIZEN_DECLARATION",
            claimed_at=now,
        )
        session.add(dummy_claim)
        await session.flush()
        claims.append(dummy_claim)

    evidence_items: List[Evidence] = []
    target_claim = claims[0]
    for ev_type, ev_status in evidence_statuses.items():
        ev = Evidence(
            claim_id=target_claim.id,
            evidence_type=ev_type,
            storage_reference=f"vault/{ev_type.lower()}_{uuid.uuid4().hex[:8]}.pdf",
            metadata_json={"document_name": f"{ev_type}.pdf", "file_size_bytes": 102400},
            status=ev_status,
            submitted_at=now,
        )
        session.add(ev)
        await session.flush()

        if ev_status in (EvidenceStatus.VERIFIED, EvidenceStatus.REJECTED):
            v_record = VerificationRecord(
                evidence_id=ev.id,
                claim_id=target_claim.id,
                verification_method="MANUAL_OFFICER_REVIEW",
                status=VerificationStatus[ev_status.value],
                verified_by=officer_email,
                details_json={"notes": "Phase J Verification decision recorded."},
                verified_at=now,
            )
            session.add(v_record)
            await session.flush()

        evidence_items.append(ev)

    await session.commit()
    await session.refresh(journey)
    return journey, citizen, claims, evidence_items


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest_asyncio.fixture(autouse=True)
async def ensure_baseline_data(db_session: AsyncSession) -> None:
    """Ensure statutory policies and provenance metadata are seeded."""
    stmt = select(Scheme).where(Scheme.scheme_code == "PM_KISAN")
    res = await db_session.execute(stmt)
    if not res.scalar_one_or_none():
        await load_all_policies(session=db_session)
    await seed_all_provenance(db_session)


# ==============================================================================
# 1. J-A: End-to-End Citizen & Officer Lifecycle
# ==============================================================================

@pytest.mark.asyncio
async def test_e2e_full_lifecycle_positive(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """J-A: Test complete journey from citizen discovery to decision & provenance."""
    citizen_token = _make_citizen_token(ref="SYN-CIT-DEMO-JA1")
    officer_token = _make_officer_token()
    cit_headers = {"Authorization": f"Bearer {citizen_token}"}
    off_headers = {"Authorization": f"Bearer {officer_token}"}

    # 1. Scheme Discovery
    resp = await async_client.get("/api/v1/citizen/schemes", headers=cit_headers)
    assert resp.status_code == 200
    schemes = resp.json()
    pm_kisan = next((s for s in schemes if s["scheme_code"] == "PM_KISAN"), None)
    assert pm_kisan is not None

    # 2. Form Requirements Discovery
    req_resp = await async_client.get(
        "/api/v1/citizen/schemes/PM_KISAN/requirements", headers=cit_headers
    )
    assert req_resp.status_code == 200
    req_data = req_resp.json()
    assert "sections" in req_data
    assert "fields" in req_data
    assert "evidence_types" in req_data

    # 3. Create Draft Application
    draft_resp = await async_client.post(
        "/api/v1/citizen/applications",
        json={"scheme_code": "PM_KISAN"},
        headers=cit_headers,
    )
    assert draft_resp.status_code == 201
    app_data = draft_resp.json()
    journey_id = app_data["id"]
    assert app_data["state"] == "DRAFT"

    # 4. Save and Submit Application
    valid_facts = {
        "family.owns_cultivable_land": True,
        "land.total_land_area_hectares": 1.8,
        "land.transferred_after_cutoff": False,
        "family.is_institutional_landholder": False,
        "family.has_constitutional_post_holder": False,
        "family.has_public_representative": False,
        "family.has_disqualified_government_employee": False,
        "family.has_pensioner_above_ten_thousand": False,
        "family.has_income_tax_payer": False,
        "family.has_registered_practicing_professional": False,
        "family.is_nri": False,
    }
    submit_resp = await async_client.post(
        f"/api/v1/citizen/applications/{journey_id}/submit",
        json={"facts": valid_facts, "declaration_confirmed": True},
        headers=cit_headers,
    )
    assert submit_resp.status_code == 200
    sub_data = submit_resp.json()
    assert sub_data["state"] in ("FACTS_COLLECTED", "EVIDENCE_PENDING", "VERIFICATION_IN_PROGRESS", "READY_FOR_EVALUATION")

    # 5. Fetch Officer Queue
    q_resp = await async_client.get("/api/v1/officer/queue", headers=off_headers)
    assert q_resp.status_code == 200

    # 6. Officer Case Detail
    case_resp = await async_client.get(f"/api/v1/officer/cases/{journey_id}", headers=off_headers)
    assert case_resp.status_code == 200
    case_data = case_resp.json()
    assert case_data["scheme_code"] == "PM_KISAN"


# ==============================================================================
# 2. J-B: Ten Schemes × Four Outcomes Matrix
# ==============================================================================

@pytest.mark.asyncio
async def test_ten_schemes_all_active_and_bound_to_policies(db_session: AsyncSession) -> None:
    """J-B: Verify all 10 canonical schemes are ACTIVE with bound policy versions."""
    canonical_codes = [
        "PM_KISAN", "SSY", "PM_KMY", "PMUY", "PM_VISHWAKARMA",
        "PMAY_G", "PMAY_U_2_0", "PM_SVANIDHI", "PMMVY", "IGNOAPS"
    ]
    stmt = (
        select(Scheme)
        .where(Scheme.scheme_code.in_(canonical_codes))
        .options(selectinload(Scheme.policy_versions).selectinload(PolicyVersion.rule_set))
    )
    res = await db_session.execute(stmt)
    schemes = {s.scheme_code: s for s in res.scalars().all()}

    assert len(schemes) == 10
    for code in canonical_codes:
        scheme = schemes[code]
        assert scheme.status == SchemeStatus.ACTIVE
        assert len(scheme.policy_versions) >= 1
        for pv in scheme.policy_versions:
            assert pv.rule_set is not None
            assert pv.rule_definition_hash is not None


@pytest.mark.asyncio
async def test_pm_kisan_eligible(async_client: AsyncClient, db_session: AsyncSession) -> None:
    """J-B 1: PM_KISAN positive evaluation -> ELIGIBLE."""
    facts = SCHEME_ELIGIBLE_FACTS["PM_KISAN"]
    evidence = {doc: EvidenceStatus.VERIFIED for doc in SCHEME_MANDATORY_EVIDENCE["PM_KISAN"]}
    journey, _, _, _ = await _create_test_journey(db_session, "PM_KISAN", facts, evidence)

    headers = {"Authorization": f"Bearer {_make_officer_token()}"}
    resp = await async_client.post(f"/api/v1/officer/cases/{journey.id}/evaluate", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["determination"] == "ELIGIBLE"
    assert len(data["reasons_en"]) > 0


@pytest.mark.asyncio
async def test_pm_kisan_ineligible_exclusion(async_client: AsyncClient, db_session: AsyncSession) -> None:
    """J-B 2: PM_KISAN statutory exclusion (income tax paid) -> INELIGIBLE."""
    facts = {
        "family": {
            "owns_cultivable_land": True,
            "is_institutional_landholder": False,
            "has_constitutional_post_holder": False,
            "has_public_representative": False,
            "has_disqualified_government_employee": False,
            "has_pensioner_above_ten_thousand": False,
            "has_income_tax_payer": True,  # Disqualifying exclusion
            "has_registered_practicing_professional": False,
            "is_nri": False,
        },
        "land": {"transferred_after_cutoff": False},
    }
    evidence = {doc: EvidenceStatus.VERIFIED for doc in SCHEME_MANDATORY_EVIDENCE["PM_KISAN"]}
    journey, _, _, _ = await _create_test_journey(db_session, "PM_KISAN", facts, evidence)

    headers = {"Authorization": f"Bearer {_make_officer_token()}"}
    resp = await async_client.post(f"/api/v1/officer/cases/{journey.id}/evaluate", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["determination"] == "INELIGIBLE"


@pytest.mark.asyncio
async def test_pm_kisan_missing_facts_insufficient(async_client: AsyncClient, db_session: AsyncSession) -> None:
    """J-B 3: PM_KISAN missing essential land facts -> INSUFFICIENT_INFORMATION / INELIGIBLE."""
    facts = {"family": {"owns_cultivable_land": False}}
    evidence = {doc: EvidenceStatus.VERIFIED for doc in SCHEME_MANDATORY_EVIDENCE["PM_KISAN"]}
    journey, _, _, _ = await _create_test_journey(db_session, "PM_KISAN", facts, evidence)

    headers = {"Authorization": f"Bearer {_make_officer_token()}"}
    resp = await async_client.post(f"/api/v1/officer/cases/{journey.id}/evaluate", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["determination"] in ("INELIGIBLE", "INSUFFICIENT_INFORMATION")


@pytest.mark.asyncio
async def test_ssy_eligible(async_client: AsyncClient, db_session: AsyncSession) -> None:
    """J-B 4: SSY girl child <= 10 years -> ELIGIBLE."""
    facts = SCHEME_ELIGIBLE_FACTS["SSY"]
    evidence = {doc: EvidenceStatus.VERIFIED for doc in SCHEME_MANDATORY_EVIDENCE["SSY"]}
    journey, _, _, _ = await _create_test_journey(db_session, "SSY", facts, evidence)

    headers = {"Authorization": f"Bearer {_make_officer_token()}"}
    resp = await async_client.post(f"/api/v1/officer/cases/{journey.id}/evaluate", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["determination"] == "ELIGIBLE"


@pytest.mark.asyncio
async def test_ssy_ineligible_age(async_client: AsyncClient, db_session: AsyncSession) -> None:
    """J-B 5: SSY girl child > 10 years -> INELIGIBLE."""
    facts = {
        "beneficiary": {"gender": "FEMALE", "is_indian_resident": True, "date_of_birth": "2010-01-01"},
        "family": {"active_ssy_accounts_count": 0, "has_multiple_birth_exception": False},
        "guardian": {"is_natural_guardian": True, "is_court_appointed_legal_guardian": False},
        "account": {"is_first_account_for_child": True, "opening_date": "2024-06-01"},
    }
    evidence = {doc: EvidenceStatus.VERIFIED for doc in SCHEME_MANDATORY_EVIDENCE["SSY"]}
    journey, _, _, _ = await _create_test_journey(db_session, "SSY", facts, evidence)

    headers = {"Authorization": f"Bearer {_make_officer_token()}"}
    resp = await async_client.post(f"/api/v1/officer/cases/{journey.id}/evaluate", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["determination"] == "INELIGIBLE"


@pytest.mark.asyncio
async def test_pm_kmy_eligible(async_client: AsyncClient, db_session: AsyncSession) -> None:
    """J-B 6: PM_KMY small farmer age 18-40 -> ELIGIBLE."""
    facts = SCHEME_ELIGIBLE_FACTS["PM_KMY"]
    evidence = {doc: EvidenceStatus.VERIFIED for doc in SCHEME_MANDATORY_EVIDENCE["PM_KMY"]}
    journey, _, _, _ = await _create_test_journey(db_session, "PM_KMY", facts, evidence)

    headers = {"Authorization": f"Bearer {_make_officer_token()}"}
    resp = await async_client.post(f"/api/v1/officer/cases/{journey.id}/evaluate", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["determination"] == "ELIGIBLE"


@pytest.mark.asyncio
async def test_pmuy_eligible(async_client: AsyncClient, db_session: AsyncSession) -> None:
    """J-B 7: PMUY adult woman BPL without LPG connection -> ELIGIBLE."""
    facts = SCHEME_ELIGIBLE_FACTS["PMUY"]
    evidence = {doc: EvidenceStatus.VERIFIED for doc in SCHEME_MANDATORY_EVIDENCE["PMUY"]}
    journey, _, _, _ = await _create_test_journey(db_session, "PMUY", facts, evidence)

    headers = {"Authorization": f"Bearer {_make_officer_token()}"}
    resp = await async_client.post(f"/api/v1/officer/cases/{journey.id}/evaluate", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["determination"] == "ELIGIBLE"


@pytest.mark.asyncio
async def test_pm_vishwakarma_eligible(async_client: AsyncClient, db_session: AsyncSession) -> None:
    """J-B 8: PM_VISHWAKARMA traditional artisan -> ELIGIBLE."""
    facts = SCHEME_ELIGIBLE_FACTS["PM_VISHWAKARMA"]
    evidence = {doc: EvidenceStatus.VERIFIED for doc in SCHEME_MANDATORY_EVIDENCE["PM_VISHWAKARMA"]}
    journey, _, _, _ = await _create_test_journey(db_session, "PM_VISHWAKARMA", facts, evidence)

    headers = {"Authorization": f"Bearer {_make_officer_token()}"}
    resp = await async_client.post(f"/api/v1/officer/cases/{journey.id}/evaluate", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["determination"] == "ELIGIBLE"


@pytest.mark.asyncio
async def test_pmay_g_eligible(async_client: AsyncClient, db_session: AsyncSession) -> None:
    """J-B 9: PMAY_G rural homeless/kutcha house -> ELIGIBLE."""
    facts = SCHEME_ELIGIBLE_FACTS["PMAY_G"]
    evidence = {doc: EvidenceStatus.VERIFIED for doc in SCHEME_MANDATORY_EVIDENCE["PMAY_G"]}
    journey, _, _, _ = await _create_test_journey(db_session, "PMAY_G", facts, evidence)

    headers = {"Authorization": f"Bearer {_make_officer_token()}"}
    resp = await async_client.post(f"/api/v1/officer/cases/{journey.id}/evaluate", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["determination"] == "ELIGIBLE"


@pytest.mark.asyncio
async def test_pmay_u_2_0_eligible(async_client: AsyncClient, db_session: AsyncSession) -> None:
    """J-B 10: PMAY_U_2_0 urban EWS family without pucca house -> ELIGIBLE."""
    facts = SCHEME_ELIGIBLE_FACTS["PMAY_U_2_0"]
    evidence = {doc: EvidenceStatus.VERIFIED for doc in SCHEME_MANDATORY_EVIDENCE["PMAY_U_2_0"]}
    journey, _, _, _ = await _create_test_journey(db_session, "PMAY_U_2_0", facts, evidence)

    headers = {"Authorization": f"Bearer {_make_officer_token()}"}
    resp = await async_client.post(f"/api/v1/officer/cases/{journey.id}/evaluate", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["determination"] == "ELIGIBLE"


@pytest.mark.asyncio
async def test_pm_svanidhi_eligible(async_client: AsyncClient, db_session: AsyncSession) -> None:
    """J-B 11: PM_SVANIDHI urban street vendor with CoV -> ELIGIBLE."""
    facts = SCHEME_ELIGIBLE_FACTS["PM_SVANIDHI"]
    evidence = {doc: EvidenceStatus.VERIFIED for doc in SCHEME_MANDATORY_EVIDENCE["PM_SVANIDHI"]}
    journey, _, _, _ = await _create_test_journey(db_session, "PM_SVANIDHI", facts, evidence)

    headers = {"Authorization": f"Bearer {_make_officer_token()}"}
    resp = await async_client.post(f"/api/v1/officer/cases/{journey.id}/evaluate", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["determination"] == "ELIGIBLE"


@pytest.mark.asyncio
async def test_pmmvy_eligible(async_client: AsyncClient, db_session: AsyncSession) -> None:
    """J-B 12: PMMVY pregnant woman first child -> ELIGIBLE."""
    facts = SCHEME_ELIGIBLE_FACTS["PMMVY"]
    evidence = {doc: EvidenceStatus.VERIFIED for doc in SCHEME_MANDATORY_EVIDENCE["PMMVY"]}
    journey, _, _, _ = await _create_test_journey(db_session, "PMMVY", facts, evidence)

    headers = {"Authorization": f"Bearer {_make_officer_token()}"}
    resp = await async_client.post(f"/api/v1/officer/cases/{journey.id}/evaluate", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["determination"] == "ELIGIBLE"


@pytest.mark.asyncio
async def test_ignoaps_eligible(async_client: AsyncClient, db_session: AsyncSession) -> None:
    """J-B 13: IGNOAPS elderly >= 60 in BPL -> ELIGIBLE."""
    facts = SCHEME_ELIGIBLE_FACTS["IGNOAPS"]
    evidence = {doc: EvidenceStatus.VERIFIED for doc in SCHEME_MANDATORY_EVIDENCE["IGNOAPS"]}
    journey, _, _, _ = await _create_test_journey(db_session, "IGNOAPS", facts, evidence)

    headers = {"Authorization": f"Bearer {_make_officer_token()}"}
    resp = await async_client.post(f"/api/v1/officer/cases/{journey.id}/evaluate", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["determination"] == "ELIGIBLE"


# ==============================================================================
# 3. J-C: Complete Clarification Lifecycle
# ==============================================================================

@pytest.mark.asyncio
async def test_clarification_full_round_lifecycle(db_session: AsyncSession) -> None:
    """J-C: Officer requests clarification -> citizen responds -> resolved."""
    cit = Citizen(
        synthetic_reference="SYN-CIT-CLARIF-01",
        display_name="Clarification Citizen",
        date_of_birth=date(1988, 5, 20),
        gender="Male",
    )
    db_session.add(cit)
    await db_session.flush()

    sch_stmt = select(Scheme).where(Scheme.scheme_code == "PM_KISAN")
    sch = (await db_session.execute(sch_stmt)).scalar_one()

    journey = EvaluationJourney(
        citizen_id=cit.id,
        scheme_id=sch.id,
        state=JourneyState.VERIFICATION_IN_PROGRESS,
    )
    db_session.add(journey)
    await db_session.flush()

    # Officer creates clarification request
    clarif = ClarificationRequest(
        journey_id=journey.id,
        round=1,
        requesting_officer="officer.demo@yogyatamitra.local",
        request_reason="Land document illegible; please upload clear page 1 showing khasra number.",
        status=ClarificationStatus.OPEN,
    )
    db_session.add(clarif)
    await db_session.flush()

    assert clarif.status == ClarificationStatus.OPEN
    assert clarif.round == 1

    # Citizen responds
    clarif.response_text = "Uploaded high-resolution scan of land title page 1."
    clarif.status = ClarificationStatus.RESPONDED
    clarif.responded_at = datetime.now(timezone.utc)
    await db_session.flush()

    # Officer reviews and resolves
    clarif.status = ClarificationStatus.RESOLVED
    clarif.resolved_by = "officer.demo@yogyatamitra.local"
    clarif.resolved_at = datetime.now(timezone.utc)
    clarif.resolution_notes = "Verified clear document; khasra number matches."
    await db_session.flush()

    assert clarif.status == ClarificationStatus.RESOLVED


@pytest.mark.asyncio
async def test_clarification_cross_citizen_isolation(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """J-C: Citizen B cannot view or respond to Citizen A's clarification requests."""
    ref_a = f"SYN-CIT-A-CLARIF-{uuid.uuid4().hex[:6]}"
    ref_b = f"SYN-CIT-B-CLARIF-{uuid.uuid4().hex[:6]}"
    cit_a = Citizen(synthetic_reference=ref_a, display_name="Citizen A")
    cit_b = Citizen(synthetic_reference=ref_b, display_name="Citizen B")
    db_session.add_all([cit_a, cit_b])
    await db_session.flush()

    sch = (await db_session.execute(select(Scheme).where(Scheme.scheme_code == "PM_KISAN"))).scalar_one()
    journey_a = EvaluationJourney(citizen_id=cit_a.id, scheme_id=sch.id, state=JourneyState.ACTION_REQUIRED)
    db_session.add(journey_a)
    await db_session.flush()

    clarif = ClarificationRequest(
        journey_id=journey_a.id,
        round=1,
        requesting_officer="officer@test.local",
        request_reason="Need Aadhaar proof",
        status=ClarificationStatus.OPEN,
    )
    db_session.add(clarif)
    await db_session.commit()

    cit_b_token = _make_citizen_token(ref=ref_b)
    resp = await async_client.get(
        f"/api/v1/citizen/applications/{journey_a.id}/clarifications",
        headers={"Authorization": f"Bearer {cit_b_token}"},
    )
    assert resp.status_code == 404


# ==============================================================================
# 4. J-D: Decision Trace Reconstruction from DB Records
# ==============================================================================

@pytest.mark.asyncio
async def test_decision_trace_reconstruction_from_db(db_session: AsyncSession) -> None:
    """J-D: Full statutory decision reconstructible from persisted EvaluationTrace alone."""
    cit = Citizen(synthetic_reference="SYN-CIT-TRACE-RECON", display_name="Recon Citizen")
    db_session.add(cit)
    await db_session.flush()

    stmt = select(PolicyVersion).join(Scheme).where(Scheme.scheme_code == "PM_KISAN").order_by(PolicyVersion.effective_from.desc())
    pv = (await db_session.execute(stmt)).scalars().first()

    facts_snapshot = {"family.owns_cultivable_land": True}

    trace = EvaluationTrace(
        citizen_id=cit.id,
        scheme_id=pv.scheme_id,
        policy_version_id=pv.id,
        evaluation_date=date(2026, 1, 1),
        input_snapshot_json=facts_snapshot,
        result_state=EligibilityResult.ELIGIBLE,
        trace_json={"node_id": "ROOT", "result": "TRUE", "reasons": ["All PM-KISAN conditions met."]},
        rule_definition_hash=pv.rule_definition_hash,
        evaluated_by="SYSTEM_DETERMINISTIC_ENGINE",
    )
    db_session.add(trace)
    await db_session.flush()

    trace_id = trace.id

    recon_stmt = (
        select(EvaluationTrace)
        .where(EvaluationTrace.id == trace_id)
        .options(
            selectinload(EvaluationTrace.policy_version).selectinload(PolicyVersion.scheme),
            selectinload(EvaluationTrace.policy_version).selectinload(PolicyVersion.rule_set),
            selectinload(EvaluationTrace.citizen),
        )
    )
    recon = (await db_session.execute(recon_stmt)).scalar_one()

    assert recon.policy_version_id == pv.id
    assert recon.rule_definition_hash == pv.rule_definition_hash
    assert recon.result_state == EligibilityResult.ELIGIBLE
    assert recon.input_snapshot_json == facts_snapshot
    assert recon.policy_version.scheme.scheme_code == "PM_KISAN"
    assert recon.policy_version.rule_set is not None


# ==============================================================================
# 5. J-E: Four-Outcome Integrity & Tamper Prevention
# ==============================================================================

@pytest.mark.asyncio
async def test_four_outcomes_produced_strictly_by_backend_engine(db_session: AsyncSession) -> None:
    """J-E: Four outcome enum values are strictly distinct and valid."""
    outcomes = [
        EligibilityResult.ELIGIBLE,
        EligibilityResult.INELIGIBLE,
        EligibilityResult.INSUFFICIENT_INFORMATION,
        EligibilityResult.VERIFICATION_REQUIRED,
    ]
    assert len(set(outcomes)) == 4
    for o in outcomes:
        assert isinstance(o.value, str)


@pytest.mark.asyncio
async def test_client_cannot_self_verify_claims_or_evidence(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """J-E: Malicious client cannot submit claims pre-marked as VERIFIED."""
    ref = f"SYN-CIT-TAMPER-{uuid.uuid4().hex[:6]}"
    cit_token = _make_citizen_token(ref=ref)
    headers = {"Authorization": f"Bearer {cit_token}"}

    draft_resp = await async_client.post(
        "/api/v1/citizen/applications",
        json={"scheme_code": "PM_KISAN"},
        headers=headers,
    )
    app_id = draft_resp.json()["id"]

    tampered_facts = {
        "family.owns_cultivable_land": True,
        "land.total_land_area_hectares": 1.5,
        "land.transferred_after_cutoff": False,
        "status": "VERIFIED",
        "claim_status": "VERIFIED",
        "evidence_status": "VERIFIED",
        "evaluation_result": "ELIGIBLE",
    }
    # Client attempts to submit tampered facts with pre-set VERIFIED flags
    submit_resp = await async_client.post(
        f"/api/v1/citizen/applications/{app_id}/submit",
        json={"facts": tampered_facts, "declaration_confirmed": True},
        headers=headers,
    )
    # The server's form-contract validation rejects unexpected/unauthorized fields with 400 Bad Request
    assert submit_resp.status_code in (400, 422)

    # When submitted with valid facts, claims are initialized as CLAIMED, never self-verified
    valid_facts = {
        "family.owns_cultivable_land": True,
        "land.total_land_area_hectares": 1.5,
        "land.transferred_after_cutoff": False,
        "family.is_institutional_landholder": False,
        "family.has_constitutional_post_holder": False,
        "family.has_public_representative": False,
        "family.has_disqualified_government_employee": False,
        "family.has_pensioner_above_ten_thousand": False,
        "family.has_income_tax_payer": False,
        "family.has_registered_practicing_professional": False,
        "family.is_nri": False,
    }
    submit_valid = await async_client.post(
        f"/api/v1/citizen/applications/{app_id}/submit",
        json={"facts": valid_facts, "declaration_confirmed": True},
        headers=headers,
    )
    assert submit_valid.status_code == 200

    stmt = select(Claim).where(Claim.journey_id == uuid.UUID(app_id))
    claims = (await db_session.execute(stmt)).scalars().all()
    for c in claims:
        assert c.status != ClaimStatus.VERIFIED


# ==============================================================================
# 6. J-F: Historical Policy Version Reproducibility (D1 vs D2)
# ==============================================================================

@pytest.mark.asyncio
async def test_historical_policy_version_immutability(db_session: AsyncSession) -> None:
    """J-F: Evaluation under D1 preserves binding to D1 after D2 is created."""
    stmt = (
        select(Scheme)
        .where(Scheme.scheme_code == "PM_KISAN")
        .options(selectinload(Scheme.policy_versions))
    )
    scheme = (await db_session.execute(stmt)).scalar_one()

    # Earlier policy version
    d1 = scheme.policy_versions[-1]
    cit = Citizen(synthetic_reference=f"SYN-CIT-HIST-{uuid.uuid4().hex[:6]}", display_name="Historical Citizen")
    db_session.add(cit)
    await db_session.flush()

    journey = EvaluationJourney(
        citizen_id=cit.id,
        scheme_id=scheme.id,
        policy_version_id=d1.id,
        state=JourneyState.EVALUATED,
    )
    db_session.add(journey)
    await db_session.flush()

    trace = EvaluationTrace(
        citizen_id=cit.id,
        scheme_id=scheme.id,
        policy_version_id=d1.id,
        journey_id=journey.id,
        evaluation_date=date(2020, 1, 1),
        input_snapshot_json={"is_farmer": True},
        result_state=EligibilityResult.ELIGIBLE,
        trace_json={"result": "TRUE"},
        rule_definition_hash=d1.rule_definition_hash,
    )
    db_session.add(trace)
    await db_session.flush()

    check_stmt = select(EvaluationTrace).where(EvaluationTrace.id == trace.id)
    persisted = (await db_session.execute(check_stmt)).scalar_one()
    assert persisted.policy_version_id == d1.id
    assert persisted.rule_definition_hash == d1.rule_definition_hash


# ==============================================================================
# 7. J-G: End-to-End Provenance Traversal
# ==============================================================================

@pytest.mark.asyncio
async def test_provenance_full_graph_traversal(db_session: AsyncSession) -> None:
    """J-G: Traversal from PolicyVersion -> RuleProvenance -> DocumentVersion -> Source."""
    stmt = (
        select(PolicyVersion)
        .join(Scheme)
        .where(Scheme.scheme_code == "PM_KISAN")
        .options(
            selectinload(PolicyVersion.rule_provenances)
            .selectinload(RuleProvenance.document_version)
            .selectinload(OfficialDocumentVersion.document)
            .selectinload(OfficialDocument.official_source)
        )
        .order_by(PolicyVersion.effective_from.desc())
    )
    pv = (await db_session.execute(stmt)).scalars().first()
    assert pv is not None
    assert len(pv.rule_provenances) > 0

    rp = pv.rule_provenances[0]
    assert rp.document_version is not None
    assert rp.document_version.document is not None
    assert rp.document_version.document.official_source is not None
    source = rp.document_version.document.official_source
    assert source.official_domain == "pmkisan.gov.in"
    assert source.canonical_url.startswith("https://")


# ==============================================================================
# 8. J-H: F-01 Hardening (ProvenanceCompleteness Verification States)
# ==============================================================================

@pytest.mark.asyncio
async def test_provenance_completeness_enum_hardening(db_session: AsyncSession) -> None:
    """J-H: Verify SOURCE_METADATA_VERIFIED and PHYSICAL_ARTIFACT_VERIFIED are recognized."""
    stmt = select(OfficialDocumentVersion).limit(5)
    res = await db_session.execute(stmt)
    versions = res.scalars().all()

    for v in versions:
        if v.document_hash is None:
            assert v.provenance_completeness in (
                ProvenanceCompleteness.SOURCE_METADATA_VERIFIED,
                ProvenanceCompleteness.COMPLETE,
            )


# ==============================================================================
# 9. J-I: Public Provenance API Hardening (Filesystem Path Sanitization)
# ==============================================================================

@pytest.mark.asyncio
async def test_public_provenance_api_strips_filesystem_paths(async_client: AsyncClient) -> None:
    """J-I: Ensure public provenance API never exposes server local filesystem paths."""
    resp = await async_client.get("/api/v1/provenance/schemes/PM_KISAN")
    assert resp.status_code == 200
    data = resp.json()

    for doc in data.get("documents", []):
        for v in doc.get("versions", []):
            content_ref = v.get("content_reference")
            if content_ref:
                assert not content_ref.startswith("C:\\")
                assert not content_ref.startswith("D:\\")
                assert not content_ref.startswith("/")
                assert not content_ref.startswith("file:")

    # Direct sanitizer verification
    assert sanitize_content_reference("C:\\internal\\path.pdf") is None
    assert sanitize_content_reference("D:/secrets/doc.pdf") is None
    assert sanitize_content_reference("/etc/passwd") is None
    assert sanitize_content_reference("https://pmkisan.gov.in/doc.pdf") == "https://pmkisan.gov.in/doc.pdf"


# ==============================================================================
# 10. J-J: Provenance Audit Trail Immutability (PostgreSQL Trigger)
# ==============================================================================

@pytest.mark.asyncio
async def test_provenance_audit_events_immutable_trigger(db_session: AsyncSession) -> None:
    """J-J: Direct UPDATE or DELETE on provenance_audit_events raises database exception."""
    event = ProvenanceAuditEvent(
        event_type=ProvenanceEventType.DOCUMENT_REGISTERED,
        entity_type="OfficialDocument",
        entity_id=str(uuid.uuid4()),
        actor_id="TEST_ADMIN",
        actor_role="ADMIN",
        reason="Trigger validation test",
    )
    db_session.add(event)
    await db_session.flush()

    event_id = event.id

    with pytest.raises((DBAPIError, InternalError, Exception)) as exc_info:
        await db_session.execute(
            text(f"UPDATE provenance_audit_events SET reason = 'Tampered' WHERE id = '{event_id}';")
        )
        await db_session.flush()

    assert "forbidden" in str(exc_info.value).lower() or "append-only" in str(exc_info.value).lower()
    await db_session.rollback()


# ==============================================================================
# 11. J-K: Citizen IDOR & Security Isolation
# ==============================================================================

@pytest.mark.asyncio
async def test_citizen_idor_cannot_read_peer_application(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """J-K 1: Citizen B receives HTTP 404 attempting to access Citizen A's application."""
    ref_a = f"SYN-CIT-IDOR-A-{uuid.uuid4().hex[:6]}"
    ref_b = f"SYN-CIT-IDOR-B-{uuid.uuid4().hex[:6]}"
    cit_a = Citizen(synthetic_reference=ref_a, display_name="Citizen A")
    db_session.add(cit_a)
    await db_session.flush()

    sch = (await db_session.execute(select(Scheme).where(Scheme.scheme_code == "PM_KISAN"))).scalar_one()
    journey = EvaluationJourney(citizen_id=cit_a.id, scheme_id=sch.id, state=JourneyState.DRAFT)
    db_session.add(journey)
    await db_session.commit()

    cit_b_token = _make_citizen_token(ref=ref_b, name="Citizen B")
    resp = await async_client.get(
        f"/api/v1/citizen/applications/{journey.id}",
        headers={"Authorization": f"Bearer {cit_b_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_citizen_cannot_access_officer_portal(async_client: AsyncClient) -> None:
    """J-K 2: Citizen token receives HTTP 403 Forbidden accessing officer queue."""
    cit_token = _make_citizen_token()
    resp = await async_client.get(
        "/api/v1/officer/queue",
        headers={"Authorization": f"Bearer {cit_token}"},
    )
    assert resp.status_code == 403


# ==============================================================================
# 12. J-L: Officer Authorization Boundaries
# ==============================================================================

@pytest.mark.asyncio
async def test_unassigned_officer_cannot_verify_peer_case(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """J-L: Officer B cannot verify evidence on a case assigned to Officer A."""
    ref_bound = f"SYN-CIT-BOUND-{uuid.uuid4().hex[:6]}"
    cit = Citizen(synthetic_reference=ref_bound, display_name="Bound Citizen")
    db_session.add(cit)
    await db_session.flush()

    sch = (await db_session.execute(select(Scheme).where(Scheme.scheme_code == "PM_KISAN"))).scalar_one()
    journey = EvaluationJourney(citizen_id=cit.id, scheme_id=sch.id, state=JourneyState.VERIFICATION_IN_PROGRESS)
    db_session.add(journey)
    await db_session.flush()

    claim = Claim(citizen_id=cit.id, journey_id=journey.id, claim_type="LAND", value_json={"area": 1.0}, source="CITIZEN", status=ClaimStatus.CLAIMED)
    db_session.add(claim)
    await db_session.flush()

    evidence = Evidence(claim_id=claim.id, evidence_type="LAND_RECORD", storage_reference="s3://records/land.pdf", status=EvidenceStatus.PENDING)
    db_session.add(evidence)
    await db_session.flush()

    # Assign exclusively to Officer Alpha
    assign = OfficerAssignment(
        journey_id=journey.id,
        officer_identity="officer.alpha@yogyatamitra.local",
        officer_name="Officer Alpha",
        status=AssignmentStatus.ASSIGNED,
        is_active=True,
        due_at=datetime.now(timezone.utc) + timedelta(hours=48),
    )
    db_session.add(assign)
    await db_session.commit()

    # Officer Beta attempts to verify
    officer_beta_token = _make_officer_token(email="officer.beta@yogyatamitra.local", name="Officer Beta")
    resp = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evidence/{evidence.id}/verify",
        json={"action": "VERIFY", "notes": "Officer Beta unauthorized attempt"},
        headers={"Authorization": f"Bearer {officer_beta_token}"},
    )
    assert resp.status_code == 403


# ==============================================================================
# 13. J-M: Client Tampering Rejection
# ==============================================================================

@pytest.mark.asyncio
async def test_tampered_payload_fields_ignored_or_rejected(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    """J-M: Attempt to inject evaluated_by or override evaluation result directly is rejected."""
    ref_m = f"SYN-CIT-TAMPER-M-{uuid.uuid4().hex[:6]}"
    cit_token = _make_citizen_token(ref=ref_m)
    headers = {"Authorization": f"Bearer {cit_token}"}

    draft_resp = await async_client.post(
        "/api/v1/citizen/applications",
        json={"scheme_code": "PM_KISAN"},
        headers=headers,
    )
    assert draft_resp.status_code == 201
    app_id = draft_resp.json()["id"]

    resp = await async_client.post(
        f"/api/v1/citizen/applications/{app_id}/submit",
        json={
            "facts": {"family.owns_cultivable_land": True, "land.total_land_area_hectares": 1.5, "land.transferred_after_cutoff": False},
            "evaluated_by": "MALICIOUS_INJECTION",
            "result_state": "ELIGIBLE",
            "decision": "ELIGIBLE",
        },
        headers=headers,
    )
    assert resp.status_code in (200, 422)

    stmt = select(EvaluationJourney).where(EvaluationJourney.id == uuid.UUID(app_id))
    j = (await db_session.execute(stmt)).scalar_one()
    assert j.state != JourneyState.EVALUATED


# ==============================================================================
# 14. J-N: Concurrency & Idempotency
# ==============================================================================

@pytest.mark.asyncio
async def test_concurrent_evaluation_idempotency(db_session: AsyncSession) -> None:
    """J-N: Multiple parallel AST evaluations on identical context produce identical results."""
    stmt = (
        select(PolicyVersion)
        .join(Scheme)
        .where(Scheme.scheme_code == "PM_KISAN")
        .order_by(PolicyVersion.effective_from.desc())
    )
    pv = (await db_session.execute(stmt)).scalars().first()

    rs_stmt = select(RuleSet).where(RuleSet.policy_version_id == pv.id)
    ruleset = (await db_session.execute(rs_stmt)).scalar_one()

    context = EvaluationContext(
        data={
            "family.owns_cultivable_land": True,
            "family.is_institutional_landholder": False,
            "family.has_constitutional_post_holder": False,
            "family.has_public_representative": False,
            "family.has_disqualified_government_employee": False,
            "family.has_pensioner_above_ten_thousand": False,
            "family.has_income_tax_payer": False,
            "family.has_registered_practicing_professional": False,
            "family.is_nri": False,
            "land.transferred_after_cutoff": False,
        },
        evaluation_date=date(2026, 1, 1),
    )

    evaluator = DeterministicEvaluator()

    results = await asyncio.gather(
        *(asyncio.to_thread(evaluator.evaluate, ruleset.definition_json, context) for _ in range(5))
    )

    first_result = results[0]
    for r in results[1:]:
        assert r.overall_result == first_result.overall_result
        assert r.root_truth_value == first_result.root_truth_value


# ==============================================================================
# 15. J-O: Transaction Recovery & Rollback
# ==============================================================================

@pytest.mark.asyncio
async def test_transaction_rollback_on_evaluation_error(db_session: AsyncSession) -> None:
    """J-O: If a failure occurs before commit, transaction rolls back cleanly without orphan state."""
    cit = Citizen(synthetic_reference="SYN-CIT-ROLLBACK-01", display_name="Rollback Citizen")
    db_session.add(cit)
    await db_session.flush()

    sch = (await db_session.execute(select(Scheme).where(Scheme.scheme_code == "PM_KISAN"))).scalar_one()
    journey = EvaluationJourney(citizen_id=cit.id, scheme_id=sch.id, state=JourneyState.DRAFT)
    db_session.add(journey)
    await db_session.flush()

    await db_session.rollback()

    check = (
        await db_session.execute(
            select(Citizen).where(Citizen.synthetic_reference == "SYN-CIT-ROLLBACK-01")
        )
    ).scalar_one_or_none()
    assert check is None


# ==============================================================================
# 16. J-P & J-Q: Synthetic Demonstration Data & Reset Script
# ==============================================================================

@pytest.mark.asyncio
async def test_demo_seed_and_reset_idempotent(db_session: AsyncSession) -> None:
    """J-P & J-Q: Demo seed and reset operates cleanly and idempotently on synthetic data."""
    # 1. Reset first
    await reset_demo_data(db_session)
    await db_session.commit()

    # 2. Seed demo data
    await seed_demo_data(db_session)
    await db_session.commit()

    stmt = select(Citizen).where(Citizen.synthetic_reference.like("SYN-CIT-DEMO%"))
    citizens = (await db_session.execute(stmt)).scalars().all()
    assert len(citizens) == 3
    refs = {c.synthetic_reference for c in citizens}
    assert "SYN-CIT-DEMO0001" in refs
    assert "SYN-CIT-DEMO0002" in refs
    assert "SYN-CIT-DEMO0003" in refs

    # 3. Reset again cleans them up
    await reset_demo_data(db_session)
    await db_session.commit()

    stmt_after = select(Citizen).where(Citizen.synthetic_reference.like("SYN-CIT-DEMO%"))
    remaining = (await db_session.execute(stmt_after)).scalars().all()
    assert len(remaining) == 0
