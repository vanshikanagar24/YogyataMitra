"""Comprehensive test suite for YogyataMitra Phase 7 Citizen Journey & Evidence Workflow.

Verifies:
1. Journey Lifecycle & State Machine Transitions:
   - Draft creation, progression through allowed states
   - Rejection of illegal transitions (e.g. DRAFT -> EVALUATED, COMPLETED -> DRAFT)
   - Immutable audit trail of every state transition
   - Terminal state semantics of COMPLETED
2. Claims Association & Fact Assembly:
   - Adding claims to a journey auto-advances DRAFT to FACTS_COLLECTED
   - Dot-notated and section-based claims assembly
   - Inability to add claims to COMPLETED journeys
3. Evidence Workflow & Verification Records:
   - Evidence submission with PENDING initial status
   - Verification of evidence creates immutable VerificationRecord
   - Rejection of evidence enforces mandatory rejection_reason
   - STRICT SEPARATION: Evidence VERIFIED/REJECTED never mutates factual claims or forces truth values
4. Journey Evaluation Integration:
   - Evaluates against statutory rules engine and links latest_evaluation_id
   - Handles ELIGIBLE, INELIGIBLE, and INSUFFICIENT_INFORMATION outcomes
   - Advances journey to EVALUATED or ACTION_REQUIRED based on blockers/pending evidence
   - Re-evaluation cycle creates distinct audit traces and updates state
   - Inability to evaluate COMPLETED journeys
5. Citizen Identity & Privacy:
   - No fake PII or invented demographic data
"""

from __future__ import annotations

from datetime import date
import uuid
import pytest
from httpx import AsyncClient

from app.models.enums import (
    ClaimStatus,
    EligibilityResult,
    EvidenceStatus,
    JourneyState,
    VerificationStatus,
)


# ==============================================================================
# 1. Journey Creation & Retrieval Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_journey_create_success_draft(async_client: AsyncClient):
    """POST /api/v1/journeys initializes a journey in DRAFT state."""
    payload = {
        "citizen_ref": f"CIT-TEST-{uuid.uuid4().hex[:8].upper()}",
        "scheme_code": "PM_KISAN",
    }
    response = await async_client.post("/api/v1/journeys", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["state"] == "DRAFT"
    assert data["citizen_ref"] == payload["citizen_ref"]
    assert data["scheme_code"] == "PM_KISAN"
    assert data["latest_evaluation_id"] is None
    assert "id" in data


@pytest.mark.asyncio
async def test_journey_create_with_initial_facts(async_client: AsyncClient):
    """POST /api/v1/journeys with initial_facts auto-transitions to FACTS_COLLECTED."""
    cit_ref = f"CIT-INIT-{uuid.uuid4().hex[:8].upper()}"
    payload = {
        "citizen_ref": cit_ref,
        "scheme_code": "PM_KISAN",
        "initial_facts": {
            "family": {
                "owns_cultivable_land": True,
                "is_institutional_landholder": False,
            }
        },
    }
    response = await async_client.post("/api/v1/journeys", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["state"] == "FACTS_COLLECTED"

    # Verify transition audit history
    history_res = await async_client.get(f"/api/v1/journeys/{data['id']}/history")
    assert history_res.status_code == 200
    history = history_res.json()
    assert len(history) == 1
    assert history[0]["from_state"] == "DRAFT"
    assert history[0]["to_state"] == "FACTS_COLLECTED"


@pytest.mark.asyncio
async def test_journey_create_unknown_scheme_returns_404(async_client: AsyncClient):
    """POST /api/v1/journeys with unknown scheme code returns 404."""
    payload = {
        "citizen_ref": "SYN-TEST-001",
        "scheme_code": "NON_EXISTENT_SCHEME_XYZ",
    }
    response = await async_client.post("/api/v1/journeys", json=payload)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_journey_create_extra_fields_forbidden(async_client: AsyncClient):
    """POST /api/v1/journeys rejects unknown extra fields with 422."""
    payload = {
        "citizen_ref": "SYN-TEST-001",
        "scheme_code": "PM_KISAN",
        "unauthorized_field": "hacker_val",
    }
    response = await async_client.post("/api/v1/journeys", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_journey_get_details(async_client: AsyncClient):
    """GET /api/v1/journeys/{id} retrieves full journey details."""
    create_res = await async_client.post("/api/v1/journeys", json={
        "citizen_ref": f"CIT-DET-{uuid.uuid4().hex[:8].upper()}",
        "scheme_code": "SSY",
    })
    journey_id = create_res.json()["id"]

    res = await async_client.get(f"/api/v1/journeys/{journey_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == journey_id
    assert data["scheme_code"] == "SSY"
    assert isinstance(data["claims"], list)
    assert isinstance(data["transitions"], list)


@pytest.mark.asyncio
async def test_journey_get_nonexistent_returns_404(async_client: AsyncClient):
    """GET /api/v1/journeys/{random_uuid} returns 404."""
    random_id = str(uuid.uuid4())
    res = await async_client.get(f"/api/v1/journeys/{random_id}")
    assert res.status_code == 404


# ==============================================================================
# 2. State Machine Transitions & Audit Log Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_journey_valid_transition_lifecycle(async_client: AsyncClient):
    """Verify standard legal path: DRAFT -> FACTS_COLLECTED -> READY_FOR_EVALUATION -> EVALUATED -> COMPLETED."""
    create_res = await async_client.post("/api/v1/journeys", json={
        "citizen_ref": f"CIT-LIFE-{uuid.uuid4().hex[:8].upper()}",
        "scheme_code": "PM_KISAN",
    })
    j_id = create_res.json()["id"]

    # 1. DRAFT -> FACTS_COLLECTED
    t1 = await async_client.post(f"/api/v1/journeys/{j_id}/transitions", json={
        "target_state": "FACTS_COLLECTED",
        "actor": "CITIZEN",
        "reason": "Filled out initial form",
    })
    assert t1.status_code == 200
    assert t1.json()["state"] == "FACTS_COLLECTED"

    # 2. FACTS_COLLECTED -> READY_FOR_EVALUATION
    t2 = await async_client.post(f"/api/v1/journeys/{j_id}/transitions", json={
        "target_state": "READY_FOR_EVALUATION",
        "actor": "OFFICER_42",
        "reason": "Form reviewed and approved",
    })
    assert t2.status_code == 200
    assert t2.json()["state"] == "READY_FOR_EVALUATION"

    # 3. READY_FOR_EVALUATION -> EVALUATED
    t3 = await async_client.post(f"/api/v1/journeys/{j_id}/transitions", json={
        "target_state": "EVALUATED",
        "actor": "ENGINE",
        "reason": "Rules evaluated",
    })
    assert t3.status_code == 200
    assert t3.json()["state"] == "EVALUATED"

    # 4. EVALUATED -> COMPLETED
    t4 = await async_client.post(f"/api/v1/journeys/{j_id}/transitions", json={
        "target_state": "COMPLETED",
        "actor": "OFFICER_42",
        "reason": "Journey finalized",
    })
    assert t4.status_code == 200
    assert t4.json()["state"] == "COMPLETED"


@pytest.mark.asyncio
async def test_journey_illegal_transition_rejected(async_client: AsyncClient):
    """Attempting an illegal transition (e.g. DRAFT -> COMPLETED) is rejected with 400."""
    create_res = await async_client.post("/api/v1/journeys", json={
        "citizen_ref": f"CIT-ILL-{uuid.uuid4().hex[:8].upper()}",
        "scheme_code": "PM_KISAN",
    })
    j_id = create_res.json()["id"]

    # DRAFT directly to COMPLETED is forbidden
    bad_t = await async_client.post(f"/api/v1/journeys/{j_id}/transitions", json={
        "target_state": "COMPLETED",
        "actor": "ATTACKER",
        "reason": "Bypassing checks",
    })
    assert bad_t.status_code == 400
    assert "Illegal state transition" in bad_t.json()["error"]["message"]


@pytest.mark.asyncio
async def test_journey_completed_is_terminal(async_client: AsyncClient):
    """COMPLETED journeys reject any further transitions with 400."""
    create_res = await async_client.post("/api/v1/journeys", json={
        "citizen_ref": f"CIT-TERM-{uuid.uuid4().hex[:8].upper()}",
        "scheme_code": "PM_KISAN",
    })
    j_id = create_res.json()["id"]

    # Transition to completed via valid route
    await async_client.post(f"/api/v1/journeys/{j_id}/transitions", json={
        "target_state": "FACTS_COLLECTED", "actor": "OFFICER"
    })
    await async_client.post(f"/api/v1/journeys/{j_id}/transitions", json={
        "target_state": "READY_FOR_EVALUATION", "actor": "OFFICER"
    })
    await async_client.post(f"/api/v1/journeys/{j_id}/transitions", json={
        "target_state": "EVALUATED", "actor": "OFFICER"
    })
    await async_client.post(f"/api/v1/journeys/{j_id}/transitions", json={
        "target_state": "COMPLETED", "actor": "OFFICER"
    })

    # Try to transition out of COMPLETED
    res = await async_client.post(f"/api/v1/journeys/{j_id}/transitions", json={
        "target_state": "DRAFT",
        "actor": "OFFICER",
    })
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_journey_history_audit_records(async_client: AsyncClient):
    """Verify that every transition creates an immutable JourneyTransitionRecord."""
    create_res = await async_client.post("/api/v1/journeys", json={
        "citizen_ref": f"CIT-HIST-{uuid.uuid4().hex[:8].upper()}",
        "scheme_code": "PM_KISAN",
    })
    j_id = create_res.json()["id"]

    await async_client.post(f"/api/v1/journeys/{j_id}/transitions", json={
        "target_state": "FACTS_COLLECTED",
        "actor": "OFFICER_A",
        "reason": "Step 1 complete",
    })
    await async_client.post(f"/api/v1/journeys/{j_id}/transitions", json={
        "target_state": "EVIDENCE_PENDING",
        "actor": "OFFICER_B",
        "reason": "Requesting docs",
    })

    history_res = await async_client.get(f"/api/v1/journeys/{j_id}/history")
    assert history_res.status_code == 200
    records = history_res.json()
    assert len(records) == 2
    assert records[0]["from_state"] == "DRAFT"
    assert records[0]["to_state"] == "FACTS_COLLECTED"
    assert records[0]["actor"] == "OFFICER_A"
    assert records[1]["from_state"] == "FACTS_COLLECTED"
    assert records[1]["to_state"] == "EVIDENCE_PENDING"
    assert records[1]["actor"] == "OFFICER_B"


# ==============================================================================
# 3. Claims Registration Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_journey_add_claim_auto_advances_draft_to_facts_collected(async_client: AsyncClient):
    """Adding a claim to a DRAFT journey automatically advances it to FACTS_COLLECTED."""
    create_res = await async_client.post("/api/v1/journeys", json={
        "citizen_ref": f"CIT-CLM-{uuid.uuid4().hex[:8].upper()}",
        "scheme_code": "PM_KISAN",
    })
    j_id = create_res.json()["id"]

    claim_res = await async_client.post(f"/api/v1/journeys/{j_id}/claims", json={
        "claim_type": "family.owns_cultivable_land",
        "value_json": {"value": True},
        "source": "SELF_DECLARATION",
    })
    assert claim_res.status_code == 201
    claim_data = claim_res.json()
    assert claim_data["claim_type"] == "family.owns_cultivable_land"
    assert claim_data["value_json"] == {"value": True}
    assert claim_data["status"] == "CLAIMED"

    # Check journey state changed to FACTS_COLLECTED
    j_res = await async_client.get(f"/api/v1/journeys/{j_id}")
    assert j_res.json()["state"] == "FACTS_COLLECTED"


@pytest.mark.asyncio
async def test_journey_cannot_add_claim_to_completed_journey(async_client: AsyncClient):
    """Cannot add claims once journey is COMPLETED."""
    create_res = await async_client.post("/api/v1/journeys", json={
        "citizen_ref": f"CIT-DONE-{uuid.uuid4().hex[:8].upper()}",
        "scheme_code": "PM_KISAN",
    })
    j_id = create_res.json()["id"]

    # Transition to COMPLETED
    await async_client.post(f"/api/v1/journeys/{j_id}/transitions", json={
        "target_state": "FACTS_COLLECTED", "actor": "O"
    })
    await async_client.post(f"/api/v1/journeys/{j_id}/transitions", json={
        "target_state": "READY_FOR_EVALUATION", "actor": "O"
    })
    await async_client.post(f"/api/v1/journeys/{j_id}/transitions", json={
        "target_state": "EVALUATED", "actor": "O"
    })
    await async_client.post(f"/api/v1/journeys/{j_id}/transitions", json={
        "target_state": "COMPLETED", "actor": "O"
    })

    bad_claim = await async_client.post(f"/api/v1/journeys/{j_id}/claims", json={
        "claim_type": "land.transferred_after_cutoff",
        "value_json": {"value": False},
    })
    assert bad_claim.status_code == 400


@pytest.mark.asyncio
async def test_journey_list_claims(async_client: AsyncClient):
    """GET /api/v1/journeys/{id}/claims lists all registered claims."""
    create_res = await async_client.post("/api/v1/journeys", json={
        "citizen_ref": f"CIT-LIST-{uuid.uuid4().hex[:8].upper()}",
        "scheme_code": "PM_KISAN",
    })
    j_id = create_res.json()["id"]

    await async_client.post(f"/api/v1/journeys/{j_id}/claims", json={
        "claim_type": "family.owns_cultivable_land",
        "value_json": {"value": True},
    })
    await async_client.post(f"/api/v1/journeys/{j_id}/claims", json={
        "claim_type": "family.is_institutional_landholder",
        "value_json": {"value": False},
    })

    claims_res = await async_client.get(f"/api/v1/journeys/{j_id}/claims")
    assert claims_res.status_code == 200
    claims = claims_res.json()
    assert len(claims) == 2
    types = {c["claim_type"] for c in claims}
    assert "family.owns_cultivable_land" in types
    assert "family.is_institutional_landholder" in types


# ==============================================================================
# 4. Evidence Workflow & Separation of Concerns Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_journey_submit_and_verify_evidence(async_client: AsyncClient):
    """Submitting and verifying evidence updates evidence status and creates VerificationRecord."""
    create_res = await async_client.post("/api/v1/journeys", json={
        "citizen_ref": f"CIT-EV1-{uuid.uuid4().hex[:8].upper()}",
        "scheme_code": "PM_KISAN",
    })
    j_id = create_res.json()["id"]

    # Add claim
    c_res = await async_client.post(f"/api/v1/journeys/{j_id}/claims", json={
        "claim_type": "family.owns_cultivable_land",
        "value_json": {"value": True},
    })
    claim_id = c_res.json()["id"]

    # Submit evidence
    ev_res = await async_client.post(f"/api/v1/journeys/{j_id}/claims/{claim_id}/evidence", json={
        "evidence_type": "KHATAUNI_RECORD_7_12",
        "storage_reference": "doc-vault://revenue/land/doc-9876.pdf",
        "metadata_json": {"khasra_no": "104/2", "district": "Varanasi"},
    })
    assert ev_res.status_code == 201
    ev_data = ev_res.json()
    assert ev_data["status"] == "PENDING"
    assert ev_data["evidence_type"] == "KHATAUNI_RECORD_7_12"
    ev_id = ev_data["id"]

    # Verify evidence
    verify_res = await async_client.post(f"/api/v1/journeys/{j_id}/evidence/{ev_id}/verify", json={
        "status": "VERIFIED",
        "verification_method": "LAND_PORTAL_API_LOOKUP",
        "verified_by": "AGRI_OFFICER_07",
        "details_json": {"portal_ref": "UP-REV-9921", "match_confidence": 1.0},
    })
    assert verify_res.status_code == 200
    verified_data = verify_res.json()
    assert verified_data["status"] == "VERIFIED"
    assert verified_data["verified_at"] is not None
    assert len(verified_data["verification_records"]) == 1
    vr = verified_data["verification_records"][0]
    assert vr["status"] == "VERIFIED"
    assert vr["verification_method"] == "LAND_PORTAL_API_LOOKUP"
    assert vr["verified_by"] == "AGRI_OFFICER_07"


@pytest.mark.asyncio
async def test_journey_reject_evidence_requires_reason(async_client: AsyncClient):
    """Rejecting evidence requires a non-empty rejection_reason."""
    create_res = await async_client.post("/api/v1/journeys", json={
        "citizen_ref": f"CIT-EV2-{uuid.uuid4().hex[:8].upper()}",
        "scheme_code": "PM_KISAN",
    })
    j_id = create_res.json()["id"]

    c_res = await async_client.post(f"/api/v1/journeys/{j_id}/claims", json={
        "claim_type": "family.owns_cultivable_land",
        "value_json": {"value": True},
    })
    claim_id = c_res.json()["id"]

    ev_res = await async_client.post(f"/api/v1/journeys/{j_id}/claims/{claim_id}/evidence", json={
        "evidence_type": "KHATAUNI_RECORD_7_12",
        "storage_reference": "doc-vault://revenue/land/bad-doc.pdf",
    })
    ev_id = ev_res.json()["id"]

    # Rejection without reason fails with 400
    bad_verify = await async_client.post(f"/api/v1/journeys/{j_id}/evidence/{ev_id}/verify", json={
        "status": "REJECTED",
        "verification_method": "MANUAL_INSPECTION",
        "verified_by": "OFFICER_99",
    })
    assert bad_verify.status_code == 400

    # Rejection with reason succeeds
    good_verify = await async_client.post(f"/api/v1/journeys/{j_id}/evidence/{ev_id}/verify", json={
        "status": "REJECTED",
        "verification_method": "MANUAL_INSPECTION",
        "verified_by": "OFFICER_99",
        "rejection_reason": "Document seal illegible and blurred",
    })
    assert good_verify.status_code == 200
    assert good_verify.json()["status"] == "REJECTED"
    assert good_verify.json()["rejection_reason"] == "Document seal illegible and blurred"


@pytest.mark.asyncio
async def test_strict_separation_evidence_verification_does_not_mutate_facts(async_client: AsyncClient):
    """CRITICAL: Evidence VERIFIED does not mutate underlying factual claims or force facts TRUE."""
    create_res = await async_client.post("/api/v1/journeys", json={
        "citizen_ref": f"CIT-SEP1-{uuid.uuid4().hex[:8].upper()}",
        "scheme_code": "PM_KISAN",
    })
    j_id = create_res.json()["id"]

    # Citizen asserted owns_cultivable_land is False
    c_res = await async_client.post(f"/api/v1/journeys/{j_id}/claims", json={
        "claim_type": "family.owns_cultivable_land",
        "value_json": {"value": False},
    })
    claim_id = c_res.json()["id"]

    ev_res = await async_client.post(f"/api/v1/journeys/{j_id}/claims/{claim_id}/evidence", json={
        "evidence_type": "AFFIDAVIT",
        "storage_reference": "doc-vault://affidavit.pdf",
    })
    ev_id = ev_res.json()["id"]

    # Verify the evidence
    await async_client.post(f"/api/v1/journeys/{j_id}/evidence/{ev_id}/verify", json={
        "status": "VERIFIED",
        "verification_method": "NOTARY_VERIFICATION",
        "verified_by": "NOTARY_PUBLIC",
    })

    # Assert underlying claim value_json has NOT been changed to True!
    claims_res = await async_client.get(f"/api/v1/journeys/{j_id}/claims")
    claim_after = next(c for c in claims_res.json() if c["id"] == claim_id)
    assert claim_after["value_json"] == {"value": False}


@pytest.mark.asyncio
async def test_strict_separation_evidence_rejection_does_not_mutate_facts(async_client: AsyncClient):
    """CRITICAL: Evidence REJECTED does not mutate underlying factual claims or force facts FALSE."""
    create_res = await async_client.post("/api/v1/journeys", json={
        "citizen_ref": f"CIT-SEP2-{uuid.uuid4().hex[:8].upper()}",
        "scheme_code": "PM_KISAN",
    })
    j_id = create_res.json()["id"]

    c_res = await async_client.post(f"/api/v1/journeys/{j_id}/claims", json={
        "claim_type": "family.owns_cultivable_land",
        "value_json": {"value": True},
    })
    claim_id = c_res.json()["id"]

    ev_res = await async_client.post(f"/api/v1/journeys/{j_id}/claims/{claim_id}/evidence", json={
        "evidence_type": "LAND_RECORD",
        "storage_reference": "doc-vault://land.pdf",
    })
    ev_id = ev_res.json()["id"]

    # Reject evidence
    await async_client.post(f"/api/v1/journeys/{j_id}/evidence/{ev_id}/verify", json={
        "status": "REJECTED",
        "verification_method": "MANUAL_CHECK",
        "verified_by": "OFFICER",
        "rejection_reason": "Expired document",
    })

    # Assert underlying claim value_json has NOT been changed to False!
    claims_res = await async_client.get(f"/api/v1/journeys/{j_id}/claims")
    claim_after = next(c for c in claims_res.json() if c["id"] == claim_id)
    assert claim_after["value_json"] == {"value": True}


# ==============================================================================
# 5. Journey Evaluation Integration Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_journey_evaluate_pm_kisan_eligible(async_client: AsyncClient):
    """Evaluating a fully qualifying PM-KISAN journey produces ELIGIBLE and links evaluation trace."""
    cit_ref = f"CIT-PMK-ELIG-{uuid.uuid4().hex[:8].upper()}"
    create_res = await async_client.post("/api/v1/journeys", json={
        "citizen_ref": cit_ref,
        "scheme_code": "PM_KISAN",
        "initial_facts": {
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
    })
    j_id = create_res.json()["id"]

    eval_res = await async_client.post(f"/api/v1/journeys/{j_id}/evaluate", json={
        "evaluation_date": "2024-01-01",
    })
    assert eval_res.status_code == 200
    data = eval_res.json()
    assert data["result_state"] == "ELIGIBLE"
    assert data["is_eligible"] is True
    assert data["journey_state"] == "EVALUATED"
    assert data["evaluation_id"] is not None
    assert len(data["missing_facts"]) == 0
    assert len(data["disqualifying_factors"]) == 0

    # Verify journey has latest_evaluation_id set
    j_detail = await async_client.get(f"/api/v1/journeys/{j_id}")
    assert j_detail.json()["latest_evaluation_id"] == data["evaluation_id"]


@pytest.mark.asyncio
async def test_journey_evaluate_pm_kisan_ineligible(async_client: AsyncClient):
    """Evaluating an ineligible PM-KISAN journey produces INELIGIBLE, disqualifying factors, and ACTION_REQUIRED."""
    cit_ref = f"CIT-PMK-INEL-{uuid.uuid4().hex[:8].upper()}"
    create_res = await async_client.post("/api/v1/journeys", json={
        "citizen_ref": cit_ref,
        "scheme_code": "PM_KISAN",
        "initial_facts": {
            "family": {
                "owns_cultivable_land": True,
                "is_institutional_landholder": False,
                "has_constitutional_post_holder": False,
                "has_public_representative": False,
                "has_disqualified_government_employee": False,
                "has_pensioner_above_ten_thousand": False,
                "has_income_tax_payer": True,  # Disqualifying!
                "has_registered_practicing_professional": False,
                "is_nri": False,
            },
            "land": {
                "transferred_after_cutoff": False,
            },
        },
    })
    j_id = create_res.json()["id"]

    eval_res = await async_client.post(f"/api/v1/journeys/{j_id}/evaluate", json={
        "evaluation_date": "2024-01-01",
    })
    assert eval_res.status_code == 200
    data = eval_res.json()
    assert data["result_state"] == "INELIGIBLE"
    assert data["is_eligible"] is False
    assert data["journey_state"] == "ACTION_REQUIRED"
    assert len(data["disqualifying_factors"]) >= 1
    dq_fields = [d["field_path"] for d in data["disqualifying_factors"]]
    assert "family.has_income_tax_payer" in dq_fields


@pytest.mark.asyncio
async def test_journey_evaluate_missing_facts_produces_insufficient_information(async_client: AsyncClient):
    """Evaluating with partial facts produces INSUFFICIENT_INFORMATION and lists missing required fields."""
    cit_ref = f"CIT-MISS-{uuid.uuid4().hex[:8].upper()}"
    create_res = await async_client.post("/api/v1/journeys", json={
        "citizen_ref": cit_ref,
        "scheme_code": "PM_KISAN",
        "initial_facts": {
            "family": {
                "owns_cultivable_land": True,
                # Missing all exclusions!
            },
        },
    })
    j_id = create_res.json()["id"]

    eval_res = await async_client.post(f"/api/v1/journeys/{j_id}/evaluate", json={
        "evaluation_date": "2024-01-01",
    })
    assert eval_res.status_code == 200
    data = eval_res.json()
    assert data["result_state"] == "INSUFFICIENT_INFORMATION"
    assert data["is_eligible"] is None
    assert data["journey_state"] == "ACTION_REQUIRED"
    assert len(data["missing_facts"]) > 0


@pytest.mark.asyncio
async def test_journey_evaluate_with_facts_override(async_client: AsyncClient):
    """`facts_override` allows supplementing missing facts dynamically during evaluation."""
    cit_ref = f"CIT-OVR-{uuid.uuid4().hex[:8].upper()}"
    create_res = await async_client.post("/api/v1/journeys", json={
        "citizen_ref": cit_ref,
        "scheme_code": "PM_KISAN",
        "initial_facts": {
            "family": {
                "owns_cultivable_land": True,
            },
        },
    })
    j_id = create_res.json()["id"]

    # Provide remaining facts via override
    eval_res = await async_client.post(f"/api/v1/journeys/{j_id}/evaluate", json={
        "evaluation_date": "2024-01-01",
        "facts_override": {
            "family": {
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
    })
    assert eval_res.status_code == 200
    assert eval_res.json()["result_state"] == "ELIGIBLE"


@pytest.mark.asyncio
async def test_journey_evaluate_with_pending_evidence_sets_action_required(async_client: AsyncClient):
    """When facts are eligible but evidence is still PENDING verification, journey state becomes ACTION_REQUIRED."""
    cit_ref = f"CIT-PND-EV-{uuid.uuid4().hex[:8].upper()}"
    create_res = await async_client.post("/api/v1/journeys", json={
        "citizen_ref": cit_ref,
        "scheme_code": "PM_KISAN",
        "initial_facts": {
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
    })
    j_id = create_res.json()["id"]

    # Add a claim and an unverified evidence item
    c_res = await async_client.post(f"/api/v1/journeys/{j_id}/claims", json={
        "claim_type": "land.record_verification",
        "value_json": {"status": "submitted"},
    })
    claim_id = c_res.json()["id"]
    await async_client.post(f"/api/v1/journeys/{j_id}/claims/{claim_id}/evidence", json={
        "evidence_type": "PATTA_RECORD",
        "storage_reference": "doc://patta.pdf",
    })

    eval_res = await async_client.post(f"/api/v1/journeys/{j_id}/evaluate", json={
        "evaluation_date": "2024-01-01",
    })
    assert eval_res.status_code == 200
    data = eval_res.json()
    assert data["result_state"] == "ELIGIBLE"
    assert data["pending_evidence_count"] == 1
    assert data["journey_state"] == "ACTION_REQUIRED"
    assert any("pending verification" in item for item in data["action_items"])


@pytest.mark.asyncio
async def test_journey_re_evaluation_creates_distinct_audit_traces(async_client: AsyncClient):
    """Re-evaluating a journey produces distinct persisted audit trace records."""
    cit_ref = f"CIT-REEVAL-{uuid.uuid4().hex[:8].upper()}"
    create_res = await async_client.post("/api/v1/journeys", json={
        "citizen_ref": cit_ref,
        "scheme_code": "SSY",
        "initial_facts": {
            "beneficiary": {
                "gender": "FEMALE",
                "is_indian_resident": True,
                "date_of_birth": "2019-01-01",
            },
            "account": {
                "opening_date": "2024-06-01",
                "is_first_account_for_child": True,
            },
            "guardian": {
                "is_natural_guardian": True,
                "is_court_appointed_legal_guardian": False,
            },
            "family": {
                "active_ssy_accounts_count": 0,
                "has_multiple_birth_exception": False,
            },
        },
    })
    j_id = create_res.json()["id"]

    eval1 = await async_client.post(f"/api/v1/journeys/{j_id}/evaluate", json={
        "evaluation_date": "2024-06-01",
    })
    assert eval1.status_code == 200
    eval_id_1 = eval1.json()["evaluation_id"]

    eval2 = await async_client.post(f"/api/v1/journeys/{j_id}/evaluate", json={
        "evaluation_date": "2024-06-01",
    })
    assert eval2.status_code == 200
    eval_id_2 = eval2.json()["evaluation_id"]

    # Distinct audit records created
    assert eval_id_1 != eval_id_2

    # Latest evaluation on journey points to second evaluation
    j_res = await async_client.get(f"/api/v1/journeys/{j_id}")
    assert j_res.json()["latest_evaluation_id"] == eval_id_2


@pytest.mark.asyncio
async def test_journey_evaluate_completed_journey_fails(async_client: AsyncClient):
    """Cannot execute evaluation on a completed journey."""
    create_res = await async_client.post("/api/v1/journeys", json={
        "citizen_ref": f"CIT-CMPL-{uuid.uuid4().hex[:8].upper()}",
        "scheme_code": "PM_KISAN",
    })
    j_id = create_res.json()["id"]

    # Advance to COMPLETED
    await async_client.post(f"/api/v1/journeys/{j_id}/transitions", json={
        "target_state": "FACTS_COLLECTED", "actor": "A"
    })
    await async_client.post(f"/api/v1/journeys/{j_id}/transitions", json={
        "target_state": "READY_FOR_EVALUATION", "actor": "A"
    })
    await async_client.post(f"/api/v1/journeys/{j_id}/transitions", json={
        "target_state": "EVALUATED", "actor": "A"
    })
    await async_client.post(f"/api/v1/journeys/{j_id}/transitions", json={
        "target_state": "COMPLETED", "actor": "A"
    })

    res = await async_client.post(f"/api/v1/journeys/{j_id}/evaluate", json={
        "evaluation_date": "2024-01-01",
    })
    assert res.status_code == 400


# ==============================================================================
# 6. Citizen Representation & Privacy Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_journey_citizen_reference_no_invented_pii(async_client: AsyncClient):
    """Citizen record created via journey contains only synthetic reference, zero invented PII."""
    from app.models.citizen import Citizen
    from tests.conftest import TestSessionLocal
    from sqlalchemy import select

    test_ref = f"SYN-NOPII-{uuid.uuid4().hex[:8].upper()}"
    create_res = await async_client.post("/api/v1/journeys", json={
        "citizen_ref": test_ref,
        "scheme_code": "PM_KISAN",
    })
    assert create_res.status_code == 201

    async with TestSessionLocal() as session:
        stmt = select(Citizen).where(Citizen.synthetic_reference == test_ref)
        result = await session.execute(stmt)
        citizen = result.scalar_one_or_none()
        assert citizen is not None
        assert citizen.synthetic_reference == test_ref
        assert citizen.display_name is None
        assert citizen.date_of_birth is None
        assert citizen.gender is None
        assert citizen.state is None
        assert citizen.district is None
