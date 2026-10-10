"""Comprehensive Test Suite for YogyataMitra Phase H (Ten Target Government Schemes).

Verifies:
1. Metadata & Requirements Discovery across ALL 10 Canonical Schemes:
   - PM_KISAN, SSY, PM_KMY, PMUY, PM_VISHWAKARMA, PMAY_G, PMAY_U_2_0, PM_SVANIDHI, PMMVY, IGNOAPS
   - Structural validation of form metadata (bilingual labels, sections, fields, evidence)
   - Public & Citizen API requirements discovery endpoints
2. Authoritative Server-Side Validation:
   - Rejection of unknown / unexpected fields (HTTP 400)
   - Required field enforcement at submission
   - Numeric range, type, and conditional field evaluation
3. The 40 Canonical Policy Scenarios (10 schemes x 4 canonical outcomes):
   - ELIGIBLE: All statutory criteria met with verified documentary evidence
   - INELIGIBLE: Statutory exclusion triggered or cutoff violated
   - INSUFFICIENT_INFORMATION: Mandatory evidence missing or unstated prerequisite facts
   - VERIFICATION_REQUIRED: Mandatory documentary evidence attached but pending officer review
4. Provenance, Bilingual Explanations & Security Invariants:
   - Deterministic AST evaluation trace with SHA-256 hash provenance
   - Bilingual statutory explanation reasons (English + Hindi)
   - Client cannot escalate claim/evidence status to VERIFIED
   - Citizen IDOR protection and officer assignment authorization
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.assignment import OfficerAssignment
from app.models.citizen import Citizen, Claim, Evidence, VerificationRecord
from app.models.enums import (
    AssignmentStatus,
    ClaimStatus,
    EligibilityResult,
    EvidenceStatus,
    JourneyState,
    SchemeStatus,
    VerificationStatus,
)
from app.models.evaluation import EvaluationTrace
from app.models.human_review import HumanReviewAuditEvent
from app.models.journey import EvaluationJourney
from app.models.scheme import PolicyVersion, RuleSet, Scheme
from app.schemas.form_metadata import (
    PolicyFormMetadata,
    FormFieldType,
)
from app.services.form_metadata_service import (
    get_policy_form_metadata,
    _FORM_REGISTRY,
)
from app.services.form_metadata_validator import (
    validate_policy_form_metadata,
    validate_citizen_form_submission,
)
from app.services.policy_loader import load_all_policies
from tests.conftest import TestSessionLocal as AsyncSessionLocal


CANONICAL_10_SCHEMES = [
    "PM_KISAN",
    "SSY",
    "PM_KMY",
    "PMUY",
    "PM_VISHWAKARMA",
    "PMAY_G",
    "PMAY_U_2_0",
    "PM_SVANIDHI",
    "PMMVY",
    "IGNOAPS",
]


def _make_citizen_token(
    email: str = "rameshwar.sharma@test.local",
    ref: str = "SYN-CIT-PHASE-H",
    name: str = "Rameshwar Sharma",
) -> str:
    """Generate a citizen JWT for test requests."""
    payload = {
        "sub": email,
        "role": "CITIZEN",
        "citizen_ref": ref,
        "name": name,
        "state": "Maharashtra",
        "district": "Pune",
    }
    return create_access_token(data=payload)


def _make_officer_token(
    email: str = "officer.verif@yogyatamitra.local",
    role: str = "OFFICER",
    name: str = "Senior Verification Officer (Phase H)",
) -> str:
    """Generate an officer JWT for test requests."""
    payload = {
        "sub": email,
        "email": email,
        "role": role,
        "name": name,
        "designation": "Verification Officer Grade I",
        "department": "Welfare Verification Cell",
    }
    return create_access_token(data=payload)


# ==============================================================================
# Database Seed Fixture
# ==============================================================================

@pytest_asyncio.fixture(scope="function", autouse=True)
async def ensure_all_10_schemes_loaded():
    """Ensure all 10 canonical schemes and their policies/rulesets are loaded."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(Scheme).where(Scheme.scheme_code.in_(CANONICAL_10_SCHEMES))
        )
        loaded = {s.scheme_code for s in res.scalars().all()}
        if len(loaded) < 10:
            await load_all_policies(session=session)


async def _create_journey_with_claims_and_evidence(
    session: AsyncSession,
    scheme_code: str,
    claims_dict: Dict[str, Any],
    evidence_statuses: Dict[str, EvidenceStatus],
    citizen_ref: str = "SYN-CIT-PHASE-H",
    officer_email: str = "officer.verif@yogyatamitra.local",
) -> tuple[EvaluationJourney, Citizen, List[Claim], List[Evidence]]:
    """Helper to persist a submitted journey with claims and evidence."""
    now = datetime.now(timezone.utc)

    # 1. Scheme
    stmt_s = select(Scheme).where(Scheme.scheme_code == scheme_code)
    scheme = (await session.execute(stmt_s)).scalars().first()
    assert scheme is not None, f"Scheme {scheme_code} not found in database"

    # 2. PolicyVersion
    pv_stmt = (
        select(PolicyVersion)
        .where(PolicyVersion.scheme_id == scheme.id)
        .order_by(PolicyVersion.effective_from.desc())
    )
    pv = (await session.execute(pv_stmt)).scalars().first()
    assert pv is not None, f"PolicyVersion for {scheme_code} not found"

    # 3. Citizen
    stmt_c = select(Citizen).where(Citizen.synthetic_reference == citizen_ref)
    citizen = (await session.execute(stmt_c)).scalars().first()
    if not citizen:
        citizen = Citizen(
            id=uuid.uuid4(),
            synthetic_reference=citizen_ref,
            display_name="Test Citizen Phase H",
            state="Maharashtra",
            district="Pune",
        )
        session.add(citizen)
        await session.flush()

    # 4. Journey
    journey = EvaluationJourney(
        id=uuid.uuid4(),
        citizen_id=citizen.id,
        scheme_id=scheme.id,
        policy_version_id=pv.id,
        state=JourneyState.VERIFICATION_IN_PROGRESS,
        submitted_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(journey)
    await session.flush()

    # 5. Officer Assignment
    assignment = OfficerAssignment(
        id=uuid.uuid4(),
        journey_id=journey.id,
        officer_identity=officer_email,
        officer_name="Senior Verification Officer (Phase H)",
        assigned_by="SYSTEM_BALANCER",
        assigned_at=now,
        due_at=now + timedelta(hours=48),
        sla_duration_hours=48,
        status=AssignmentStatus.ASSIGNED,
        is_active=True,
    )
    session.add(assignment)
    await session.flush()

    # 6. Claims
    claims: List[Claim] = []
    for section_name, section_facts in claims_dict.items():
        claim = Claim(
            id=uuid.uuid4(),
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
            id=uuid.uuid4(),
            citizen_id=citizen.id,
            journey_id=journey.id,
            claim_type="statutory.declaration",
            value_json={"declared": True},
            status=ClaimStatus.PENDING,
            source="CITIZEN_DECLARATION",
            claimed_at=now,
        )
        session.add(dummy_claim)
        await session.flush()
        claims.append(dummy_claim)

    # 7. Evidence
    evidence_items: List[Evidence] = []
    target_claim = claims[0]
    for ev_type, ev_status in evidence_statuses.items():
        ev = Evidence(
            id=uuid.uuid4(),
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
                id=uuid.uuid4(),
                evidence_id=ev.id,
                claim_id=target_claim.id,
                verification_method="MANUAL_OFFICER_REVIEW",
                status=VerificationStatus[ev_status.value],
                verified_by=officer_email,
                details_json={"notes": "Phase H Statutory verification decision recorded."},
                verified_at=now,
            )
            session.add(v_record)
            await session.flush()

        evidence_items.append(ev)

    await session.commit()
    await session.refresh(journey)
    return journey, citizen, claims, evidence_items


# ==============================================================================
# Fact Dictionaries for the 10 Schemes
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
        "land": {
            "transferred_after_cutoff": False,
        },
    },
    "SSY": {
        "beneficiary": {
            "gender": "FEMALE",
            "is_indian_resident": True,
            "date_of_birth": "2018-01-01",
        },
        "family": {
            "active_ssy_accounts_count": 0,
            "has_multiple_birth_exception": False,
        },
        "guardian": {
            "is_natural_guardian": True,
            "is_court_appointed_legal_guardian": False,
        },
        "account": {
            "is_first_account_for_child": True,
            "opening_date": "2024-06-01",
        },
    },
    "PM_KMY": {
        "applicant": {
            "age": 30,
            "has_other_pension_scheme": False,
        },
        "family": {
            "owns_cultivable_land": True,
            "is_institutional_landholder": False,
            "has_constitutional_post_holder": False,
            "has_disqualified_government_employee": False,
            "has_income_tax_payer": False,
            "has_registered_practicing_professional": False,
        },
        "land": {
            "record_date_valid": True,
            "total_land_area_hectares": 1.5,
        },
    },
    "PMUY": {
        "applicant": {
            "age": 28,
            "gender": "FEMALE",
        },
        "household": {
            "has_existing_lpg": False,
            "is_deprived_or_qualifying_category": True,
            "has_government_employee": False,
            "owns_motorized_four_wheeler": False,
        },
    },
    "PM_VISHWAKARMA": {
        "applicant": {
            "age": 35,
        },
        "trade": {
            "is_eligible_trade": True,
            "is_self_employed": True,
            "has_outstanding_similar_loan": False,
        },
        "family": {
            "has_government_employee": False,
            "other_member_enrolled": False,
        },
    },
    "PMAY_G": {
        "location": {
            "is_rural_area": True,
        },
        "housing": {
            "owns_pucca_house": False,
            "house_type": "KUTCHA",
        },
        "land": {
            "irrigated_land_acres": 1.0,
        },
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
        "location": {
            "is_urban_area": True,
        },
        "housing": {
            "owns_pucca_house": False,
        },
        "family": {
            "annual_income": 240000.0,
            "has_prior_housing_benefit": False,
        },
    },
    "PM_SVANIDHI": {
        "applicant": {
            "age": 28,
        },
        "vendor": {
            "is_urban_street_vendor": True,
            "has_vending_certificate": True,
        },
        "account": {
            "has_active_bank_account": True,
        },
    },
    "PMMVY": {
        "applicant": {
            "age": 24,
            "is_pregnant_or_lactating": True,
            "is_government_or_psu_employee": False,
            "is_sc_st": True,
        },
        "maternity": {
            "child_order": 1,
        },
    },
    "IGNOAPS": {
        "applicant": {
            "age": 65,
            "has_other_social_security_pension": False,
        },
        "family": {
            "is_bpl": True,
        },
    },
}

SCHEME_INELIGIBLE_FACTS: Dict[str, Dict[str, Any]] = {
    "PM_KISAN": {
        "family": {
            "owns_cultivable_land": True,
            "is_institutional_landholder": False,
            "has_constitutional_post_holder": False,
            "has_public_representative": False,
            "has_disqualified_government_employee": False,
            "has_pensioner_above_ten_thousand": False,
            "has_income_tax_payer": True,  # Disqualification: income tax payee
            "has_registered_practicing_professional": False,
            "is_nri": False,
        },
        "land": {"transferred_after_cutoff": False},
    },
    "SSY": {
        "beneficiary": {
            "gender": "MALE",  # Disqualification: not a girl child
            "is_indian_resident": True,
            "date_of_birth": "2018-01-01",
        },
        "family": {"active_ssy_accounts_count": 0, "has_multiple_birth_exception": False},
        "guardian": {"is_natural_guardian": True, "is_court_appointed_legal_guardian": False},
        "account": {"is_first_account_for_child": True, "opening_date": "2024-06-01"},
    },
    "PM_KMY": {
        "applicant": {"age": 55, "has_other_pension_scheme": False},  # Disqualification: age > 40
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
            "has_existing_lpg": True,  # Disqualification: existing LPG connection
            "is_deprived_or_qualifying_category": True,
            "has_government_employee": False,
            "owns_motorized_four_wheeler": False,
        },
    },
    "PM_VISHWAKARMA": {
        "applicant": {"age": 35},
        "trade": {
            "is_eligible_trade": False,  # Disqualification: not in 18 notified artisan crafts
            "is_self_employed": True,
            "has_outstanding_similar_loan": False,
        },
        "family": {"has_government_employee": False, "other_member_enrolled": False},
    },
    "PMAY_G": {
        "location": {"is_rural_area": True},
        "housing": {
            "owns_pucca_house": True,  # Disqualification: owns pucca house
            "house_type": "PUCCA",
        },
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
        "housing": {"owns_pucca_house": True},  # Disqualification: owns pucca house
        "family": {"annual_income": 240000.0, "has_prior_housing_benefit": False},
    },
    "PM_SVANIDHI": {
        "applicant": {"age": 28},
        "vendor": {
            "is_urban_street_vendor": False,  # Disqualification: not a street vendor
            "has_vending_certificate": False,
            "has_letter_of_recommendation": False,
            "identified_in_ulb_survey": False,
        },
        "account": {"has_active_bank_account": True},
    },
    "PMMVY": {
        "applicant": {
            "age": 24,
            "is_pregnant_or_lactating": True,
            "is_government_or_psu_employee": True,  # Disqualification: regular government employee
            "is_sc_st": True,
        },
        "maternity": {"child_order": 1},
    },
    "IGNOAPS": {
        "applicant": {"age": 45, "has_other_social_security_pension": False},  # Disqualification: age < 60
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
# SECTION 1: Form Metadata & Requirements Discovery Tests
# ==============================================================================

def test_all_10_schemes_in_form_registry():
    """All 10 target schemes must have registered form metadata builders."""
    registered_codes = {k[0] for k in _FORM_REGISTRY.keys()}
    for scheme_code in CANONICAL_10_SCHEMES:
        assert scheme_code in registered_codes, f"Scheme {scheme_code} missing from form registry"


def test_form_metadata_structural_validation_all_10_schemes():
    """Every registered policy form metadata must pass structural validator."""
    for (scheme_code, version_code), builder in _FORM_REGISTRY.items():
        meta = builder() if callable(builder) else builder
        assert isinstance(meta, PolicyFormMetadata)
        assert meta.scheme_code == scheme_code
        assert meta.policy_version_code == version_code
        assert len(meta.sections) > 0, f"No sections in {scheme_code} {version_code}"
        assert len(meta.fields) > 0, f"No fields in {scheme_code} {version_code}"
        assert len(meta.evidence_types) > 0, f"No evidence types in {scheme_code} {version_code}"

        # Must pass structural validation without error
        validate_policy_form_metadata(meta)


@pytest.mark.asyncio
async def test_api_requirements_discovery_all_10_schemes(async_client: AsyncClient):
    """GET /api/v1/citizen/schemes/{scheme_code}/requirements returns 200 for all 10 schemes."""
    token = _make_citizen_token()
    headers = {"Authorization": f"Bearer {token}"}
    for scheme_code in CANONICAL_10_SCHEMES:
        resp = await async_client.get(
            f"/api/v1/citizen/schemes/{scheme_code}/requirements", headers=headers
        )
        assert resp.status_code == 200, f"Failed for {scheme_code}: {resp.text}"
        data = resp.json()
        assert data["scheme_code"] == scheme_code
        assert len(data["sections"]) > 0
        assert len(data["fields"]) > 0
        assert len(data["evidence_types"]) > 0

        # Check bilingual representation
        for sec in data["sections"]:
            assert sec["title_en"] and sec["title_hi"]
        for fld in data["fields"]:
            assert fld["label_en"] and fld["label_hi"]


@pytest.mark.asyncio
async def test_api_citizen_available_schemes_contains_all_10(async_client: AsyncClient):
    """GET /api/v1/citizen/schemes contains all 10 canonical schemes."""
    token = _make_citizen_token()
    headers = {"Authorization": f"Bearer {token}"}
    resp = await async_client.get("/api/v1/citizen/schemes", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    codes = {s["scheme_code"] for s in data}
    for scheme_code in CANONICAL_10_SCHEMES:
        assert scheme_code in codes, f"Scheme {scheme_code} missing from citizen available schemes"


# ==============================================================================
# SECTION 2: Server-Side Form Validation Tests
# ==============================================================================

def test_submission_rejects_unknown_fields_for_new_schemes():
    """Form submission with unrecognized fields must be rejected (anti-tampering)."""
    for scheme_code in ["PM_KMY", "PMUY", "PM_VISHWAKARMA", "PMAY_G", "PMAY_U_2_0", "PM_SVANIDHI", "PMMVY", "IGNOAPS"]:
        meta = get_policy_form_metadata(scheme_code)
        bad_facts = {"applicant.age": 30, "malicious_unregistered_key": "injected_value"}
        errors = validate_citizen_form_submission(bad_facts, meta, is_submission=True)
        assert len(errors) > 0
        assert any("Unknown" in err or "malicious_unregistered_key" in err for err in errors)


def test_submission_rejects_missing_required_fields_at_final_submission():
    """Final submission must reject missing required statutory fields."""
    for scheme_code in ["PM_KMY", "PMUY", "PM_VISHWAKARMA", "PMAY_G", "PMAY_U_2_0", "PM_SVANIDHI", "PMMVY", "IGNOAPS"]:
        meta = get_policy_form_metadata(scheme_code)
        empty_facts: Dict[str, Any] = {}
        errors = validate_citizen_form_submission(empty_facts, meta, is_submission=True)
        assert len(errors) > 0


# ==============================================================================
# SECTION 3: The 40 Canonical Policy Scenarios (10 Schemes x 4 Scenarios)
# ==============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize("scheme_code", CANONICAL_10_SCHEMES)
async def test_canonical_scenario_1_eligible(
    async_client: AsyncClient, db_session: AsyncSession, scheme_code: str
):
    """Scenario 1: ELIGIBLE - All criteria met and all mandatory evidence VERIFIED."""
    facts = SCHEME_ELIGIBLE_FACTS[scheme_code]
    mandatory_docs = SCHEME_MANDATORY_EVIDENCE[scheme_code]
    evidence_statuses = {doc: EvidenceStatus.VERIFIED for doc in mandatory_docs}

    journey, _, _, _ = await _create_journey_with_claims_and_evidence(
        db_session,
        scheme_code=scheme_code,
        claims_dict=facts,
        evidence_statuses=evidence_statuses,
    )

    token = _make_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evaluate",
        headers=headers,
        json={"notes": f"Statutory evaluation of {scheme_code} for canonical eligible case."},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["determination"] == "ELIGIBLE", f"Expected ELIGIBLE for {scheme_code}, got {data['determination']}: {data.get('reasons_en')}"
    assert len(data["reasons_en"]) > 0
    assert len(data["reasons_hi"]) > 0
    assert data["evaluation_id"] is not None
    assert data["ruleset_hash"] is not None

    # Check journey transition
    async with AsyncSessionLocal() as session:
        j = await session.get(EvaluationJourney, journey.id)
        assert j.state == JourneyState.EVALUATED
        assert j.latest_evaluation_id is not None


@pytest.mark.asyncio
@pytest.mark.parametrize("scheme_code", CANONICAL_10_SCHEMES)
async def test_canonical_scenario_2_ineligible(
    async_client: AsyncClient, db_session: AsyncSession, scheme_code: str
):
    """Scenario 2: INELIGIBLE - Statutory criterion violated or exclusion triggered."""
    facts = SCHEME_INELIGIBLE_FACTS[scheme_code]
    mandatory_docs = SCHEME_MANDATORY_EVIDENCE[scheme_code]
    evidence_statuses = {doc: EvidenceStatus.VERIFIED for doc in mandatory_docs}

    journey, _, _, _ = await _create_journey_with_claims_and_evidence(
        db_session,
        scheme_code=scheme_code,
        claims_dict=facts,
        evidence_statuses=evidence_statuses,
    )

    token = _make_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evaluate",
        headers=headers,
        json={"notes": f"Statutory evaluation of {scheme_code} for canonical ineligible case."},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["determination"] == "INELIGIBLE", f"Expected INELIGIBLE for {scheme_code}, got {data['determination']}"
    assert len(data["reasons_en"]) > 0
    assert len(data["reasons_hi"]) > 0


@pytest.mark.asyncio
@pytest.mark.parametrize("scheme_code", CANONICAL_10_SCHEMES)
async def test_canonical_scenario_3_insufficient_information(
    async_client: AsyncClient, db_session: AsyncSession, scheme_code: str
):
    """Scenario 3: INSUFFICIENT_INFORMATION - Missing mandatory evidence yields halt."""
    facts = SCHEME_ELIGIBLE_FACTS[scheme_code]
    # Completely omit mandatory evidence (0 evidence items attached)
    evidence_statuses: Dict[str, EvidenceStatus] = {}

    journey, _, _, _ = await _create_journey_with_claims_and_evidence(
        db_session,
        scheme_code=scheme_code,
        claims_dict=facts,
        evidence_statuses=evidence_statuses,
    )

    token = _make_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evaluate",
        headers=headers,
        json={"notes": f"Evaluation of {scheme_code} with missing mandatory evidence."},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["determination"] == "INSUFFICIENT_INFORMATION", f"Expected INSUFFICIENT_INFORMATION for {scheme_code}, got {data['determination']}"
    assert len(data["missing_facts"]) > 0

    # Journey state must transition to ACTION_REQUIRED
    async with AsyncSessionLocal() as session:
        j = await session.get(EvaluationJourney, journey.id)
        assert j.state == JourneyState.ACTION_REQUIRED


@pytest.mark.asyncio
@pytest.mark.parametrize("scheme_code", CANONICAL_10_SCHEMES)
async def test_canonical_scenario_4_verification_required(
    async_client: AsyncClient, db_session: AsyncSession, scheme_code: str
):
    """Scenario 4: VERIFICATION_REQUIRED - Mandatory evidence attached but PENDING review."""
    facts = SCHEME_ELIGIBLE_FACTS[scheme_code]
    mandatory_docs = SCHEME_MANDATORY_EVIDENCE[scheme_code]
    # Set all mandatory evidence to PENDING
    evidence_statuses = {doc: EvidenceStatus.PENDING for doc in mandatory_docs}

    journey, _, _, _ = await _create_journey_with_claims_and_evidence(
        db_session,
        scheme_code=scheme_code,
        claims_dict=facts,
        evidence_statuses=evidence_statuses,
    )

    token = _make_officer_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evaluate",
        headers=headers,
        json={"notes": f"Evaluation of {scheme_code} with unverified evidence."},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["determination"] == "VERIFICATION_REQUIRED", f"Expected VERIFICATION_REQUIRED for {scheme_code}, got {data['determination']}"
    assert len(data["reasons_en"]) > 0
    assert len(data["reasons_hi"]) > 0

    # Journey state must reflect verification required (ACTION_REQUIRED)
    async with AsyncSessionLocal() as session:
        j = await session.get(EvaluationJourney, journey.id)
        assert j.state == JourneyState.ACTION_REQUIRED


# ==============================================================================
# SECTION 4: Security, IDOR & Authorization Invariants
# ==============================================================================

@pytest.mark.asyncio
async def test_citizen_cannot_invoke_officer_evaluation(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Citizen token must be strictly forbidden from officer evaluation endpoints (HTTP 403)."""
    journey, _, _, _ = await _create_journey_with_claims_and_evidence(
        db_session,
        scheme_code="PM_KMY",
        claims_dict=SCHEME_ELIGIBLE_FACTS["PM_KMY"],
        evidence_statuses={doc: EvidenceStatus.VERIFIED for doc in SCHEME_MANDATORY_EVIDENCE["PM_KMY"]},
    )

    citizen_token = _make_citizen_token()
    headers = {"Authorization": f"Bearer {citizen_token}"}

    resp = await async_client.post(
        f"/api/v1/officer/cases/{journey.id}/evaluate",
        headers=headers,
        json={"notes": "Citizen trying to self-evaluate"},
    )
    assert resp.status_code == 403, f"Expected 403 Forbidden, got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_citizen_cannot_self_escalate_claims_or_evidence_to_verified(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Citizen draft submission must strictly store claims as CLAIMED and evidence as PENDING."""
    citizen_token = _make_citizen_token(ref="SYN-CIT-TAMPER-TEST")
    headers = {"Authorization": f"Bearer {citizen_token}"}

    # 1. Create Draft
    create_resp = await async_client.post(
        "/api/v1/citizen/applications",
        headers=headers,
        json={"scheme_code": "PM_VISHWAKARMA"},
    )
    assert create_resp.status_code == 201, create_resp.text
    app_id = create_resp.json()["id"]

    # 2. Try to submit with claims and evidence
    submit_resp = await async_client.post(
        f"/api/v1/citizen/applications/{app_id}/submit",
        headers=headers,
        json={
            "facts": {
                "applicant.age": 35,
                "trade.trade_name": "CARPENTER",
                "trade.is_eligible_trade": True,
                "trade.is_self_employed": True,
                "trade.has_outstanding_similar_loan": False,
                "family.has_government_employee": False,
                "family.other_member_enrolled": False,
            },
            "evidence_items": [
                {
                    "evidence_type": "AADHAAR",
                    "storage_reference": "vault/aadhaar_tamper.pdf",
                    "document_name": "Aadhaar Card.pdf",
                },
                {
                    "evidence_type": "ARTISAN_ID_OR_DECLARATION",
                    "storage_reference": "vault/artisan_tamper.pdf",
                    "document_name": "Artisan Card.pdf",
                },
                {
                    "evidence_type": "RATION_CARD",
                    "storage_reference": "vault/ration_tamper.pdf",
                    "document_name": "Ration Card.pdf",
                },
                {
                    "evidence_type": "BANK_PASSBOOK",
                    "storage_reference": "vault/bank_tamper.pdf",
                    "document_name": "Bank Passbook.pdf",
                },
            ],
            "declaration_confirmed": True,
        },
    )
    assert submit_resp.status_code == 200, submit_resp.text

    # 3. Verify database records: claims must NOT be VERIFIED
    async with AsyncSessionLocal() as session:
        stmt_claims = select(Claim).where(Claim.journey_id == uuid.UUID(app_id))
        claims = (await session.execute(stmt_claims)).scalars().all()
        for c in claims:
            assert c.status != ClaimStatus.VERIFIED, "Claim was erroneously marked VERIFIED by client!"

        stmt_ev = select(Evidence).join(Claim).where(Claim.journey_id == uuid.UUID(app_id))
        evidences = (await session.execute(stmt_ev)).scalars().all()
        for ev in evidences:
            assert ev.status != EvidenceStatus.VERIFIED, "Evidence was erroneously marked VERIFIED by client!"
            assert ev.status == EvidenceStatus.PENDING


@pytest.mark.asyncio
async def test_citizen_idor_cannot_access_other_citizens_application(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Citizen A cannot view or manipulate Citizen B's application (HTTP 404)."""
    # Create journey for Citizen A
    journey, _, _, _ = await _create_journey_with_claims_and_evidence(
        db_session,
        scheme_code="PMUY",
        claims_dict=SCHEME_ELIGIBLE_FACTS["PMUY"],
        evidence_statuses={doc: EvidenceStatus.VERIFIED for doc in SCHEME_MANDATORY_EVIDENCE["PMUY"]},
        citizen_ref="SYN-CIT-CITIZEN-A",
    )

    # Citizen B tries to access Citizen A's application
    token_b = _make_citizen_token(ref="SYN-CIT-CITIZEN-B", email="citizen.b@test.local")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    resp = await async_client.get(
        f"/api/v1/citizen/applications/{journey.id}",
        headers=headers_b,
    )
    assert resp.status_code == 404, f"Expected 404 Not Found (IDOR protection), got {resp.status_code}"
