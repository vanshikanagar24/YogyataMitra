"""Tests for Phase B Citizen Applications and Dashboard API.

Verifies:
1. Unauthenticated requests are rejected (401).
2. Officer tokens are rejected on citizen endpoints (403 role boundary).
3. Zero-application state for new citizen.
4. Multiple applications across schemes for a single citizen.
5. Strict IDOR protection: Cross-citizen application access returns 404.
6. Application detail with claims, evidence items, and state transitions.
7. Dashboard summary aggregates (total, in_progress, evaluated, action_required).
8. Dynamic in-portal application initiation (POST /citizen/applications).
9. Invalid scheme code handling (404).
"""

from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.citizen import Citizen, Claim, Evidence
from app.models.enums import ClaimStatus, EvidenceStatus, JourneyState
from app.models.journey import EvaluationJourney, JourneyTransitionRecord
from app.models.scheme import Scheme


def _make_citizen_token(
    email: str = "citizen.test@yogyatamitra.local",
    ref: str = "SYN-CIT-DEMO0001",
    name: str = "Demo Citizen",
) -> str:
    return create_access_token(
        data={
            "sub": email,
            "role": "CITIZEN",
            "name": name,
            "citizen_ref": ref,
            "state": "Uttar Pradesh",
            "district": "Varanasi",
        }
    )


def _make_officer_token() -> str:
    return create_access_token(
        data={
            "sub": "officer.varanasi@yogyatamitra.gov.in",
            "role": "OFFICER",
            "name": "Officer Sharma",
            "designation": "Welfare Verification Officer",
            "department": "Agriculture & Farmers Welfare",
        }
    )


def _get_error_message(resp_json: dict) -> str:
    if "error" in resp_json and isinstance(resp_json["error"], dict):
        return resp_json["error"].get("message", "")
    return resp_json.get("detail", "")


@pytest.mark.asyncio
async def test_unauthenticated_applications_rejected(async_client: AsyncClient):
    """Accessing citizen applications without token must return 401."""
    resp = await async_client.get("/api/v1/citizen/applications")
    assert resp.status_code == 401
    assert _get_error_message(resp.json()) != ""


@pytest.mark.asyncio
async def test_officer_token_rejected_from_citizen_applications(async_client: AsyncClient):
    """Accessing citizen applications with Officer token must return 403."""
    officer_token = _make_officer_token()
    headers = {"Authorization": f"Bearer {officer_token}"}
    resp = await async_client.get("/api/v1/citizen/applications", headers=headers)
    assert resp.status_code == 403
    assert "Access forbidden" in _get_error_message(resp.json())


@pytest.mark.asyncio
async def test_empty_applications_for_new_citizen(async_client: AsyncClient, db_session: AsyncSession):
    """A fresh citizen with no journeys returns empty list and zero stats."""
    unique_ref = f"SYN-CIT-EMPTY-{uuid.uuid4().hex[:6].upper()}"
    token = _make_citizen_token(email="new.citizen@test.local", ref=unique_ref)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Check applications
    resp = await async_client.get("/api/v1/citizen/applications", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []

    # 2. Check dashboard stats
    stats_resp = await async_client.get("/api/v1/citizen/dashboard/stats", headers=headers)
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["total_applications"] == 0
    assert stats["in_progress_count"] == 0
    assert stats["evaluated_count"] == 0
    assert stats["recent_applications"] == []


@pytest.mark.asyncio
async def test_multiple_applications_across_schemes(async_client: AsyncClient, db_session: AsyncSession):
    """A single citizen can hold MULTIPLE applications across schemes."""
    unique_ref = f"SYN-CIT-MULTI-{uuid.uuid4().hex[:6].upper()}"
    token = _make_citizen_token(email="multi.citizen@test.local", ref=unique_ref)
    headers = {"Authorization": f"Bearer {token}"}

    # Create citizen in DB
    db_citizen = Citizen(
        synthetic_reference=unique_ref,
        display_name="Multi Application Citizen",
        state="Bihar",
        district="Patna",
    )
    db_session.add(db_citizen)
    await db_session.flush()

    # Get PM_KISAN and SSY schemes
    res = await db_session.execute(select(Scheme).where(Scheme.scheme_code.in_(["PM_KISAN", "SSY"])))
    schemes = {s.scheme_code: s for s in res.scalars().all()}
    assert "PM_KISAN" in schemes, "PM_KISAN scheme must exist"
    assert "SSY" in schemes, "SSY scheme must exist"

    # Application 1: PM_KISAN
    j1 = EvaluationJourney(
        citizen_id=db_citizen.id,
        scheme_id=schemes["PM_KISAN"].id,
        state=JourneyState.VERIFICATION_IN_PROGRESS,
    )
    # Application 2: SSY
    j2 = EvaluationJourney(
        citizen_id=db_citizen.id,
        scheme_id=schemes["SSY"].id,
        state=JourneyState.DRAFT,
    )
    db_session.add_all([j1, j2])
    await db_session.commit()

    # Query API
    resp = await async_client.get("/api/v1/citizen/applications", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2

    scheme_codes = {app["scheme_code"] for app in data}
    assert "PM_KISAN" in scheme_codes
    assert "SSY" in scheme_codes

    # Verify application reference formatting
    for app in data:
        assert app["application_ref"].startswith("APP-")
        assert len(app["application_ref"]) > 10
        assert app["status_label_en"] is not None
        assert app["status_label_hi"] is not None


@pytest.mark.asyncio
async def test_strict_idor_protection(async_client: AsyncClient, db_session: AsyncSession):
    """Citizen B MUST NOT be able to view or fetch Citizen A's application."""
    ref_a = f"SYN-CIT-A-{uuid.uuid4().hex[:6].upper()}"
    ref_b = f"SYN-CIT-B-{uuid.uuid4().hex[:6].upper()}"

    token_b = _make_citizen_token(email="citizen.b@test.local", ref=ref_b, name="Citizen B")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Create Citizen A and B in DB
    cit_a = Citizen(synthetic_reference=ref_a, display_name="Citizen A")
    cit_b = Citizen(synthetic_reference=ref_b, display_name="Citizen B")
    db_session.add_all([cit_a, cit_b])
    await db_session.flush()

    res = await db_session.execute(select(Scheme).where(Scheme.scheme_code == "PM_KISAN"))
    pm_kisan = res.scalar_one()

    # Create journey owned by Citizen A
    journey_a = EvaluationJourney(
        citizen_id=cit_a.id,
        scheme_id=pm_kisan.id,
        state=JourneyState.FACTS_COLLECTED,
    )
    db_session.add(journey_a)
    await db_session.commit()

    # Citizen B tries to access Citizen A's journey detail
    idor_resp = await async_client.get(
        f"/api/v1/citizen/applications/{journey_a.id}",
        headers=headers_b,
    )
    # Must return 404 Not Found (not 403 or 200) to prevent IDOR and enumeration
    assert idor_resp.status_code == 404
    assert "not found" in _get_error_message(idor_resp.json()).lower()

    # Citizen B's application listing does not include Citizen A's journey
    list_resp = await async_client.get("/api/v1/citizen/applications", headers=headers_b)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 0


@pytest.mark.asyncio
async def test_citizen_application_detail_with_claims_and_evidence(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Detail endpoint returns comprehensive application dossier with claims, evidence, and audit trail."""
    ref = f"SYN-CIT-DET-{uuid.uuid4().hex[:6].upper()}"
    token = _make_citizen_token(email="detail.citizen@test.local", ref=ref)
    headers = {"Authorization": f"Bearer {token}"}

    cit = Citizen(synthetic_reference=ref, display_name="Detail Citizen")
    db_session.add(cit)
    await db_session.flush()

    res = await db_session.execute(select(Scheme).where(Scheme.scheme_code == "PM_KISAN"))
    scheme = res.scalar_one()

    journey = EvaluationJourney(
        citizen_id=cit.id,
        scheme_id=scheme.id,
        state=JourneyState.VERIFICATION_IN_PROGRESS,
    )
    db_session.add(journey)
    await db_session.flush()

    # Add a transition
    t1 = JourneyTransitionRecord(
        journey_id=journey.id,
        from_state=JourneyState.DRAFT,
        to_state=JourneyState.VERIFICATION_IN_PROGRESS,
        actor="CITIZEN",
        reason="Submitted supporting land documents",
    )
    # Add a claim with evidence
    claim = Claim(
        citizen_id=cit.id,
        journey_id=journey.id,
        claim_type="agricultural_landholding",
        value_json={"has_cultivable_land": True, "land_area_hectares": 1.5},
        source="CITIZEN_DECLARATION",
        status=ClaimStatus.CLAIMED,
    )
    db_session.add_all([t1, claim])
    await db_session.flush()

    evidence = Evidence(
        claim_id=claim.id,
        evidence_type="land_record_7_12",
        storage_reference="uploads/demo_ror.pdf",
        status=EvidenceStatus.PENDING,
    )
    db_session.add(evidence)
    await db_session.commit()

    # Query detail
    resp = await async_client.get(
        f"/api/v1/citizen/applications/{journey.id}",
        headers=headers,
    )
    assert resp.status_code == 200
    detail = resp.json()

    assert detail["id"] == str(journey.id)
    assert detail["scheme_code"] == "PM_KISAN"
    assert detail["citizen_ref"] == ref
    assert detail["claims_count"] == 1
    assert detail["evidence_count"] == 1
    assert len(detail["claims"]) == 1
    assert len(detail["transitions"]) == 1
    assert detail["allowed_actions"] is not None


@pytest.mark.asyncio
async def test_citizen_create_application(async_client: AsyncClient, db_session: AsyncSession):
    """Citizen can initiate a new application under a statutory scheme."""
    ref = f"SYN-CIT-INIT-{uuid.uuid4().hex[:6].upper()}"
    token = _make_citizen_token(email="init.citizen@test.local", ref=ref)
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "scheme_code": "SSY",
        "initial_facts": {"girl_child_age": 7, "number_of_daughters": 1},
    }

    resp = await async_client.post(
        "/api/v1/citizen/applications",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 201
    created = resp.json()
    assert created["scheme_code"] == "SSY"
    assert created["state"] == "FACTS_COLLECTED"
    assert created["application_ref"].startswith("APP-")


@pytest.mark.asyncio
async def test_citizen_create_application_invalid_scheme(async_client: AsyncClient):
    """Initiating an application with unknown scheme returns 404."""
    ref = f"SYN-CIT-INV-{uuid.uuid4().hex[:6].upper()}"
    token = _make_citizen_token(email="inv.citizen@test.local", ref=ref)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.post(
        "/api/v1/citizen/applications",
        json={"scheme_code": "UNKNOWN_SCHEME_XYZ"},
        headers=headers,
    )
    assert resp.status_code == 404
    assert "not found" in _get_error_message(resp.json()).lower()
