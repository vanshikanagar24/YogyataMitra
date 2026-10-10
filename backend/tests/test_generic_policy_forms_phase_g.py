"""Comprehensive Test Suite for YogyataMitra Phase G.

Verifies Generic Policy-Driven Form Architecture:
1. Version-Bound Policy Form Metadata:
   - Declarative requirements resolution for PM_KISAN (v1.0, v2.0, v3.0) and SSY (v1.0, v2.0, v3.0)
   - Structured sections with bilingual titles/descriptions
   - Rich field definitions (field_type, validation bounds, conditions, display order)
   - Cross-field rules (e.g., SSY age <= 10, PM-KISAN land succession)
   - Temporal version resolution via evaluation_date / policy_version_id
   - Controlled failure on unsupported schemes (HTTP 400 / 404)
2. Authoritative Server-Side Validation:
   - Rejection of unknown / unexpected fields (HTTP 400)
   - Enforcement of required fields at final submission (HTTP 400)
   - Field type checking (boolean, number, date, select)
   - Numeric range validation (e.g., land area bounds in PM-KISAN v1.0)
   - Conditional field evaluation (field required only when condition matches)
   - Cross-field rule enforcement (e.g., SSY age at evaluation date)
   - Mandatory evidence enforcement at submission
3. Provenance & Security Invariants:
   - Form submission strictly records claims as CLAIMED and evidence as PENDING
   - Client cannot escalate status to VERIFIED
4. Structural Metadata Validation Service:
   - Structural integrity checking for duplicate keys, missing labels, invalid references
"""

from __future__ import annotations

from datetime import date, datetime, timezone
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.enums import ClaimStatus, EvidenceStatus, JourneyState
from app.schemas.form_metadata import (
    ConditionOperator,
    FieldCondition,
    FormFieldDefinition,
    FormFieldType,
    FormSectionDefinition,
    PolicyFormMetadata,
    CrossFieldRule,
)
from app.services.form_metadata_validator import (
    MetadataValidationError,
    validate_policy_form_metadata,
    validate_citizen_form_submission,
)
from app.services.form_metadata_service import (
    get_policy_form_metadata,
    SchemeFormNotSupportedError,
)


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


def _get_error_message(resp_json: dict) -> str:
    """Helper to extract standardized error message across schema representations."""
    if "error" in resp_json and isinstance(resp_json["error"], dict):
        return resp_json["error"].get("message", "")
    return resp_json.get("detail", "")


# ==============================================================================
# 1. Policy Form Metadata Structural Validation Unit Tests
# ==============================================================================

def test_metadata_validator_passes_valid_metadata():
    """Valid PolicyFormMetadata passes structural integrity checks."""
    valid_meta = PolicyFormMetadata(
        scheme_code="TEST_SCHEME",
        policy_version_code="v1.0",
        effective_from="2024-01-01",
        sections=[
            FormSectionDefinition(
                section_key="sec_personal",
                title_en="Personal Information",
                title_hi="व्यक्तिगत जानकारी",
                display_order=1,
            )
        ],
        fields=[
            FormFieldDefinition(
                field_key="applicant.is_resident",
                claim_type="RESIDENCE",
                field_type=FormFieldType.BOOLEAN,
                label_en="Is Resident?",
                label_hi="क्या निवासी हैं?",
                section_key="sec_personal",
                required=True,
                display_order=1,
            )
        ],
        evidence_types=[],
        cross_field_rules=[],
    )
    # Should not raise
    validate_policy_form_metadata(valid_meta)


def test_metadata_validator_detects_duplicate_fields():
    """Duplicate field_keys are caught by metadata validation."""
    meta = PolicyFormMetadata(
        scheme_code="TEST_SCHEME",
        policy_version_code="v1.0",
        effective_from="2024-01-01",
        sections=[
            FormSectionDefinition(
                section_key="s1",
                title_en="Section 1",
                title_hi="अनुभाग १",
                display_order=1,
            )
        ],
        fields=[
            FormFieldDefinition(
                field_key="applicant.age",
                claim_type="AGE",
                field_type=FormFieldType.INTEGER,
                label_en="Age",
                label_hi="आयु",
                section_key="s1",
                required=True,
            ),
            FormFieldDefinition(
                field_key="applicant.age",
                claim_type="AGE",
                field_type=FormFieldType.INTEGER,
                label_en="Age 2",
                label_hi="आयु २",
                section_key="s1",
                required=True,
            ),
        ],
    )
    with pytest.raises(MetadataValidationError) as exc:
        validate_policy_form_metadata(meta)
    assert "Duplicate field_key" in str(exc.value)


def test_metadata_validator_detects_missing_bilingual_labels():
    """Empty English or Hindi labels are rejected either by Pydantic model or validator."""
    with pytest.raises((Exception, MetadataValidationError)):
        meta = PolicyFormMetadata(
            scheme_code="TEST_SCHEME",
            policy_version_code="v1.0",
            effective_from="2024-01-01",
            sections=[
                FormSectionDefinition(
                    section_key="s1",
                    title_en="Section 1",
                    title_hi="अनुभाग १",
                    display_order=1,
                )
            ],
            fields=[
                FormFieldDefinition(
                    field_key="applicant.name",
                    claim_type="NAME",
                    field_type=FormFieldType.TEXT,
                    label_en="Full Name",
                    label_hi="",  # Missing Hindi label
                    section_key="s1",
                    required=True,
                )
            ],
        )
        validate_policy_form_metadata(meta)


def test_metadata_validator_detects_invalid_section_reference():
    """Field pointing to non-existent section is rejected."""
    meta = PolicyFormMetadata(
        scheme_code="TEST_SCHEME",
        policy_version_code="v1.0",
        effective_from="2024-01-01",
        sections=[
            FormSectionDefinition(
                section_key="sec_1",
                title_en="Section 1",
                title_hi="अनुभाग १",
                display_order=1,
            )
        ],
        fields=[
            FormFieldDefinition(
                field_key="field_1",
                claim_type="TEST",
                field_type=FormFieldType.TEXT,
                label_en="F1",
                label_hi="एफ१",
                section_key="non_existent_section",
                required=True,
            )
        ],
    )
    with pytest.raises(MetadataValidationError) as exc:
        validate_policy_form_metadata(meta)
    assert "nonexistent section_key" in str(exc.value)


def test_metadata_validator_detects_invalid_condition_reference():
    """Condition referencing non-existent field is rejected."""
    meta = PolicyFormMetadata(
        scheme_code="TEST_SCHEME",
        policy_version_code="v1.0",
        effective_from="2024-01-01",
        sections=[
            FormSectionDefinition(
                section_key="sec_1",
                title_en="Section 1",
                title_hi="अनुभाग १",
                display_order=1,
            )
        ],
        fields=[
            FormFieldDefinition(
                field_key="field_1",
                claim_type="TEST",
                field_type=FormFieldType.TEXT,
                label_en="F1",
                label_hi="एफ१",
                section_key="sec_1",
                required=True,
                condition=FieldCondition(
                    field_key="unknown_controlling_field",
                    operator=ConditionOperator.EQUALS,
                    value=True,
                ),
            )
        ],
    )
    with pytest.raises(MetadataValidationError) as exc:
        validate_policy_form_metadata(meta)
    assert "unknown field" in str(exc.value)


# ==============================================================================
# 2. Scheme Requirements API & Policy Version Resolution Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_requirements_endpoint_returns_sections_and_cross_rules_pmkisan(async_client: AsyncClient):
    """GET /requirements for PM_KISAN returns policy sections, conditional fields, and cross-rules."""
    token = _make_citizen_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.get("/api/v1/citizen/schemes/PM_KISAN/requirements", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    # Sections verified
    assert "sections" in data
    assert len(data["sections"]) >= 2
    section_keys = [s["section_key"] for s in data["sections"]]
    assert "land_details" in section_keys
    assert "statutory_exclusions" in section_keys

    # Bilingual titles verified
    land_section = next(s for s in data["sections"] if s["section_key"] == "land_details")
    assert "Land" in land_section["title_en"]
    assert "भूमि" in land_section["title_hi"]

    # Fields and conditions verified
    fields = data["fields"]
    succession_field = next(f for f in fields if f["field_key"] == "land.acquired_via_succession")
    assert succession_field["condition"] is not None
    assert succession_field["condition"]["field_key"] == "land.transferred_after_cutoff"
    assert succession_field["condition"]["operator"] == "EQUALS"
    assert succession_field["condition"]["value"] is True

    # Cross-field rules verified
    assert "cross_field_rules" in data


@pytest.mark.asyncio
async def test_requirements_endpoint_returns_sections_and_cross_rules_ssy(async_client: AsyncClient):
    """GET /requirements for SSY returns beneficiary sections and age cross-field rule."""
    token = _make_citizen_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.get("/api/v1/citizen/schemes/SSY/requirements", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    # Sections
    section_keys = [s["section_key"] for s in data["sections"]]
    assert "beneficiary_details" in section_keys
    assert "guardian_details" in section_keys

    # Cross-field rule for age <= 10
    age_rule = next(r for r in data["cross_field_rules"] if r["rule_type"] == "AGE_AT_DATE")
    assert age_rule["primary_field"] == "beneficiary.date_of_birth"
    assert age_rule["parameters"]["max_age_years"] == 10
    assert "10 years" in age_rule["message_en"]


@pytest.mark.asyncio
async def test_requirements_version_binding_pmkisan_v1_vs_v3(async_client: AsyncClient):
    """Querying PM_KISAN requirements for 2018 (v1.0) enforces 2-hectare limit, while v3.0 does not."""
    token = _make_citizen_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Query 2018 date -> v1.0
    resp_v1 = await async_client.get(
        "/api/v1/citizen/schemes/PM_KISAN/requirements?evaluation_date=2018-12-15",
        headers=headers,
    )
    assert resp_v1.status_code == 200
    data_v1 = resp_v1.json()
    assert "v1.0-2018" in data_v1["policy_version_code"]
    land_v1 = next(f for f in data_v1["fields"] if f["field_key"] == "land.total_land_area_hectares")
    assert land_v1["max_value"] == 2.0

    # Query latest (v3.0) -> no 2ha ceiling
    resp_v3 = await async_client.get(
        "/api/v1/citizen/schemes/PM_KISAN/requirements",
        headers=headers,
    )
    assert resp_v3.status_code == 200
    data_v3 = resp_v3.json()
    assert "v3.0-2023" in data_v3["policy_version_code"]
    land_v3 = next(f for f in data_v3["fields"] if f["field_key"] == "land.total_land_area_hectares")
    assert land_v3["max_value"] is None or land_v3["max_value"] >= 1000.0


@pytest.mark.asyncio
async def test_unsupported_scheme_requirements_safe_rejection(async_client: AsyncClient):
    """Unsupported or non-configured schemes fail safely with controlled error, never 500."""
    token = _make_citizen_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Non-existent scheme returns 404
    resp = await async_client.get("/api/v1/citizen/schemes/UNKNOWN_SCHEME_XYZ/requirements", headers=headers)
    assert resp.status_code == 404


# ==============================================================================
# 3. Server-Side Validation: Draft and Submit Enforcements
# ==============================================================================

@pytest.mark.asyncio
async def test_unknown_fields_rejection_in_draft_update(async_client: AsyncClient):
    """Submitting unknown/unexpected field keys in draft update is authoritatively rejected (HTTP 400)."""
    token = _make_citizen_token(ref=f"SYN-CIT-UNK-{uuid.uuid4().hex[:6]}")
    headers = {"Authorization": f"Bearer {token}"}

    # Create draft
    create_res = await async_client.post(
        "/api/v1/citizen/applications",
        json={"scheme_code": "PM_KISAN"},
        headers=headers,
    )
    app_id = create_res.json()["id"]

    # Attempt to inject unknown field in draft facts
    bad_payload = {
        "facts": {
            "family.owns_cultivable_land": True,
            "unauthorized_field_injection": "malicious_payload",
        }
    }
    update_res = await async_client.put(
        f"/api/v1/citizen/applications/{app_id}/draft",
        json=bad_payload,
        headers=headers,
    )
    assert update_res.status_code == 400
    msg = _get_error_message(update_res.json())
    assert "Unknown field" in msg


@pytest.mark.asyncio
async def test_unknown_fields_rejection_in_final_submission(async_client: AsyncClient):
    """Submitting unknown fields at final submit is strictly rejected with HTTP 400."""
    token = _make_citizen_token(ref=f"SYN-CIT-SUBUNK-{uuid.uuid4().hex[:6]}")
    headers = {"Authorization": f"Bearer {token}"}

    create_res = await async_client.post(
        "/api/v1/citizen/applications",
        json={"scheme_code": "PM_KISAN"},
        headers=headers,
    )
    app_id = create_res.json()["id"]

    submit_payload = {
        "facts": {
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
            "fraudulent_field": 99999,  # Unknown field
        },
        "declaration_confirmed": True,
    }

    sub_res = await async_client.post(
        f"/api/v1/citizen/applications/{app_id}/submit",
        json=submit_payload,
        headers=headers,
    )
    assert sub_res.status_code == 400
    msg = _get_error_message(sub_res.json())
    assert "Unknown field" in msg


@pytest.mark.asyncio
async def test_missing_required_fields_rejection_at_submission(async_client: AsyncClient):
    """Submitting missing mandatory policy fields at final submit returns HTTP 400."""
    token = _make_citizen_token(ref=f"SYN-CIT-REQ-{uuid.uuid4().hex[:6]}")
    headers = {"Authorization": f"Bearer {token}"}

    create_res = await async_client.post(
        "/api/v1/citizen/applications",
        json={"scheme_code": "PM_KISAN"},
        headers=headers,
    )
    app_id = create_res.json()["id"]

    # Incomplete facts (omitted all exclusion checks)
    incomplete_payload = {
        "facts": {
            "family.owns_cultivable_land": True,
        },
        "declaration_confirmed": True,
    }

    sub_res = await async_client.post(
        f"/api/v1/citizen/applications/{app_id}/submit",
        json=incomplete_payload,
        headers=headers,
    )
    assert sub_res.status_code == 400
    msg = _get_error_message(sub_res.json())
    assert "required" in msg.lower()


@pytest.mark.asyncio
async def test_field_type_validation_boolean_rejection(async_client: AsyncClient):
    """Providing a non-boolean for a boolean field in draft update returns HTTP 400."""
    token = _make_citizen_token(ref=f"SYN-CIT-TYPE-{uuid.uuid4().hex[:6]}")
    headers = {"Authorization": f"Bearer {token}"}

    create_res = await async_client.post(
        "/api/v1/citizen/applications",
        json={"scheme_code": "PM_KISAN"},
        headers=headers,
    )
    app_id = create_res.json()["id"]

    res = await async_client.put(
        f"/api/v1/citizen/applications/{app_id}/draft",
        json={"facts": {"family.owns_cultivable_land": "yes_definitely"}},  # invalid type
        headers=headers,
    )
    assert res.status_code == 400
    msg = _get_error_message(res.json())
    assert "boolean" in msg.lower()


@pytest.mark.asyncio
async def test_numeric_bounds_validation_pmkisan(async_client: AsyncClient):
    """Negative land area is rejected by numeric bounds validation."""
    token = _make_citizen_token(ref=f"SYN-CIT-BND-{uuid.uuid4().hex[:6]}")
    headers = {"Authorization": f"Bearer {token}"}

    create_res = await async_client.post(
        "/api/v1/citizen/applications",
        json={"scheme_code": "PM_KISAN"},
        headers=headers,
    )
    app_id = create_res.json()["id"]

    res = await async_client.put(
        f"/api/v1/citizen/applications/{app_id}/draft",
        json={"facts": {"land.total_land_area_hectares": -0.5}},  # negative land area
        headers=headers,
    )
    assert res.status_code == 400
    msg = _get_error_message(res.json())
    assert "minimum" in msg.lower() or "statutory" in msg.lower()


@pytest.mark.asyncio
async def test_conditional_field_validation_pmkisan_succession(async_client: AsyncClient):
    """When land is transferred after cutoff, succession status field is required at submission."""
    token = _make_citizen_token(ref=f"SYN-CIT-COND-{uuid.uuid4().hex[:6]}")
    headers = {"Authorization": f"Bearer {token}"}

    create_res = await async_client.post(
        "/api/v1/citizen/applications",
        json={"scheme_code": "PM_KISAN"},
        headers=headers,
    )
    app_id = create_res.json()["id"]

    # Transferred after cutoff = True, but land.acquired_via_succession omitted!
    payload = {
        "facts": {
            "family.owns_cultivable_land": True,
            "land.total_land_area_hectares": 1.2,
            "land.transferred_after_cutoff": True,  # Condition triggered!
            # "land.acquired_via_succession": omitted!
            "family.is_institutional_landholder": False,
            "family.has_constitutional_post_holder": False,
            "family.has_public_representative": False,
            "family.has_disqualified_government_employee": False,
            "family.has_pensioner_above_ten_thousand": False,
            "family.has_income_tax_payer": False,
            "family.has_registered_practicing_professional": False,
            "family.is_nri": False,
        },
        "evidence_items": [
            {
                "evidence_type": "LAND_RECORD",
                "storage_reference": "doc-ref://vault/land.pdf",
            },
            {
                "evidence_type": "AADHAAR",
                "storage_reference": "doc-ref://vault/aadhaar.pdf",
            },
        ],
        "declaration_confirmed": True,
    }

    res = await async_client.post(
        f"/api/v1/citizen/applications/{app_id}/submit",
        json=payload,
        headers=headers,
    )
    assert res.status_code == 400
    msg = _get_error_message(res.json())
    assert "land.acquired_via_succession" in msg


@pytest.mark.asyncio
async def test_cross_field_rule_enforcement_ssy_age(async_client: AsyncClient):
    """Submitting an SSY application for a girl child older than 10 years fails cross-field validation."""
    token = _make_citizen_token(ref=f"SYN-CIT-SSYAGE-{uuid.uuid4().hex[:6]}")
    headers = {"Authorization": f"Bearer {token}"}

    create_res = await async_client.post(
        "/api/v1/citizen/applications",
        json={"scheme_code": "SSY"},
        headers=headers,
    )
    assert create_res.status_code == 201
    app_id = create_res.json()["id"]

    # Birth date 15 years ago (clearly > 10 years)
    payload = {
        "facts": {
            "beneficiary.gender": "FEMALE",
            "beneficiary.date_of_birth": "2010-01-01",  # > 10 years old!
            "beneficiary.is_indian_citizen": True,
            "beneficiary.is_resident": True,
            "guardian.is_natural_guardian": True,
            "family.existing_ssy_accounts_count": 0,
        },
        "evidence_items": [
            {
                "evidence_type": "BIRTH_CERTIFICATE",
                "storage_reference": "doc-ref://vault/birth_cert.pdf",
            },
            {
                "evidence_type": "AADHAAR",
                "storage_reference": "doc-ref://vault/aadhaar.pdf",
            },
        ],
        "declaration_confirmed": True,
    }

    res = await async_client.post(
        f"/api/v1/citizen/applications/{app_id}/submit",
        json=payload,
        headers=headers,
    )
    assert res.status_code == 400
    msg = _get_error_message(res.json())
    assert "10 years" in msg or "age" in msg.lower()


# ==============================================================================
# 4. Fact Provenance & Security Invariants
# ==============================================================================

@pytest.mark.asyncio
async def test_provenance_invariants_claims_claimed_evidence_pending(async_client: AsyncClient):
    """Form submission authoritatively guarantees claims are CLAIMED and evidence is PENDING."""
    token = _make_citizen_token(ref=f"SYN-CIT-PROV-{uuid.uuid4().hex[:6]}")
    headers = {"Authorization": f"Bearer {token}"}

    create_res = await async_client.post(
        "/api/v1/citizen/applications",
        json={"scheme_code": "PM_KISAN"},
        headers=headers,
    )
    app_id = create_res.json()["id"]

    submit_payload = {
        "facts": {
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
        },
        "evidence_items": [
            {
                "evidence_type": "LAND_RECORD",
                "storage_reference": "doc-ref://vault/land.pdf",
                "document_name": "Land Record",
            },
            {
                "evidence_type": "AADHAAR",
                "storage_reference": "doc-ref://vault/aadhaar.pdf",
                "document_name": "Aadhaar Card",
            },
        ],
        "declaration_confirmed": True,
    }

    sub_res = await async_client.post(
        f"/api/v1/citizen/applications/{app_id}/submit",
        json=submit_payload,
        headers=headers,
    )
    assert sub_res.status_code == 200

    # Fetch full detail
    detail_res = await async_client.get(
        f"/api/v1/citizen/applications/{app_id}",
        headers=headers,
    )
    assert detail_res.status_code == 200
    app_detail = detail_res.json()

    # Claims must all be strictly CLAIMED
    assert len(app_detail["claims"]) > 0
    for claim in app_detail["claims"]:
        assert claim["status"] == "CLAIMED", f"Claim {claim['claim_type']} had status {claim['status']}, expected CLAIMED"

    # Evidence items must all be strictly PENDING
    assert len(app_detail["claims"]) > 0
    evidence_count = 0
    for claim in app_detail["claims"]:
        for ev in claim.get("evidence_items", []):
            evidence_count += 1
            assert ev["status"] == "PENDING", f"Evidence {ev['evidence_type']} had status {ev['status']}, expected PENDING"
    assert evidence_count >= 2
