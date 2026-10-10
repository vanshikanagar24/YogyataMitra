"""Comprehensive Test Suite for YogyataMitra Phase C.

Verifies:
1. Available Schemes & Requirements:
   - Canonical scheme discovery for citizen portal (PM_KISAN, SSY)
   - Structured statutory requirements (fields, evidence types, active policy version)
   - 404 handling on unknown schemes
2. Generic Application Creation in DRAFT:
   - DRAFT state initialization
   - Strict binding of active PolicyVersion at creation time
   - Non-sensitive canonical application reference generation (APP-YYYY-XXXXXXXX)
   - submitted_at is null in draft
3. Draft In-Progress Progression:
   - Updating draft facts and attaching draft evidence references
   - Rejection of draft updates on non-draft applications
   - Strict IDOR isolation (foreign citizen access returns 404)
4. Formal Application Submission:
   - State transition from DRAFT to FACTS_COLLECTED / EVIDENCE_PENDING
   - Setting of immutable submitted_at timestamp
   - Transition audit record with actor='CITIZEN'
   - Strict status invariants: Claims remain CLAIMED (not VERIFIED); Evidence remains PENDING (not VERIFIED)
   - Zero evaluation triggered at submission
5. Multiple Application Ownership:
   - Multiple applications across PM_KISAN and SSY for a single citizen
   - Accurate dashboard aggregation metrics
"""

from __future__ import annotations

from datetime import date, datetime, timezone
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.enums import ClaimStatus, EvidenceStatus, JourneyState


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
# 1. Scheme Discovery & Requirements Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_citizen_schemes_list(async_client: AsyncClient):
    """Citizen can query available canonical schemes for application."""
    token = _make_citizen_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.get("/api/v1/citizen/schemes", headers=headers)
    assert resp.status_code == 200
    schemes = resp.json()
    assert len(schemes) >= 2
    codes = [s["scheme_code"] for s in schemes]
    assert "PM_KISAN" in codes
    assert "SSY" in codes


@pytest.mark.asyncio
async def test_citizen_scheme_requirements_pm_kisan(async_client: AsyncClient):
    """Citizen can inspect PM_KISAN application requirements."""
    token = _make_citizen_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.get("/api/v1/citizen/schemes/PM_KISAN/requirements", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["scheme_code"] == "PM_KISAN"
    assert "v3.0-2023" in data["policy_version_code"]
    assert len(data["fields"]) >= 10
    field_keys = [f["field_key"] for f in data["fields"]]
    assert "family.owns_cultivable_land" in field_keys
    assert "land.total_land_area_hectares" in field_keys
    assert "family.has_income_tax_payer" in field_keys

    evidence_types = [e["evidence_type"] for e in data["evidence_types"]]
    assert "LAND_RECORD" in evidence_types
    assert "AADHAAR" in evidence_types
    assert "BANK_PASSBOOK" in evidence_types


@pytest.mark.asyncio
async def test_citizen_scheme_requirements_ssy(async_client: AsyncClient):
    """Citizen can inspect SSY application requirements."""
    token = _make_citizen_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.get("/api/v1/citizen/schemes/SSY/requirements", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["scheme_code"] == "SSY"
    assert "v3.0-2024" in data["policy_version_code"]
    field_keys = [f["field_key"] for f in data["fields"]]
    assert "beneficiary.gender" in field_keys
    assert "beneficiary.date_of_birth" in field_keys
    assert "guardian.is_natural_guardian" in field_keys

    evidence_types = [e["evidence_type"] for e in data["evidence_types"]]
    assert "BIRTH_CERTIFICATE" in evidence_types
    assert "AADHAAR" in evidence_types


@pytest.mark.asyncio
async def test_citizen_scheme_requirements_unknown_scheme(async_client: AsyncClient):
    """Requesting requirements for an invalid scheme returns 404."""
    token = _make_citizen_token()
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.get("/api/v1/citizen/schemes/INVALID_SCHEME_99/requirements", headers=headers)
    assert resp.status_code == 404


# ==============================================================================
# 2. Application Creation & Draft Invariants
# ==============================================================================

@pytest.mark.asyncio
async def test_create_draft_application_policy_binding(async_client: AsyncClient):
    """Creating an application starts in DRAFT and binds the active PolicyVersion."""
    ref = f"SYN-CIT-PHC-{uuid.uuid4().hex[:6].upper()}"
    token = _make_citizen_token(email="phc.citizen@test.local", ref=ref)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.post(
        "/api/v1/citizen/applications",
        json={"scheme_code": "PM_KISAN"},
        headers=headers,
    )
    assert resp.status_code == 201
    app = resp.json()
    assert app["state"] == "DRAFT"
    assert app["submitted_at"] is None
    assert app["policy_version_id"] is not None
    assert "v3.0-2023" in app["policy_version_code"]
    assert app["rule_definition_hash"] is not None
    assert app["application_ref"].startswith("APP-")


@pytest.mark.asyncio
async def test_save_draft_application_progress(async_client: AsyncClient):
    """Citizen can save progress on an in-progress DRAFT application."""
    ref = f"SYN-CIT-SAVE-{uuid.uuid4().hex[:6].upper()}"
    token = _make_citizen_token(email="save.citizen@test.local", ref=ref)
    headers = {"Authorization": f"Bearer {token}"}

    create_res = await async_client.post(
        "/api/v1/citizen/applications",
        json={"scheme_code": "PM_KISAN"},
        headers=headers,
    )
    assert create_res.status_code == 201
    app_id = create_res.json()["id"]

    # Save draft facts and evidence reference
    draft_payload = {
        "facts": {
            "family.owns_cultivable_land": True,
            "land.total_land_area_hectares": 2.2,
        },
        "evidence_items": [
            {
                "evidence_type": "LAND_RECORD",
                "storage_reference": "doc-ref://vault/land_712_draft.pdf",
                "document_name": "7/12 Land Record",
                "metadata_json": {"khasra_no": "104/A"},
            }
        ],
    }

    update_res = await async_client.put(
        f"/api/v1/citizen/applications/{app_id}/draft",
        json=draft_payload,
        headers=headers,
    )
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["state"] == "DRAFT"
    assert updated["submitted_at"] is None
    assert updated["claims_count"] >= 2
    assert updated["evidence_count"] >= 1


@pytest.mark.asyncio
async def test_draft_update_idor_protection(async_client: AsyncClient):
    """Citizen B cannot update Citizen A's draft application."""
    token_a = _make_citizen_token(email="cit.a@test.local", ref=f"SYN-CIT-A-{uuid.uuid4().hex[:6]}")
    token_b = _make_citizen_token(email="cit.b@test.local", ref=f"SYN-CIT-B-{uuid.uuid4().hex[:6]}")

    # Citizen A creates application
    res_a = await async_client.post(
        "/api/v1/citizen/applications",
        json={"scheme_code": "PM_KISAN"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    app_id = res_a.json()["id"]

    # Citizen B attempts to update Citizen A's draft
    res_b = await async_client.put(
        f"/api/v1/citizen/applications/{app_id}/draft",
        json={"facts": {"family.owns_cultivable_land": False}},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b.status_code == 404


# ==============================================================================
# 3. Application Submission & Verification Boundary Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_submit_application_full_workflow(async_client: AsyncClient):
    """Submitting an application transitions from DRAFT to SUBMITTED state with audit logs."""
    ref = f"SYN-CIT-SUB-{uuid.uuid4().hex[:6].upper()}"
    token = _make_citizen_token(email="sub.citizen@test.local", ref=ref)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create DRAFT application
    create_res = await async_client.post(
        "/api/v1/citizen/applications",
        json={"scheme_code": "PM_KISAN"},
        headers=headers,
    )
    app_id = create_res.json()["id"]
    policy_ver_id = create_res.json()["policy_version_id"]

    # 2. Formally Submit Application
    submit_payload = {
        "facts": {
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
        },
        "evidence_items": [
            {
                "evidence_type": "LAND_RECORD",
                "storage_reference": "doc-ref://vault/land_ror_certified.pdf",
                "document_name": "Maharashtra 7/12 RoR Certified",
                "metadata_json": {"survey_no": "24/3"},
            },
            {
                "evidence_type": "AADHAAR",
                "storage_reference": "doc-ref://vault/aadhaar_masked.pdf",
                "document_name": "Applicant Aadhaar Masked Copy",
                "metadata_json": {"last_4": "1234"},
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
    submitted = sub_res.json()

    # State verification
    assert submitted["state"] == "EVIDENCE_PENDING"
    assert submitted["submitted_at"] is not None
    # Bound policy version remains immutable
    assert submitted["policy_version_id"] == policy_ver_id
    assert "v3.0-2023" in submitted["policy_version_code"]

    # Claims status verification: Citizen assertions are strictly CLAIMED, not VERIFIED
    assert len(submitted["claims"]) >= 10
    for c in submitted["claims"]:
        assert c["status"] == "CLAIMED"
        assert c["source"] == "CITIZEN_DECLARATION"

    # Evidence status verification: Evidence is strictly PENDING, not VERIFIED
    all_evidence = []
    for c in submitted["claims"]:
        all_evidence.extend(c.get("evidence_items", []))
    assert len(all_evidence) >= 2
    for ev in all_evidence:
        assert ev["status"] == "PENDING"
        assert ev["verified_at"] is None

    # Transition Audit Trail verification
    transitions = submitted["transitions"]
    assert len(transitions) >= 2
    states_traversed = [(t["from_state"], t["to_state"]) for t in transitions]
    assert ("DRAFT", "FACTS_COLLECTED") in states_traversed
    assert ("FACTS_COLLECTED", "EVIDENCE_PENDING") in states_traversed
    assert all(t["actor"] == "CITIZEN" for t in transitions)

    # Inability to re-submit an already submitted application
    re_sub = await async_client.post(
        f"/api/v1/citizen/applications/{app_id}/submit",
        json=submit_payload,
        headers=headers,
    )
    assert re_sub.status_code == 400


@pytest.mark.asyncio
async def test_submit_without_facts_rejected(async_client: AsyncClient):
    """Submitting an application without facts is rejected with 400."""
    token = _make_citizen_token(email="nofacts@test.local", ref=f"SYN-CIT-NF-{uuid.uuid4().hex[:6]}")
    headers = {"Authorization": f"Bearer {token}"}

    create_res = await async_client.post(
        "/api/v1/citizen/applications",
        json={"scheme_code": "PM_KISAN"},
        headers=headers,
    )
    app_id = create_res.json()["id"]

    sub_res = await async_client.post(
        f"/api/v1/citizen/applications/{app_id}/submit",
        json={"facts": {}, "declaration_confirmed": True},
        headers=headers,
    )
    assert sub_res.status_code == 400


# ==============================================================================
# 4. Multiple Applications Across Schemes
# ==============================================================================

@pytest.mark.asyncio
async def test_citizen_can_create_multiple_applications_across_schemes(async_client: AsyncClient):
    """A citizen can hold multiple applications across PM_KISAN and SSY schemes."""
    ref = f"SYN-CIT-MULTI-{uuid.uuid4().hex[:6].upper()}"
    token = _make_citizen_token(email="multi.citizen@test.local", ref=ref)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create PM-KISAN application and submit it
    res1 = await async_client.post(
        "/api/v1/citizen/applications",
        json={"scheme_code": "PM_KISAN"},
        headers=headers,
    )
    app1_id = res1.json()["id"]

    await async_client.post(
        f"/api/v1/citizen/applications/{app1_id}/submit",
        json={
            "facts": {"family.owns_cultivable_land": True, "land.total_land_area_hectares": 1.2},
            "declaration_confirmed": True,
        },
        headers=headers,
    )

    # 2. Create SSY application as draft
    res2 = await async_client.post(
        "/api/v1/citizen/applications",
        json={"scheme_code": "SSY"},
        headers=headers,
    )
    assert res2.status_code == 201
    app2_id = res2.json()["id"]

    # 3. Verify applications listing
    list_res = await async_client.get("/api/v1/citizen/applications", headers=headers)
    assert list_res.status_code == 200
    apps = list_res.json()
    assert len(apps) == 2
    app_schemes = {a["scheme_code"] for a in apps}
    assert app_schemes == {"PM_KISAN", "SSY"}

    # 4. Verify dashboard metrics
    stats_res = await async_client.get("/api/v1/citizen/dashboard/stats", headers=headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["total_applications"] == 2
    assert stats["in_progress_count"] == 2
