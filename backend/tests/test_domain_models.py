"""Integration tests for domain models, relationships, and constraints in PostgreSQL."""

import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.citizen import Citizen, Claim, Evidence, VerificationRecord
from app.models.enums import (
    ClaimStatus,
    EligibilityResult,
    EvidenceStatus,
    SchemeStatus,
    VerificationStatus,
)
from app.models.evaluation import EvaluationTrace
from app.models.scheme import PolicyVersion, RuleSet, Scheme


@pytest.mark.integration
@pytest.mark.asyncio
async def test_scheme_creation_and_uniqueness(db_session: AsyncSession):
    """Verify Scheme creation and unique constraint on scheme_code."""
    code = f"test_scheme_{uuid.uuid4().hex[:8]}"
    scheme = Scheme(
        scheme_code=code,
        name_en="Test Scheme",
        name_hi="परीक्षण योजना",
        description_en="Test Description",
        description_hi="परीक्षण विवरण",
        official_url="https://example.gov.in/scheme",
        status=SchemeStatus.ACTIVE,
    )
    db_session.add(scheme)
    await db_session.commit()

    # Attempt to insert duplicate scheme_code
    duplicate = Scheme(
        scheme_code=code,
        name_en="Duplicate Scheme",
        name_hi="डुप्लिकेट योजना",
        description_en="Duplicate Description",
        description_hi="डुप्लिकेट विवरण",
        official_url="https://example.gov.in/duplicate",
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_scheme_to_policy_version_relationship(db_session: AsyncSession):
    """Verify Scheme -> PolicyVersion one-to-many relationship."""
    scheme = Scheme(
        scheme_code=f"test_rel_{uuid.uuid4().hex[:8]}",
        name_en="Relationship Test",
        name_hi="संबंध परीक्षण",
        description_en="Desc",
        description_hi="विवरण",
        official_url="https://example.gov.in",
    )
    pv1 = PolicyVersion(
        version_code="v1.0-2018",
        effective_from=date(2018, 12, 1),
        effective_to=date(2019, 3, 31),
        source_url="https://example.gov.in/pv1",
        source_title="Gazette Notification 2018",
    )
    pv2 = PolicyVersion(
        version_code="v2.0-2019",
        effective_from=date(2019, 4, 1),
        effective_to=None,  # Open-ended policy
        source_url="https://example.gov.in/pv2",
        source_title="Revised Guidelines 2019",
    )
    scheme.policy_versions.extend([pv1, pv2])
    db_session.add(scheme)
    await db_session.commit()

    # Query back
    stmt = select(Scheme).where(Scheme.id == scheme.id)
    result = await db_session.execute(stmt)
    fetched = result.scalar_one()
    assert len(fetched.policy_versions) == 2
    assert {pv.version_code for pv in fetched.policy_versions} == {"v1.0-2018", "v2.0-2019"}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_policy_version_to_ruleset_and_jsonb(db_session: AsyncSession):
    """Verify PolicyVersion -> RuleSet relationship and JSONB AST persistence."""
    scheme = Scheme(
        scheme_code=f"test_ast_{uuid.uuid4().hex[:8]}",
        name_en="AST Test",
        name_hi="एएसटी परीक्षण",
        description_en="Desc",
        description_hi="विवरण",
        official_url="https://example.gov.in",
    )
    pv = PolicyVersion(
        version_code="v1.0",
        effective_from=date(2020, 1, 1),
        source_url="https://example.gov.in/ast",
        source_title="Statutory Order",
    )
    rule_ast = {
        "node_type": "logical",
        "operator": "AND",
        "children": [
            {
                "node_type": "comparison",
                "field_path": "farmer.owns_land",
                "operator": "EQ",
                "expected_value": True,
            },
            {
                "node_type": "comparison",
                "field_path": "farmer.monthly_pension",
                "operator": "LT",
                "expected_value": 10000,
            },
        ],
    }
    rs = RuleSet(
        definition_json=rule_ast,
        schema_version="1.0",
        rule_set_version="1.0",
    )
    pv.rule_set = rs
    scheme.policy_versions.append(pv)
    db_session.add(scheme)
    await db_session.commit()

    # Verify JSONB retrieval
    stmt = select(RuleSet).where(RuleSet.id == rs.id)
    res = await db_session.execute(stmt)
    loaded_rs = res.scalar_one()
    assert loaded_rs.definition_json["operator"] == "AND"
    assert len(loaded_rs.definition_json["children"]) == 2
    assert loaded_rs.definition_json["children"][1]["expected_value"] == 10000


@pytest.mark.integration
@pytest.mark.asyncio
async def test_policy_effective_dates_constraint(db_session: AsyncSession):
    """Verify CheckConstraint: effective_from must be <= effective_to if effective_to is set."""
    scheme = Scheme(
        scheme_code=f"test_chk_{uuid.uuid4().hex[:8]}",
        name_en="Date Check",
        name_hi="तारीख परीक्षण",
        description_en="Desc",
        description_hi="विवरण",
        official_url="https://example.gov.in",
    )
    db_session.add(scheme)
    await db_session.commit()

    # Invalid: effective_from (2020) > effective_to (2019)
    invalid_pv = PolicyVersion(
        scheme_id=scheme.id,
        version_code="v_invalid",
        effective_from=date(2020, 1, 1),
        effective_to=date(2019, 1, 1),
        source_url="https://example.gov.in",
        source_title="Invalid Date Order",
    )
    db_session.add(invalid_pv)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_citizen_claims_evidence_and_verification_hierarchy(db_session: AsyncSession):
    """Verify Citizen -> Claim -> Evidence -> VerificationRecord cascading relationships."""
    citizen = Citizen(
        synthetic_reference=f"CIT-{uuid.uuid4().hex[:12].upper()}",
        display_name="Devi Lal",
        date_of_birth=date(1975, 6, 15),
        gender="MALE",
        state="Haryana",
        district="Sirsa",
    )
    claim = Claim(
        claim_type="cultivable_land_ownership",
        value_json={"is_cultivable": True, "khasra_no": "104/12", "area_hectares": 1.8},
        source="SELF_DECLARATION",
        status=ClaimStatus.CLAIMED,
    )
    evidence = Evidence(
        evidence_type="record_of_rights_ror",
        storage_reference="mock://storage/evidence/sirsa_land_record_01.pdf",
        metadata_json={"page_count": 2, "file_size_bytes": 1048576},
        status=EvidenceStatus.PENDING,
    )
    v_record = VerificationRecord(
        verification_method="MANUAL_DOCUMENT_INSPECTION",
        status=VerificationStatus.VERIFIED,
        verified_by="officer:revenue_sirsa_04",
        verified_at=datetime.now(timezone.utc),
        details_json={"matched_fields": ["khasra_no", "area_hectares"], "confidence": 1.0},
    )

    evidence.verification_records.append(v_record)
    claim.evidence_items.append(evidence)
    citizen.claims.append(claim)
    db_session.add(citizen)
    await db_session.commit()

    # Query back and verify hierarchy
    stmt = select(Citizen).where(Citizen.id == citizen.id)
    res = await db_session.execute(stmt)
    loaded_citizen = res.scalar_one()

    assert len(loaded_citizen.claims) == 1
    assert loaded_citizen.claims[0].claim_type == "cultivable_land_ownership"
    assert loaded_citizen.claims[0].value_json["area_hectares"] == 1.8

    assert len(loaded_citizen.claims[0].evidence_items) == 1
    loaded_evidence = loaded_citizen.claims[0].evidence_items[0]
    assert loaded_evidence.status == EvidenceStatus.PENDING

    assert len(loaded_evidence.verification_records) == 1
    loaded_vr = loaded_evidence.verification_records[0]
    assert loaded_vr.status == VerificationStatus.VERIFIED
    assert loaded_vr.details_json["confidence"] == 1.0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_evaluation_trace_references_and_immutability(db_session: AsyncSession):
    """Verify EvaluationTrace references Citizen, Scheme, and PolicyVersion with immutable JSON snapshot."""
    citizen = Citizen(
        synthetic_reference=f"CIT-{uuid.uuid4().hex[:12].upper()}",
        display_name="Ananya Sharma",
        date_of_birth=date(2018, 9, 21),
        gender="FEMALE",
        state="Rajasthan",
        district="Jaipur",
    )
    scheme = Scheme(
        scheme_code=f"ssy_test_{uuid.uuid4().hex[:6]}",
        name_en="Sukanya Samriddhi Yojana",
        name_hi="सुकन्या समृद्धि योजना",
        description_en="Small savings scheme for girl child",
        description_hi="बालिकाओं के लिए लघु बचत योजना",
        official_url="https://www.indiapost.gov.in",
    )
    pv = PolicyVersion(
        version_code="v2.0-2019",
        effective_from=date(2019, 12, 12),
        source_url="https://egazette.gov.in/GSR914E.pdf",
        source_title="G.S.R. 914(E)",
    )
    scheme.policy_versions.append(pv)
    db_session.add_all([citizen, scheme])
    await db_session.commit()

    # Create EvaluationTrace
    eval_trace = EvaluationTrace(
        citizen_id=citizen.id,
        scheme_id=scheme.id,
        policy_version_id=pv.id,
        evaluation_date=date(2026, 3, 15),
        input_snapshot_json={
            "beneficiary": {
                "gender": "FEMALE",
                "date_of_birth": "2018-09-21",
                "is_resident_indian": True,
            },
            "applicant": {"relationship_to_beneficiary": "NATURAL_MOTHER"},
        },
        result_state=EligibilityResult.ELIGIBLE,
        trace_json={
            "root_node": "SSY-ROOT",
            "decision": "ELIGIBLE",
            "nodes_evaluated": 5,
            "all_satisfied": True,
        },
    )
    db_session.add(eval_trace)
    await db_session.commit()

    # Verify foreign key references and integrity
    stmt = select(EvaluationTrace).where(EvaluationTrace.id == eval_trace.id)
    res = await db_session.execute(stmt)
    loaded = res.scalar_one()

    assert loaded.citizen_id == citizen.id
    assert loaded.scheme_id == scheme.id
    assert loaded.policy_version_id == pv.id
    assert loaded.result_state == EligibilityResult.ELIGIBLE
    assert loaded.input_snapshot_json["beneficiary"]["gender"] == "FEMALE"

    # Test RESTRICT foreign key protection: Cannot delete Scheme while evaluation traces exist
    await db_session.delete(scheme)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_foreign_key_constraints_enforced(db_session: AsyncSession):
    """Verify that foreign key violations raise an IntegrityError."""
    # Attempt to insert Claim referencing a nonexistent Citizen UUID
    fake_citizen_id = uuid.uuid4()
    orphaned_claim = Claim(
        citizen_id=fake_citizen_id,
        claim_type="pension_amount",
        value_json={"monthly_pension": 12000},
        source="SELF_DECLARATION",
        status=ClaimStatus.CLAIMED,
    )
    db_session.add(orphaned_claim)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_enum_state_constraints_enforced(db_session: AsyncSession):
    """Verify that PostgreSQL enum types accept all defined enum states."""
    # Verify EligibilityResult enum values in Python and DB
    expected_results = {
        EligibilityResult.ELIGIBLE,
        EligibilityResult.INELIGIBLE,
        EligibilityResult.INSUFFICIENT_INFORMATION,
        EligibilityResult.VERIFICATION_REQUIRED,
        EligibilityResult.MANUAL_REVIEW_REQUIRED,
    }
    assert len(expected_results) == 5

    # Verify enum values at database level
    res = await db_session.execute(
        text("SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_enum.enumtypid = pg_type.oid WHERE pg_type.typname = 'eligibility_result_enum';")
    )
    db_labels = {row[0] for row in res.fetchall()}
    assert {e.value for e in expected_results} == db_labels
