"""Comprehensive test suite for Phase 14: Officer / Human Verification Portal.

Validates:
- Test A: Anonymous Request Rejection (HTTP 401)
- Test B: Citizen Role Rejection (HTTP 403)
- Test C: Officer Access Permitted (HTTP 200)
- Test D: Supervisor-Only Escalation Operations (HTTP 403 for Officer, 200 for Supervisor)
- Test E: Server-Side Validation & Mandatory Reason Enforcement (HTTP 422 / 400)
- Test F: Evidence Isolation & Verification Record Creation
- Test G: Fact Immutability (Claim.value_json is never mutated)
- Test H: Evaluator Logic & Rule Immutability
- Test I: Policy Version & Cryptographic Hash Immutability
- Test J: Immutable Append-Only Audit Trail Logging
- Full End-to-End Workflow: Journey -> Evidence -> Officer -> Review -> Audit
- 5-Outcome Handling: VERIFIED, CLARIFICATION_REQUIRED, REJECTED, ESCALATED, COMPLETED
"""

from __future__ import annotations

import time
import uuid
from datetime import timedelta
from typing import Any, Dict
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings
from app.core.security import (
    DEMO_USERS,
    authenticate_user,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models.citizen import Claim, Evidence, VerificationRecord
from app.models.enums import EvidenceStatus, HumanReviewStatus, VerificationStatus
from app.models.human_review import HumanReview, HumanReviewAuditEvent
from app.models.journey import EvaluationJourney


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------

def get_error_message(response) -> str:
    """Helper to extract standardized error message from API response."""
    data = response.json()
    if isinstance(data, dict):
        if "error" in data and isinstance(data["error"], dict):
            return str(data["error"].get("message", ""))
        if "detail" in data:
            return str(data["detail"])
    return str(data)


async def get_auth_token(async_client: AsyncClient, email: str, password: str) -> str:
    """Helper to authenticate and return bearer JWT token."""
    res = await async_client.post("/api/v1/officer/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


async def create_test_journey_with_evidence(
    async_client: AsyncClient, scheme_code: str = "PM_KISAN"
) -> Dict[str, Any]:
    """Helper to create a full journey with claim and evidence."""
    cit_ref = f"CIT-P14-{uuid.uuid4().hex[:8].upper()}"
    j_res = await async_client.post("/api/v1/journeys", json={
        "citizen_ref": cit_ref,
        "scheme_code": scheme_code,
    })
    assert j_res.status_code == 201
    journey_id = j_res.json()["id"]

    # Add claim
    c_res = await async_client.post(f"/api/v1/journeys/{journey_id}/claims", json={
        "claim_type": "family.owns_cultivable_land",
        "value_json": {"value": True},
        "source": "SELF_DECLARATION",
    })
    assert c_res.status_code == 201
    claim_id = c_res.json()["id"]

    # Submit evidence
    ev_res = await async_client.post(f"/api/v1/journeys/{journey_id}/claims/{claim_id}/evidence", json={
        "evidence_type": "LAND_RECORD",
        "storage_reference": f"vault://revenue/land/record-{uuid.uuid4().hex[:6]}.pdf",
        "metadata_json": {"khasra_no": "421/B", "district": "Varanasi"},
    })
    assert ev_res.status_code == 201
    evidence_id = ev_res.json()["id"]

    # Run evaluation
    eval_res = await async_client.post(
        f"/api/v1/journeys/{journey_id}/evaluate",
        json={},
    )
    assert eval_res.status_code == 200, f"Evaluate failed: {eval_res.status_code} - {eval_res.json()}"

    return {
        "journey_id": journey_id,
        "claim_id": claim_id,
        "evidence_id": evidence_id,
        "citizen_ref": cit_ref,
    }


# ==============================================================================
# Test A: Anonymous Request Rejection (HTTP 401)
# ==============================================================================

@pytest.mark.asyncio
async def test_officer_anonymous_rejection(async_client: AsyncClient):
    """Calling officer endpoints without token or with invalid/expired token returns 401."""
    # 1. No auth header
    r1 = await async_client.get("/api/v1/officer/queue")
    assert r1.status_code == 401
    assert "not provided" in get_error_message(r1).lower()

    r2 = await async_client.get(f"/api/v1/officer/cases/{uuid.uuid4()}")
    assert r2.status_code == 401

    r3 = await async_client.post(
        f"/api/v1/officer/cases/{uuid.uuid4()}/review",
        json={"decision": "VERIFIED"}
    )
    assert r3.status_code == 401

    # 2. Malformed token
    r4 = await async_client.get(
        "/api/v1/officer/queue",
        headers={"Authorization": "Bearer invalid.jwt.token"}
    )
    assert r4.status_code == 401

    # 3. Forged signature
    fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmYWtlQGdvdi5pbiIsInJvbGUiOiJPRkZJQ0VSIiwiZXhwIjoxOTk5OTk5OTk5fQ.invalid_sig"
    r5 = await async_client.get(
        "/api/v1/officer/queue",
        headers={"Authorization": f"Bearer {fake_token}"}
    )
    assert r5.status_code == 401


# ==============================================================================
# Test B: Citizen Role Rejection (HTTP 403)
# ==============================================================================

@pytest.mark.asyncio
async def test_officer_citizen_role_rejection(async_client: AsyncClient):
    """Users with CITIZEN role are rejected with HTTP 403 Forbidden."""
    # 1. Citizen login attempt on officer endpoint returns 403
    r1 = await async_client.post("/api/v1/officer/auth/login", json={
        "email": "citizen.test@yogyatamitra.local",
        "password": "Citizen@123",
    })
    assert r1.status_code == 403
    assert "citizen" in get_error_message(r1).lower()

    # 2. Token crafted with role="CITIZEN" is rejected on all officer endpoints
    citizen_token = create_access_token({
        "sub": "citizen.test@yogyatamitra.local",
        "role": "CITIZEN",
        "name": "Test Citizen",
    })
    headers = {"Authorization": f"Bearer {citizen_token}"}

    r2 = await async_client.get("/api/v1/officer/queue", headers=headers)
    assert r2.status_code == 403
    assert "citizen" in get_error_message(r2).lower()

    r3 = await async_client.get(f"/api/v1/officer/cases/{uuid.uuid4()}", headers=headers)
    assert r3.status_code == 403


# ==============================================================================
# Test C: Officer Access Permitted (HTTP 200)
# ==============================================================================

@pytest.mark.asyncio
async def test_officer_access_permitted(async_client: AsyncClient):
    """Officer login succeeds and grants access to queue and case details."""
    token = await get_auth_token(async_client, "officer@yogyatamitra.local", "Officer@123")
    headers = {"Authorization": f"Bearer {token}"}

    # Verify profile
    me_res = await async_client.get("/api/v1/officer/auth/me", headers=headers)
    assert me_res.status_code == 200
    me = me_res.json()
    assert me["role"] == "OFFICER"
    assert me["email"] == "officer@yogyatamitra.local"

    # Verify queue access
    q_res = await async_client.get("/api/v1/officer/queue", headers=headers)
    assert q_res.status_code == 200
    q_data = q_res.json()
    assert "metrics" in q_data
    assert "items" in q_data
    assert isinstance(q_data["items"], list)


# ==============================================================================
# Test D: Supervisor-Only Escalation Operations (HTTP 403 / 200)
# ==============================================================================

@pytest.mark.asyncio
async def test_supervisor_escalation_lifecycle(async_client: AsyncClient):
    """Resolving an escalated case requires SUPERVISOR role and mandatory reason."""
    fixture = await create_test_journey_with_evidence(async_client)
    j_id = fixture["journey_id"]

    officer_token = await get_auth_token(async_client, "officer@yogyatamitra.local", "Officer@123")
    sup_token = await get_auth_token(async_client, "supervisor@yogyatamitra.local", "Supervisor@123")
    off_headers = {"Authorization": f"Bearer {officer_token}"}
    sup_headers = {"Authorization": f"Bearer {sup_token}"}

    # 1. Officer escalates the case (requires reason)
    esc_res = await async_client.post(
        f"/api/v1/officer/cases/{j_id}/review",
        headers=off_headers,
        json={
            "decision": "ESCALATED",
            "reason": "Discrepancy detected between revenue record mutation date and scheme cut-off date.",
            "notes": "Requesting supervisor review per Section 4(c) guidelines",
        },
    )
    assert esc_res.status_code == 200
    assert esc_res.json()["review_status"] == "ESCALATED"

    # 2. Officer attempts to resolve the escalated case -> 403 Forbidden!
    off_resolve = await async_client.post(
        f"/api/v1/officer/cases/{j_id}/review",
        headers=off_headers,
        json={
            "decision": "COMPLETED",
            "reason": "Officer attempting unauthorized resolution",
        },
    )
    assert off_resolve.status_code == 403
    assert "supervisor" in get_error_message(off_resolve).lower()

    # 3. Supervisor attempts resolution without reason -> 422 Unprocessable Entity
    sup_bad = await async_client.post(
        f"/api/v1/officer/cases/{j_id}/review",
        headers=sup_headers,
        json={"decision": "COMPLETED", "reason": ""},
    )
    assert sup_bad.status_code == 422

    # 4. Supervisor successfully resolves with mandatory supervisory justification
    sup_resolve = await async_client.post(
        f"/api/v1/officer/cases/{j_id}/review",
        headers=sup_headers,
        json={
            "decision": "COMPLETED",
            "reason": "Supervisor confirmed succession exception applies under statutory clause 4(b).",
            "notes": "Verified via state revenue portal portal ID UP-8821.",
        },
    )
    assert sup_resolve.status_code == 200
    assert sup_resolve.json()["review_status"] == "COMPLETED"
    assert sup_resolve.json()["reviewer_role"] == "SUPERVISOR"


# ==============================================================================
# Test E: Server-Side Validation & Reason Enforcement
# ==============================================================================

@pytest.mark.asyncio
async def test_officer_validation_and_reason_enforcement(async_client: AsyncClient):
    """Server enforces mandatory reasons for adverse or escalation actions."""
    fixture = await create_test_journey_with_evidence(async_client)
    j_id = fixture["journey_id"]
    ev_id = fixture["evidence_id"]

    token = await get_auth_token(async_client, "officer@yogyatamitra.local", "Officer@123")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Reject evidence without reason -> 422
    r1 = await async_client.post(
        f"/api/v1/officer/cases/{j_id}/evidence/{ev_id}/verify",
        headers=headers,
        json={"action": "REJECT", "reason": "   "},
    )
    assert r1.status_code == 422

    # 2. Request clarification without reason -> 422
    r2 = await async_client.post(
        f"/api/v1/officer/cases/{j_id}/evidence/{ev_id}/verify",
        headers=headers,
        json={"action": "REQUEST_CLARIFICATION", "reason": None},
    )
    assert r2.status_code == 422

    # 3. Case review REJECTED without reason -> 422
    r3 = await async_client.post(
        f"/api/v1/officer/cases/{j_id}/review",
        headers=headers,
        json={"decision": "REJECTED", "reason": ""},
    )
    assert r3.status_code == 422

    # 4. Case review ESCALATED without reason -> 422
    r4 = await async_client.post(
        f"/api/v1/officer/cases/{j_id}/review",
        headers=headers,
        json={"decision": "ESCALATED", "reason": " "},
    )
    assert r4.status_code == 422

    # 5. Invalid action string -> 400
    r5 = await async_client.post(
        f"/api/v1/officer/cases/{j_id}/evidence/{ev_id}/verify",
        headers=headers,
        json={"action": "APPROVE_BENEFITS", "reason": "Valid reason"},
    )
    assert r5.status_code == 400


# ==============================================================================
# Test F & G: Evidence Verification & Fact Immutability
# ==============================================================================

@pytest.mark.asyncio
async def test_evidence_verification_and_fact_immutability(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verifying/rejecting evidence never mutates Claim.value_json."""
    fixture = await create_test_journey_with_evidence(async_client)
    j_id = fixture["journey_id"]
    claim_id = uuid.UUID(fixture["claim_id"])
    ev_id = fixture["evidence_id"]

    token = await get_auth_token(async_client, "officer@yogyatamitra.local", "Officer@123")
    headers = {"Authorization": f"Bearer {token}"}

    # Capture original claim value
    stmt = select(Claim).where(Claim.id == claim_id)
    c_res = await db_session.execute(stmt)
    claim_before = c_res.scalars().one()
    original_value_json = dict(claim_before.value_json)

    # 1. Verify evidence
    v_res = await async_client.post(
        f"/api/v1/officer/cases/{j_id}/evidence/{ev_id}/verify",
        headers=headers,
        json={
            "action": "VERIFY",
            "notes": "Verified against state land revenue records (RoR)",
        },
    )
    assert v_res.status_code == 200
    ev_data = v_res.json()
    assert ev_data["status"] == "VERIFIED"
    assert ev_data["verified_at"] is not None
    assert len(ev_data["verification_records"]) >= 1

    # 2. Check claim value in DB is completely untouched
    await db_session.rollback()  # Refresh session
    c_res2 = await db_session.execute(stmt)
    claim_after = c_res2.scalars().one()
    assert claim_after.value_json == original_value_json

    # 3. Record adverse case decision
    dec_res = await async_client.post(
        f"/api/v1/officer/cases/{j_id}/review",
        headers=headers,
        json={
            "decision": "CLARIFICATION_REQUIRED",
            "reason": "Supporting land map missing field boundary numbers.",
        },
    )
    assert dec_res.status_code == 200

    # 4. Check claim value in DB remains 100% untouched
    await db_session.rollback()
    c_res3 = await db_session.execute(stmt)
    claim_final = c_res3.scalars().one()
    assert claim_final.value_json == original_value_json


# ==============================================================================
# Test H & I: Policy Version, Hash & Evaluator Immutability
# ==============================================================================

@pytest.mark.asyncio
async def test_policy_version_and_hash_immutability(async_client: AsyncClient):
    """Case inspection displays read-only policy provenance with exact statutory rule hash."""
    fixture = await create_test_journey_with_evidence(async_client, scheme_code="PM_KISAN")
    j_id = fixture["journey_id"]

    token = await get_auth_token(async_client, "officer@yogyatamitra.local", "Officer@123")
    headers = {"Authorization": f"Bearer {token}"}

    case_res = await async_client.get(f"/api/v1/officer/cases/{j_id}", headers=headers)
    assert case_res.status_code == 200
    case = case_res.json()

    assert case["scheme_code"] == "PM_KISAN"
    prov = case["policy_provenance"]
    assert prov is not None
    assert prov["policy_version"] in ("v1.0-2019", "v2.0-2020", "v3.0-2023", "v1.0-2014", "v2.0-2016", "v3.0-2019")
    assert prov["content_sha256"] is not None
    assert len(prov["content_sha256"]) == 64  # Valid SHA-256
    assert prov["is_statutory_source_verified"] is True

    # Assessment details
    assessment = case["automated_assessment"]
    assert assessment is not None
    assert assessment["determination"] in ("ELIGIBLE", "INELIGIBLE", "INSUFFICIENT_INFORMATION")
    assert assessment["ruleset_hash"] == prov["content_sha256"]


# ==============================================================================
# Test J: Immutable Append-Only Audit Trail Logging
# ==============================================================================

@pytest.mark.asyncio
async def test_immutable_append_only_audit_trail(async_client: AsyncClient):
    """Every evidence determination and case review writes to append-only audit trail."""
    fixture = await create_test_journey_with_evidence(async_client)
    j_id = fixture["journey_id"]
    ev_id = fixture["evidence_id"]

    token = await get_auth_token(async_client, "officer@yogyatamitra.local", "Officer@123")
    headers = {"Authorization": f"Bearer {token}"}

    # Action 1: Verify evidence
    await async_client.post(
        f"/api/v1/officer/cases/{j_id}/evidence/{ev_id}/verify",
        headers=headers,
        json={"action": "VERIFY", "notes": "Land record valid"},
    )

    # Action 2: Case review
    await async_client.post(
        f"/api/v1/officer/cases/{j_id}/review",
        headers=headers,
        json={
            "decision": "VERIFIED",
            "reason": "All documents verified in accordance with statutory requirements.",
        },
    )

    # Fetch audit trail
    audit_res = await async_client.get(
        f"/api/v1/officer/cases/{j_id}/audit-trail",
        headers=headers,
    )
    assert audit_res.status_code == 200
    events = audit_res.json()
    assert len(events) >= 2

    # Check evidence verify event
    ev_events = [e for e in events if e["action"] == "EVIDENCE_VERIFY"]
    assert len(ev_events) == 1
    assert ev_events[0]["actor_identity"] == "officer@yogyatamitra.local"
    assert ev_events[0]["actor_role"] == "OFFICER"
    assert ev_events[0]["new_status"] == "VERIFIED"

    # Check case decision event
    case_events = [e for e in events if e["action"] == "DECISION_VERIFIED"]
    assert len(case_events) == 1
    assert case_events[0]["actor_identity"] == "officer@yogyatamitra.local"
    assert case_events[0]["actor_role"] == "OFFICER"
    assert case_events[0]["new_status"] == "VERIFIED"
    assert "statutory requirements" in case_events[0]["reason"]


# ==============================================================================
# Full Workflow & 5-Outcome Handling Test
# ==============================================================================

@pytest.mark.asyncio
async def test_all_five_human_review_outcomes(async_client: AsyncClient):
    """Verify all 5 official human review outcomes: VERIFIED, CLARIFICATION_REQUIRED, REJECTED, ESCALATED, COMPLETED."""
    token = await get_auth_token(async_client, "officer@yogyatamitra.local", "Officer@123")
    sup_token = await get_auth_token(async_client, "supervisor@yogyatamitra.local", "Supervisor@123")
    headers = {"Authorization": f"Bearer {token}"}
    sup_headers = {"Authorization": f"Bearer {sup_token}"}

    outcomes = [
        ("VERIFIED", "Verification complete and documents authentic", headers),
        ("CLARIFICATION_REQUIRED", "Citizen requested to upload clearer land record copy", headers),
        ("REJECTED", "Document submitted does not match revenue record database", headers),
        ("ESCALATED", "Complex joint-holding land partition requires supervisor guidance", headers),
    ]

    for decision, reason, auth in outcomes:
        fixture = await create_test_journey_with_evidence(async_client)
        j_id = fixture["journey_id"]

        r = await async_client.post(
            f"/api/v1/officer/cases/{j_id}/review",
            headers=auth,
            json={"decision": decision, "reason": reason},
        )
        assert r.status_code == 200
        assert r.json()["review_status"] == decision
        assert r.json()["review_decision"] == decision

    # For COMPLETED, test direct completion by supervisor
    fixture_comp = await create_test_journey_with_evidence(async_client)
    j_id_comp = fixture_comp["journey_id"]
    r_comp = await async_client.post(
        f"/api/v1/officer/cases/{j_id_comp}/review",
        headers=sup_headers,
        json={"decision": "COMPLETED", "reason": "Final sign-off completed by supervisor"},
    )
    assert r_comp.status_code == 200
    assert r_comp.json()["review_status"] == "COMPLETED"


# ==============================================================================
# Security Remediation Tests: Salt, Configuration & Production Boundaries
# ==============================================================================

def test_password_hashing_unique_salts_for_same_password():
    """Verify that every password hash uses a unique cryptographically random salt."""
    raw_pass = "VerificationOfficer@2026"
    hash1 = hash_password(raw_pass)
    hash2 = hash_password(raw_pass)

    assert hash1 != hash2, "Two hashes of the same password must produce distinct values"
    assert hash1.startswith("pbkdf2_sha256$100000$")
    assert hash2.startswith("pbkdf2_sha256$100000$")

    parts1 = hash1.split("$")
    parts2 = hash2.split("$")
    assert len(parts1) == 4
    assert len(parts2) == 4

    salt1, key1 = parts1[2], parts1[3]
    salt2, key2 = parts2[2], parts2[3]

    assert salt1 != salt2, "Salts must be randomly generated and distinct"
    assert key1 != key2, "Derived keys must be distinct due to different salts"


def test_password_verification_with_salt():
    """Verify that password verification succeeds with correct salt and fails with wrong password."""
    raw_pass = "SupervisorReviewSecurePass!2026"
    stored_hash = hash_password(raw_pass)

    # Correct password succeeds
    assert verify_password(raw_pass, stored_hash) is True

    # Incorrect passwords fail
    assert verify_password("WrongPass!2026", stored_hash) is False
    assert verify_password("supervisorreviewsecurepass!2026", stored_hash) is False
    assert verify_password("", stored_hash) is False

    # Corrupted / invalid hash formats fail gracefully
    assert verify_password(raw_pass, "invalid_hash") is False
    assert verify_password(raw_pass, "pbkdf2_sha256$bad$format") is False


def test_production_environment_missing_secret_key_fails_closed():
    """Verify that production environment strictly fails closed if SECRET_KEY is omitted."""
    with pytest.raises(ValueError, match="SECRET_KEY must be explicitly configured in production"):
        Settings(ENVIRONMENT="production")


def test_production_environment_rejects_insecure_secret_key():
    """Verify that production environment rejects development or insecure fallback keys."""
    with pytest.raises(ValueError, match="Insecure development SECRET_KEY cannot be used"):
        Settings(ENVIRONMENT="production", SECRET_KEY="dev-insecure-key-12345")

    with pytest.raises(ValueError, match="Insecure development SECRET_KEY cannot be used"):
        Settings(ENVIRONMENT="production", SECRET_KEY="insecure-placeholder-key")


def test_production_environment_disables_demo_accounts():
    """Verify that demo accounts cannot be enabled in production and are strictly disabled."""
    # Settings validation prevents ENABLE_DEMO_ACCOUNTS=True in production
    with pytest.raises(ValueError, match="ENABLE_DEMO_ACCOUNTS cannot be enabled in production"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="high-entropy-production-secret-key-at-least-32-chars",
            ENABLE_DEMO_ACCOUNTS=True,
        )

    # Runtime isolation: when in production, DEMO_USERS is empty and authentication fails closed
    with patch.object(settings, "ENVIRONMENT", "production"):
        with patch.object(settings, "ENABLE_DEMO_ACCOUNTS", False):
            assert len(DEMO_USERS) == 0
            assert DEMO_USERS.get("officer@yogyatamitra.local") is None
            assert authenticate_user("officer@yogyatamitra.local", "Officer@123") is None
            assert authenticate_user("supervisor@yogyatamitra.local", "Supervisor@123") is None


def test_jwt_token_expiration_enforced():
    """Verify that expired JWT access tokens are rejected by decode_access_token."""
    payload = {
        "sub": "officer@yogyatamitra.local",
        "role": "OFFICER",
        "name": "Expired Officer",
    }
    # Create token that expired 60 seconds ago
    expired_token = create_access_token(payload, expires_delta=timedelta(seconds=-60))
    decoded = decode_access_token(expired_token)
    assert decoded is None, "Expired JWT token must decode to None"


def test_jwt_tampered_signature_and_payload_rejected():
    """Verify that JWT tokens with invalid signatures or tampered payloads are rejected."""
    payload = {
        "sub": "officer@yogyatamitra.local",
        "role": "OFFICER",
        "name": "Officer Name",
    }
    valid_token = create_access_token(payload, expires_delta=timedelta(minutes=15))
    assert decode_access_token(valid_token) is not None

    # 1. Invalid signature (tampered signature string)
    parts = valid_token.split(".")
    tampered_sig = parts[0] + "." + parts[1] + "." + "corrupted_sig_12345"
    assert decode_access_token(tampered_sig) is None

    # 2. Tampered payload with original signature
    tampered_payload_str = "eyJzdWIiOiJhdHRhY2tlckB5b2d5YXRhbWl0cmEubG9jYWwiLCJyb2xlIjoiU1VQRVJWSVNPUiJ9"
    tampered_token = parts[0] + "." + tampered_payload_str + "." + parts[2]
    assert decode_access_token(tampered_token) is None

