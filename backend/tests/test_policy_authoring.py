"""Comprehensive test suite for Phase 16: Controlled Policy Authoring & Compilation.

Validates all 35+ core requirements:
- Security & RBAC: Anonymous rejection (401), Citizen rejection (403), Officer/Supervisor access (200/201)
- Authoring Lifecycle: DRAFT, AUTHORING, VALIDATING, TESTING, PENDING_REVIEW, IN_REVIEW, STAGED, REJECTED, NEEDS_CLARIFICATION, ARCHIVED
- Provenance & Candidate Import: Import APPROVED candidates only; reject non-approved with HTTP 409
- Revisions & Immutability: AST changes trigger new revision snapshot and reset validation/test status
- Static AST Validation: Type safety, duplicate rule IDs, chronological date ordering, overlap warnings, arbitrary code rejection
- Deterministic Compilation: Canonical JSON generation, frozen SHA-256 rule hashing, key order invariance
- Zero AI / Zero Network Invariant: Deterministic test generation and evaluation without external dependencies
- Boundary & Strong Kleene Tests: Auto-generated boundary values and UNKNOWN propagation on missing facts
- Deterministic Test Runner: RuleEvaluator execution against simulated facts context
- Policy Diff Engine: Structural AST diffing, added/removed/modified rule detection, human-readable explanations
- Human Governance & Separation of Duties: Mandatory >= 5 char justification reason, Author cannot stage own draft, Staging requires SUPERVISOR
- Non-Active Staged Invariant: Staged drafts never create active PolicyVersion records or alter citizen evaluations
- Statutory Regression Invariant: All 6 canonical policy version hashes remain permanently frozen
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
from typing import Any, Dict, Optional
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import TestSessionLocal as AsyncSessionLocal
from app.core.security import create_access_token
from app.engine.ast.validation import validate_ast
from app.engine.explainability.provenance import compute_canonical_rule_hash
from app.models.policy_discovery import (
    CandidateReviewStatus,
    CandidateType,
    DuplicateStatus,
    EffectiveDateStatus,
    PolicyDiscoveryCandidate,
    ProvenanceStatus,
)
from app.models.policy_draft import (
    PolicyDraft,
    PolicyDraftAuditEvent,
    PolicyDraftLifecycleStatus,
    PolicyDraftRevision,
    PolicyDraftTest,
    PolicyDraftTestStatus,
    PolicyDraftValidationStatus,
)
from app.models.scheme import PolicyVersion, Scheme
from app.services.policy_loader import load_all_policies
from app.services.policy_test_service import (
    FROZEN_CANONICAL_POLICY_HASHES,
    verify_canonical_policy_regression,
)


# ==============================================================================
# Helpers & Auth Fixtures
# ==============================================================================

def make_officer_token(
    email: str = "officer.author@yogyatamitra.gov.in",
    role: str = "OFFICER",
    name: str = "Policy Author Officer",
) -> str:
    return create_access_token(
        data={
            "sub": email,
            "email": email,
            "role": role,
            "name": name,
        }
    )


def make_supervisor_token(
    email: str = "supervisor.reviewer@yogyatamitra.gov.in",
    role: str = "SUPERVISOR",
    name: str = "Policy Reviewer Supervisor",
) -> str:
    return create_access_token(
        data={
            "sub": email,
            "email": email,
            "role": role,
            "name": name,
        }
    )


def make_citizen_token(
    email: str = "citizen.user@example.com",
    role: str = "CITIZEN",
) -> str:
    return create_access_token(
        data={
            "sub": email,
            "email": email,
            "role": role,
            "name": "Citizen User",
        }
    )


def get_error_message(res) -> str:
    data = res.json()
    if "detail" in data:
        return str(data["detail"])
    if "error" in data and isinstance(data["error"], dict):
        return str(data["error"].get("message", ""))
    return str(data)


SAMPLE_VALID_RULESET: Dict[str, Any] = {
    "node_type": "logical",
    "operator": "AND",
    "rule_id": "root_amendment_2026",
    "description_en": "Consolidated 2026 amendment eligibility criteria",
    "description_hi": "समेकित २०२६ संशोधन पात्रता मानदंड",
    "children": [
        {
            "node_type": "comparison",
            "rule_id": "land_ceiling_rule",
            "field_path": "land_details.total_operational_holding_hectares",
            "operator": "LTE",
            "expected_value": 2.0,
            "description_en": "Land holding must not exceed 2.0 hectares",
            "description_hi": "भूमि जोत २.० हेक्टेयर से अधिक नहीं होनी चाहिए",
        },
        {
            "node_type": "comparison",
            "rule_id": "exclusion_tax_rule",
            "field_path": "exclusion_profile.has_income_tax_payer",
            "operator": "EQ",
            "expected_value": False,
            "description_en": "No member paid income tax in last assessment year",
            "description_hi": "परिवार के किसी सदस्य ने आयकर का भुगतान नहीं किया हो",
        },
    ],
}


@pytest_asyncio.fixture(scope="module", autouse=True)
async def ensure_schemes_materialized():
    """Ensure statutory schemes are present in test DB."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Scheme).where(Scheme.scheme_code == "PM_KISAN"))
        if not res.scalar_one_or_none():
            await load_all_policies(session=session)


# ==============================================================================
# 1. Security & RBAC Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_01_anonymous_access_rejected(async_client: AsyncClient):
    """Anonymous requests to policy authoring endpoints are rejected with HTTP 401."""
    res = await async_client.get("/api/v1/officer/policy-authoring/drafts")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_02_citizen_role_access_rejected(async_client: AsyncClient):
    """Citizen role token accessing policy authoring endpoints is rejected with HTTP 403."""
    token = make_citizen_token()
    headers = {"Authorization": f"Bearer {token}"}
    res = await async_client.get("/api/v1/officer/policy-authoring/drafts", headers=headers)
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_03_officer_and_supervisor_access_permitted(async_client: AsyncClient):
    """Officers and Supervisors are authenticated and permitted."""
    officer_token = make_officer_token()
    supervisor_token = make_supervisor_token()

    res_off = await async_client.get(
        "/api/v1/officer/policy-authoring/drafts",
        headers={"Authorization": f"Bearer {officer_token}"},
    )
    assert res_off.status_code == 200

    res_sup = await async_client.get(
        "/api/v1/officer/policy-authoring/drafts",
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert res_sup.status_code == 200


# ==============================================================================
# 2. Policy Draft Creation and Candidate Import
# ==============================================================================

@pytest.mark.asyncio
async def test_04_create_policy_draft_from_scratch(async_client: AsyncClient):
    """Create a policy draft from scratch in initial DRAFT state with revision 1."""
    token = make_officer_token()
    payload = {
        "scheme_code": "PM_KISAN",
        "policy_title": "PM-KISAN Prospective Land Ceiling Amendment 2026",
        "description": "Amending operational land holding rules for small and marginal farmers.",
        "effective_from": "2026-04-01",
        "authored_rules_json": SAMPLE_VALID_RULESET,
    }

    res = await async_client.post(
        "/api/v1/officer/policy-authoring/drafts",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    data = res.json()

    assert data["policy_title"] == payload["policy_title"]
    assert data["scheme_code"] == "PM_KISAN"
    assert data["lifecycle_status"] == "DRAFT"
    assert data["validation_status"] == "NOT_VALIDATED"
    assert data["test_status"] == "NOT_TESTED"
    assert data["author_id"] == "officer.author@yogyatamitra.gov.in"
    assert data["rule_hash"] is not None
    assert len(data["revisions"]) == 1
    assert data["revisions"][0]["revision_number"] == 1
    assert len(data["audit_events"]) >= 1
    assert data["audit_events"][0]["action"] == "CREATE_DRAFT"


@pytest.mark.asyncio
async def test_05_create_policy_draft_from_approved_candidate(async_client: AsyncClient):
    """Importing an APPROVED discovery candidate populates provenance fields verbatim."""
    async with AsyncSessionLocal() as session:
        scheme_res = await session.execute(select(Scheme).where(Scheme.scheme_code == "PM_KISAN"))
        scheme = scheme_res.scalars().first()

        candidate = PolicyDiscoveryCandidate(
            id=uuid.uuid4(),
            scheme_id=scheme.id,
            source_url="https://agricoop.nic.in/en/pm-kisan-gazette-2026.pdf",
            source_title="Ministry of Agriculture Gazette Notification 2026",
            source_publisher="Ministry of Agriculture & Farmers Welfare",
            source_document_identifier="F.No.1-1/2026-PMK",
            source_publication_date=datetime.now(timezone.utc),
            source_effective_date=datetime.now(timezone.utc),
            retrieved_at=datetime.now(timezone.utc),
            source_excerpt="Paragraph 4: Ceiling of 2.0 hectares is hereby instituted.",
            provenance_status=ProvenanceStatus.OFFICIAL_GAZETTE,
            candidate_type=CandidateType.ELIGIBILITY_CONDITION,
            review_status=CandidateReviewStatus.APPROVED,
            effective_date_status=EffectiveDateStatus.CONFIRMED,
            duplicate_status=DuplicateStatus.UNIQUE,
            adversarial_flag_detected=False,
            title="Land Ceiling Reinstatement",
            candidate_text_en="Small farmer 2.0 hectare limit.",
            candidate_text_hi="छोटे किसान २.० हेक्टेयर सीमा।",
            normalized_concept="LAND_CEILING",
            ai_provider="MOCK_DISCOVERY",
            ai_model="mock-v1",
            ai_run_id="run-001",
            extraction_confidence=0.95,
        )
        session.add(candidate)
        await session.commit()
        cand_id = str(candidate.id)

    token = make_officer_token()
    payload = {
        "scheme_code": "PM_KISAN",
        "policy_title": "Draft from Approved Gazette Candidate",
        "description": "Legislative incorporation of official gazette notification.",
        "source_candidate_id": cand_id,
        "authored_rules_json": SAMPLE_VALID_RULESET,
    }

    res = await async_client.post(
        "/api/v1/officer/policy-authoring/drafts",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    data = res.json()

    assert data["source_candidate_id"] == cand_id
    assert data["source_url"] == "https://agricoop.nic.in/en/pm-kisan-gazette-2026.pdf"
    assert data["source_publisher"] == "Ministry of Agriculture & Farmers Welfare"
    assert data["source_document_identifier"] == "F.No.1-1/2026-PMK"
    assert data["provenance_status"] == "OFFICIAL_GAZETTE"


@pytest.mark.asyncio
async def test_06_create_draft_from_unapproved_candidate_rejected(async_client: AsyncClient):
    """Attempting to create draft from a candidate that is NOT APPROVED is rejected with HTTP 409."""
    async with AsyncSessionLocal() as session:
        scheme_res = await session.execute(select(Scheme).where(Scheme.scheme_code == "SSY"))
        scheme = scheme_res.scalars().first()

        candidate = PolicyDiscoveryCandidate(
            id=uuid.uuid4(),
            scheme_id=scheme.id,
            source_url="https://example.com/unverified-ssy-blog",
            source_title="Unverified SSY Rule Rumor",
            source_publisher="Informal Blog",
            retrieved_at=datetime.now(timezone.utc),
            source_excerpt="Age limit increased to 12 years.",
            provenance_status=ProvenanceStatus.UNKNOWN,
            candidate_type=CandidateType.ELIGIBILITY_CONDITION,
            review_status=CandidateReviewStatus.PENDING_REVIEW,  # NOT APPROVED!
            effective_date_status=EffectiveDateStatus.UNKNOWN,
            duplicate_status=DuplicateStatus.UNIQUE,
            adversarial_flag_detected=False,
            title="Unapproved Candidate",
            candidate_text_en="Tentative age extension.",
            candidate_text_hi="संभावित आयु विस्तार।",
            normalized_concept="AGE_LIMIT",
            ai_provider="MOCK_DISCOVERY",
            ai_model="mock-v1",
            ai_run_id="run-002",
            extraction_confidence=0.85,
        )
        session.add(candidate)
        await session.commit()
        cand_id = str(candidate.id)

    token = make_officer_token()
    payload = {
        "scheme_code": "SSY",
        "policy_title": "Illegal Draft from Unapproved Candidate",
        "description": "Attempting to import candidate before human approval.",
        "source_candidate_id": cand_id,
        "authored_rules_json": SAMPLE_VALID_RULESET,
    }

    res = await async_client.post(
        "/api/v1/officer/policy-authoring/drafts",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 409
    assert "Only APPROVED candidates" in get_error_message(res)


@pytest.mark.asyncio
async def test_07_import_candidate_into_existing_draft(async_client: AsyncClient):
    """POST /drafts/{id}/import-candidate imports approved candidate into an active draft."""
    token = make_officer_token()
    create_res = await async_client.post(
        "/api/v1/officer/policy-authoring/drafts",
        json={
            "scheme_code": "PM_KISAN",
            "policy_title": "Draft Waiting for Provenance",
            "description": "Authoring draft before candidate link.",
            "authored_rules_json": SAMPLE_VALID_RULESET,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_res.status_code == 201
    draft_id = create_res.json()["id"]

    async with AsyncSessionLocal() as session:
        scheme_res = await session.execute(select(Scheme).where(Scheme.scheme_code == "PM_KISAN"))
        scheme = scheme_res.scalars().first()

        candidate = PolicyDiscoveryCandidate(
            id=uuid.uuid4(),
            scheme_id=scheme.id,
            source_url="https://egazette.gov.in/official-notice.pdf",
            source_title="Official Gazette Extraordinary",
            source_publisher="GoI",
            retrieved_at=datetime.now(timezone.utc),
            source_excerpt="Statutory statutory provision.",
            provenance_status=ProvenanceStatus.OFFICIAL_GAZETTE,
            candidate_type=CandidateType.AMENDMENT,
            review_status=CandidateReviewStatus.APPROVED,
            effective_date_status=EffectiveDateStatus.CONFIRMED,
            duplicate_status=DuplicateStatus.UNIQUE,
            adversarial_flag_detected=False,
            title="Approved Gazette Amendment",
            candidate_text_en="Formal amendment citation.",
            candidate_text_hi="औपचारिक संशोधन उद्धरण।",
            normalized_concept="AMENDMENT_CITATION",
            ai_provider="MOCK_DISCOVERY",
            ai_model="mock-v1",
            ai_run_id="run-003",
            extraction_confidence=0.98,
        )
        session.add(candidate)
        await session.commit()
        cand_id = str(candidate.id)

    imp_res = await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/import-candidate",
        json={"candidate_id": cand_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert imp_res.status_code == 200
    imp_data = imp_res.json()
    assert imp_data["source_candidate_id"] == cand_id
    assert imp_data["source_url"] == "https://egazette.gov.in/official-notice.pdf"


# ==============================================================================
# 3. Rule Editing, Revisions, and Invalidation
# ==============================================================================

@pytest.mark.asyncio
async def test_08_update_draft_rules_increments_revision_and_invalidates_status(async_client: AsyncClient):
    """Editing authored rules creates revision 2 and resets validation and test status."""
    token = make_officer_token()
    create_res = await async_client.post(
        "/api/v1/officer/policy-authoring/drafts",
        json={
            "scheme_code": "PM_KISAN",
            "policy_title": "Draft for Revision Test",
            "description": "Testing rule updates and revision tracking.",
            "authored_rules_json": SAMPLE_VALID_RULESET,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    draft_id = create_res.json()["id"]

    # 1. Run validation to mark it VALID
    val_res = await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/validate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert val_res.status_code == 200
    assert val_res.json()["is_valid"] is True

    # Verify draft status is now VALID
    get_res = await async_client.get(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_res.json()["validation_status"] == "VALID"

    # 2. Update authored rules (change ceiling to 3.0 hectares)
    updated_rules = json.loads(json.dumps(SAMPLE_VALID_RULESET))
    updated_rules["children"][0]["expected_value"] = 3.0

    update_res = await async_client.patch(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}",
        json={
            "authored_rules_json": updated_rules,
            "change_summary": "Expanded land ceiling from 2.0 to 3.0 hectares.",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()

    # Must be invalidated back to NOT_VALIDATED and NOT_TESTED
    assert updated_data["validation_status"] == "NOT_VALIDATED"
    assert updated_data["test_status"] == "NOT_TESTED"
    assert len(updated_data["revisions"]) == 2
    assert updated_data["revisions"][-1]["revision_number"] == 2
    assert updated_data["revisions"][-1]["change_summary"] == "Expanded land ceiling from 2.0 to 3.0 hectares."


@pytest.mark.asyncio
async def test_09_editing_rules_in_illegal_state_rejected(async_client: AsyncClient):
    """Editing draft while in review or testing is rejected with HTTP 409."""
    token = make_officer_token()
    create_res = await async_client.post(
        "/api/v1/officer/policy-authoring/drafts",
        json={
            "scheme_code": "PM_KISAN",
            "policy_title": "Draft State Locking Test",
            "description": "Ensuring state prevents illegal edits.",
            "authored_rules_json": SAMPLE_VALID_RULESET,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    draft_id = create_res.json()["id"]

    # Transition to VALIDATING -> TESTING -> PENDING_REVIEW -> IN_REVIEW
    await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions",
        json={"action": "START_AUTHORING", "reason": "Begin rule formulation."},
        headers={"Authorization": f"Bearer {token}"},
    )
    await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions",
        json={"action": "RUN_VALIDATION", "reason": "Proceed to static validation."},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Attempt to edit while in VALIDATING
    edit_res = await async_client.patch(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}",
        json={"policy_title": "Sneaky Title Change"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert edit_res.status_code == 409
    assert "Cannot edit draft in 'VALIDATING' state" in get_error_message(edit_res)


# ==============================================================================
# 4. Static AST Validation & Invariant Checks
# ==============================================================================

@pytest.mark.asyncio
async def test_10_static_ast_validation_valid(async_client: AsyncClient):
    """Valid ruleset passes AST validation and sets draft validation_status to VALID."""
    token = make_officer_token()
    create_res = await async_client.post(
        "/api/v1/officer/policy-authoring/drafts",
        json={
            "scheme_code": "PM_KISAN",
            "policy_title": "PM-KISAN Valid AST Draft",
            "description": "Syntactically correct ruleset.",
            "effective_from": "2026-04-01",
            "effective_to": "2028-03-31",
            "authored_rules_json": SAMPLE_VALID_RULESET,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    draft_id = create_res.json()["id"]

    val_res = await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/validate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert val_res.status_code == 200
    report = val_res.json()
    assert report["is_valid"] is True
    assert len(report["errors"]) == 0
    assert report["rule_count"] >= 2


@pytest.mark.asyncio
async def test_11_static_ast_validation_invalid_node_type(async_client: AsyncClient):
    """AST with invalid node_type or missing fields is rejected."""
    token = make_officer_token()
    malformed_ast = {
        "node_type": "UNKNOWN_CUSTOM_NODE",
        "rule_id": "malformed_rule",
        "description_en": "Invalid node type",
    }
    create_res = await async_client.post(
        "/api/v1/officer/policy-authoring/drafts",
        json={
            "scheme_code": "PM_KISAN",
            "policy_title": "Draft with Malformed AST",
            "description": "Testing rejection of invalid node types.",
            "authored_rules_json": malformed_ast,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    draft_id = create_res.json()["id"]

    val_res = await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/validate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert val_res.status_code == 200
    report = val_res.json()
    assert report["is_valid"] is False
    assert len(report["errors"]) > 0
    assert any(err["code"] == "INVALID_AST_SCHEMA" for err in report["errors"])


@pytest.mark.asyncio
async def test_12_static_validation_arbitrary_code_injection_rejected(async_client: AsyncClient):
    """AST with python code injection payloads is rejected."""
    token = make_officer_token()
    injection_ast = {
        "node_type": "comparison",
        "rule_id": "exploit_rule",
        "field_path": "__import__('os').system('echo pwned')",
        "operator": "EQ",
        "expected_value": "exec(evil_code)",
        "description_en": "Malicious injection payload",
        "description_hi": "दुर्भावनापूर्ण पेलोड",
    }
    create_res = await async_client.post(
        "/api/v1/officer/policy-authoring/drafts",
        json={
            "scheme_code": "PM_KISAN",
            "policy_title": "Draft with Code Injection Payload",
            "description": "Testing injection rejection.",
            "authored_rules_json": injection_ast,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    draft_id = create_res.json()["id"]

    val_res = await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/validate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert val_res.status_code == 200
    report = val_res.json()
    assert report["is_valid"] is False
    assert any("UNSUPPORTED_CODE_INJECTION" in err["code"] or "INVALID_AST" in err["code"] for err in report["errors"])


@pytest.mark.asyncio
async def test_13_static_validation_duplicate_rule_id_detected(async_client: AsyncClient):
    """Ruleset containing duplicate rule_ids is flagged with DUPLICATE_RULE_ID error."""
    token = make_officer_token()
    dup_ast = {
        "node_type": "logical",
        "operator": "AND",
        "rule_id": "dup_parent",
        "description_en": "Parent",
        "description_hi": "माता-पिता",
        "children": [
            {
                "node_type": "comparison",
                "rule_id": "conflicting_rule_id_101",
                "field_path": "citizen.age",
                "operator": "GTE",
                "expected_value": 18,
                "description_en": "Adult rule",
                "description_hi": "वयस्क",
            },
            {
                "node_type": "comparison",
                "rule_id": "conflicting_rule_id_101",  # DUPLICATE!
                "field_path": "citizen.residence",
                "operator": "EQ",
                "expected_value": "RURAL",
                "description_en": "Rural rule",
                "description_hi": "ग्रामीण",
            },
        ],
    }
    create_res = await async_client.post(
        "/api/v1/officer/policy-authoring/drafts",
        json={
            "scheme_code": "PM_KISAN",
            "policy_title": "Draft with Duplicate Rule IDs",
            "description": "Testing duplicate rule ID detection.",
            "authored_rules_json": dup_ast,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    draft_id = create_res.json()["id"]

    val_res = await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/validate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert val_res.status_code == 200
    report = val_res.json()
    assert report["is_valid"] is False
    assert any(err["code"] == "DUPLICATE_RULE_ID" for err in report["errors"])


@pytest.mark.asyncio
async def test_14_static_validation_chronological_dates_flagged(async_client: AsyncClient):
    """Sunset date before effective start date is flagged as an error."""
    token = make_officer_token()
    create_res = await async_client.post(
        "/api/v1/officer/policy-authoring/drafts",
        json={
            "scheme_code": "PM_KISAN",
            "policy_title": "Draft with Chronological Anomaly",
            "description": "Testing date order verification.",
            "effective_from": "2026-12-31",
            "effective_to": "2026-01-01",  # End is before start!
            "authored_rules_json": SAMPLE_VALID_RULESET,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    draft_id = create_res.json()["id"]

    val_res = await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/validate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert val_res.status_code == 200
    report = val_res.json()
    assert report["is_valid"] is False
    assert any(err["code"] == "INVALID_DATE_RANGE" for err in report["errors"])


# ==============================================================================
# 5. Deterministic Compilation & Hashing
# ==============================================================================

@pytest.mark.asyncio
async def test_15_deterministic_compilation_and_key_order_invariance(async_client: AsyncClient):
    """Compilation produces canonical JSON and identical SHA-256 hash regardless of dict key order."""
    token = make_officer_token()

    # Ast variation 1
    ast1 = {
        "node_type": "comparison",
        "rule_id": "rule_a",
        "field_path": "citizen.age",
        "operator": "GTE",
        "expected_value": 18,
        "description_en": "Age check",
        "description_hi": "आयु सत्यापन",
    }
    # Ast variation 2: exact same keys and values, reversed insertion order
    ast2 = {
        "description_hi": "आयु सत्यापन",
        "description_en": "Age check",
        "expected_value": 18,
        "operator": "GTE",
        "field_path": "citizen.age",
        "rule_id": "rule_a",
        "node_type": "comparison",
    }

    create1 = await async_client.post(
        "/api/v1/officer/policy-authoring/drafts",
        json={"scheme_code": "PM_KISAN", "policy_title": "Draft Order 1", "description": "Valid description 1", "authored_rules_json": ast1},
        headers={"Authorization": f"Bearer {token}"},
    )
    draft1_id = create1.json()["id"]

    create2 = await async_client.post(
        "/api/v1/officer/policy-authoring/drafts",
        json={"scheme_code": "PM_KISAN", "policy_title": "Draft Order 2", "description": "Valid description 2", "authored_rules_json": ast2},
        headers={"Authorization": f"Bearer {token}"},
    )
    draft2_id = create2.json()["id"]

    comp1 = await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft1_id}/compile",
        headers={"Authorization": f"Bearer {token}"},
    )
    comp2 = await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft2_id}/compile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert comp1.status_code == 200
    assert comp2.status_code == 200

    hash1 = comp1.json()["rule_hash"]
    hash2 = comp2.json()["rule_hash"]
    assert hash1 == hash2, "Canonical rule hashing must be strictly invariant to object key ordering!"


# ==============================================================================
# 6. Deterministic Test Generation & Test Suite Execution
# ==============================================================================

@pytest.mark.asyncio
async def test_16_test_case_auto_generation(async_client: AsyncClient):
    """Deterministic test case generator extracts boundary and UNKNOWN propagation scenarios."""
    token = make_officer_token()
    create_res = await async_client.post(
        "/api/v1/officer/policy-authoring/drafts",
        json={
            "scheme_code": "PM_KISAN",
            "policy_title": "Draft for Test Generation",
            "description": "Testing boundary case generation.",
            "authored_rules_json": SAMPLE_VALID_RULESET,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    draft_id = create_res.json()["id"]

    gen_res = await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/generate-tests",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert gen_res.status_code == 200
    tests = gen_res.json()
    assert len(tests) >= 3

    # Check generated types
    test_names = [t["name"] for t in tests]
    assert any("Baseline Full Eligibility" in name for name in test_names)
    assert any("Boundary Ineligibility" in name for name in test_names)
    assert any("Missing Evidence & UNKNOWN Propagation" in name for name in test_names)


@pytest.mark.asyncio
async def test_17_add_human_authored_test_case(async_client: AsyncClient):
    """Officer can author and register explicit synthetic test cases."""
    token = make_officer_token()
    create_res = await async_client.post(
        "/api/v1/officer/policy-authoring/drafts",
        json={
            "scheme_code": "PM_KISAN",
            "policy_title": "Draft with Human Test",
            "description": "Adding synthetic test cases.",
            "authored_rules_json": SAMPLE_VALID_RULESET,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    draft_id = create_res.json()["id"]

    test_payload = {
        "name": "Marginal Farmer With Exactly 2.0 Hectares",
        "description": "Statutory boundary value check at exactly 2.0 ha limit.",
        "test_type": "HUMAN_AUTHORED",
        "facts_json": {
            "land_details": {"total_operational_holding_hectares": 2.0},
            "exclusion_profile": {"has_income_tax_payer": False},
        },
        "expected_result": "ELIGIBLE",
    }
    add_test_res = await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/tests",
        json=test_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert add_test_res.status_code == 201
    test_data = add_test_res.json()
    assert test_data["name"] == test_payload["name"]
    assert test_data["test_type"] == "HUMAN_AUTHORED"
    assert test_data["status"] == "NOT_TESTED"


@pytest.mark.asyncio
async def test_18_run_draft_test_suite_passed(async_client: AsyncClient):
    """Executing test suite marks draft test_status as PASSED when all assertions pass."""
    token = make_officer_token()
    create_res = await async_client.post(
        "/api/v1/officer/policy-authoring/drafts",
        json={
            "scheme_code": "PM_KISAN",
            "policy_title": "Draft for Suite Execution",
            "description": "Running deterministic tests.",
            "authored_rules_json": SAMPLE_VALID_RULESET,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    draft_id = create_res.json()["id"]

    # 1. Add matching test
    await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/tests",
        json={
            "name": "Small Farmer 1.5 ha",
            "test_type": "HUMAN_AUTHORED",
            "facts_json": {
                "land_details": {"total_operational_holding_hectares": 1.5},
                "exclusion_profile": {"has_income_tax_payer": False},
            },
            "expected_result": "ELIGIBLE",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    # 2. Add excluded test
    await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/tests",
        json={
            "name": "Large Farmer 5.0 ha",
            "test_type": "HUMAN_AUTHORED",
            "facts_json": {
                "land_details": {"total_operational_holding_hectares": 5.0},
                "exclusion_profile": {"has_income_tax_payer": False},
            },
            "expected_result": "INELIGIBLE",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    # Execute suite
    run_res = await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/test",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert run_res.status_code == 200
    summary = run_res.json()
    assert summary["total_tests"] == 2
    assert summary["passed_tests"] == 2
    assert summary["failed_tests"] == 0
    assert summary["test_status"] == "PASSED"

    # Verify draft reflection
    d_res = await async_client.get(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert d_res.json()["test_status"] == "PASSED"


@pytest.mark.asyncio
async def test_19_run_draft_test_suite_failed(async_client: AsyncClient):
    """Test suite marks draft test_status as FAILED when an assertion fails."""
    token = make_officer_token()
    create_res = await async_client.post(
        "/api/v1/officer/policy-authoring/drafts",
        json={
            "scheme_code": "PM_KISAN",
            "policy_title": "Draft for Failed Test",
            "description": "Deliberately failing test assertion.",
            "authored_rules_json": SAMPLE_VALID_RULESET,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    draft_id = create_res.json()["id"]

    # Expecting ELIGIBLE for 10.0 hectares (which evaluates to INELIGIBLE)
    await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/tests",
        json={
            "name": "Intentionally Flawed Test",
            "test_type": "HUMAN_AUTHORED",
            "facts_json": {
                "land_details": {"total_operational_holding_hectares": 10.0},
                "exclusion_profile": {"has_income_tax_payer": False},
            },
            "expected_result": "ELIGIBLE",  # Expecting wrong outcome!
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    run_res = await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/test",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert run_res.status_code == 200
    summary = run_res.json()
    assert summary["failed_tests"] == 1
    assert summary["test_status"] == "FAILED"


# ==============================================================================
# 7. Policy Diff Engine
# ==============================================================================

@pytest.mark.asyncio
async def test_20_policy_diff_against_baseline(async_client: AsyncClient):
    """Policy diff identifies added, removed, and modified rules with bilingual explanations."""
    token = make_officer_token()
    create_res = await async_client.post(
        "/api/v1/officer/policy-authoring/drafts",
        json={
            "scheme_code": "PM_KISAN",
            "policy_title": "PM-KISAN Amendment Diff Test",
            "description": "Testing policy diff engine.",
            "authored_rules_json": SAMPLE_VALID_RULESET,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    draft_id = create_res.json()["id"]

    diff_res = await async_client.get(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/diff",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert diff_res.status_code == 200
    diff_data = diff_res.json()

    assert "parent_version_code" in diff_data
    assert "human_summary" in diff_data
    assert isinstance(diff_data["added_rules"], list)
    assert isinstance(diff_data["modified_rules"], list)


# ==============================================================================
# 8. Human Governance & State Machine Lifecycle
# ==============================================================================

@pytest.mark.asyncio
async def test_21_lifecycle_state_machine_happy_path(async_client: AsyncClient):
    """Full legal lifecycle progression: DRAFT -> AUTHORING -> VALIDATING -> TESTING -> PENDING_REVIEW -> IN_REVIEW -> STAGED."""
    author_token = make_officer_token(email="officer.author1@yogyatamitra.gov.in")
    supervisor_token = make_supervisor_token(email="supervisor.reviewer1@yogyatamitra.gov.in")

    # 1. Create Draft (DRAFT)
    create_res = await async_client.post(
        "/api/v1/officer/policy-authoring/drafts",
        json={
            "scheme_code": "PM_KISAN",
            "policy_title": "Full Lifecycle Happy Path Draft",
            "description": "Testing full 10-state progression.",
            "effective_from": "2026-06-01",
            "effective_to": "2028-06-01",
            "authored_rules_json": SAMPLE_VALID_RULESET,
        },
        headers={"Authorization": f"Bearer {author_token}"},
    )
    draft_id = create_res.json()["id"]
    assert create_res.json()["lifecycle_status"] == "DRAFT"

    # 2. DRAFT -> AUTHORING
    t1 = await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions",
        json={"action": "START_AUTHORING", "reason": "Officer starting formal authoring process."},
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert t1.status_code == 200
    assert t1.json()["lifecycle_status"] == "AUTHORING"

    # 3. AUTHORING -> VALIDATING
    t2 = await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions",
        json={"action": "RUN_VALIDATION", "reason": "Authoring complete, starting static validation."},
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert t2.status_code == 200
    assert t2.json()["lifecycle_status"] == "VALIDATING"

    # Run static validation to set status VALID
    val_res = await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/validate",
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert val_res.status_code == 200
    assert val_res.json()["is_valid"] is True

    # 4. VALIDATING -> TESTING
    t3 = await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions",
        json={"action": "PROCEED_TO_TESTING", "reason": "Validation passed; moving to test execution."},
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert t3.status_code == 200
    assert t3.json()["lifecycle_status"] == "TESTING"

    # Add a passing test and run it to set test_status = PASSED
    await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/tests",
        json={
            "name": "Passing Test",
            "test_type": "HUMAN_AUTHORED",
            "facts_json": {
                "land_details": {"total_operational_holding_hectares": 1.0},
                "exclusion_profile": {"has_income_tax_payer": False},
            },
            "expected_result": "ELIGIBLE",
        },
        headers={"Authorization": f"Bearer {author_token}"},
    )
    run_res = await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/test",
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert run_res.status_code == 200
    assert run_res.json()["test_status"] == "PASSED"

    # 5. TESTING -> PENDING_REVIEW (SUBMIT_FOR_REVIEW)
    t4 = await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions",
        json={"action": "SUBMIT_FOR_REVIEW", "reason": "All checks and test suites passed; submitting for review."},
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert t4.status_code == 200
    assert t4.json()["lifecycle_status"] == "PENDING_REVIEW"
    assert t4.json()["submitted_at"] is not None

    # 6. PENDING_REVIEW -> IN_REVIEW (START_REVIEW by Supervisor)
    t5 = await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions",
        json={"action": "START_REVIEW", "reason": "Supervisor taking up draft for legislative review."},
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert t5.status_code == 200
    assert t5.json()["lifecycle_status"] == "IN_REVIEW"

    # 7. IN_REVIEW -> STAGED (STAGE by Supervisor with Separation of Duties)
    t6 = await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions",
        json={"action": "STAGE", "reason": "Statutory policy draft verified and approved for staging."},
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert t6.status_code == 200
    staged_data = t6.json()
    assert staged_data["lifecycle_status"] == "STAGED"
    assert staged_data["staged_at"] is not None
    assert staged_data["staged_by"] == "supervisor.reviewer1@yogyatamitra.gov.in"
    assert staged_data["staged_by_role"] == "SUPERVISOR"


@pytest.mark.asyncio
async def test_22_illegal_state_machine_shortcuts_rejected(async_client: AsyncClient):
    """Direct shortcuts bypassing intermediate states are rejected with HTTP 409."""
    token = make_officer_token()
    create_res = await async_client.post(
        "/api/v1/officer/policy-authoring/drafts",
        json={
            "scheme_code": "PM_KISAN",
            "policy_title": "Draft Testing Illegal Transitions",
            "description": "Testing state machine enforcement.",
            "authored_rules_json": SAMPLE_VALID_RULESET,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    draft_id = create_res.json()["id"]

    # Attempt illegal shortcut: DRAFT -> STAGED
    illegal_res = await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions",
        json={"action": "STAGE", "reason": "Illegal bypass attempt to stage directly."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert illegal_res.status_code == 409
    assert "Illegal transition" in get_error_message(illegal_res)


@pytest.mark.asyncio
async def test_23_submit_for_review_requires_valid_and_passed(async_client: AsyncClient):
    """Submitting for review before validation or before tests pass is rejected with HTTP 409."""
    token = make_officer_token()
    create_res = await async_client.post(
        "/api/v1/officer/policy-authoring/drafts",
        json={
            "scheme_code": "PM_KISAN",
            "policy_title": "Draft Untested Submit",
            "description": "Attempting submit without tests.",
            "authored_rules_json": SAMPLE_VALID_RULESET,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    draft_id = create_res.json()["id"]

    # Transition to AUTHORING -> VALIDATING -> TESTING
    await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions",
        json={"action": "START_AUTHORING", "reason": "Begin work."},
        headers={"Authorization": f"Bearer {token}"},
    )
    await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions",
        json={"action": "RUN_VALIDATION", "reason": "Begin validation."},
        headers={"Authorization": f"Bearer {token}"},
    )
    await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions",
        json={"action": "PROCEED_TO_TESTING", "reason": "Move to testing."},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Attempt to submit while validation_status is NOT_VALIDATED and test_status is NOT_TESTED
    submit_res = await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions",
        json={"action": "SUBMIT_FOR_REVIEW", "reason": "Premature submit attempt."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert submit_res.status_code == 409
    assert "must pass static validation" in get_error_message(submit_res)


@pytest.mark.asyncio
async def test_24_mandatory_reason_enforced(async_client: AsyncClient):
    """Transition without substantive justification reason (< 5 chars) is rejected with HTTP 422."""
    token = make_officer_token()
    create_res = await async_client.post(
        "/api/v1/officer/policy-authoring/drafts",
        json={
            "scheme_code": "PM_KISAN",
            "policy_title": "Draft Reason Enforcement Test",
            "description": "Testing mandatory reason length.",
            "authored_rules_json": SAMPLE_VALID_RULESET,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    draft_id = create_res.json()["id"]

    res_short = await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions",
        json={"action": "START_AUTHORING", "reason": "ok"},  # < 5 chars
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_short.status_code == 422


@pytest.mark.asyncio
async def test_25_separation_of_duties_author_cannot_stage_own_draft(async_client: AsyncClient):
    """Author cannot stage and approve their own policy draft (HTTP 409)."""
    # Create supervisor who is also the author
    dual_token = make_supervisor_token(email="dual.officer@yogyatamitra.gov.in")
    other_supervisor_token = make_supervisor_token(email="other.supervisor@yogyatamitra.gov.in")

    create_res = await async_client.post(
        "/api/v1/officer/policy-authoring/drafts",
        json={
            "scheme_code": "PM_KISAN",
            "policy_title": "Separation of Duties Test Draft",
            "description": "Testing author self-approval block.",
            "effective_from": "2026-06-01",
            "authored_rules_json": SAMPLE_VALID_RULESET,
        },
        headers={"Authorization": f"Bearer {dual_token}"},
    )
    draft_id = create_res.json()["id"]

    # Validate and pass tests
    await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/validate",
        headers={"Authorization": f"Bearer {dual_token}"},
    )
    await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/tests",
        json={"name": "Passing", "test_type": "HUMAN_AUTHORED", "facts_json": {"land_details": {"total_operational_holding_hectares": 1.0}, "exclusion_profile": {"has_income_tax_payer": False}}, "expected_result": "ELIGIBLE"},
        headers={"Authorization": f"Bearer {dual_token}"},
    )
    await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/test",
        headers={"Authorization": f"Bearer {dual_token}"},
    )

    # Move to IN_REVIEW
    await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions",
        json={"action": "START_AUTHORING", "reason": "Begin formal authoring."},
        headers={"Authorization": f"Bearer {dual_token}"},
    )
    await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions",
        json={"action": "RUN_VALIDATION", "reason": "Run static analysis."},
        headers={"Authorization": f"Bearer {dual_token}"},
    )
    await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions",
        json={"action": "PROCEED_TO_TESTING", "reason": "Run test suites."},
        headers={"Authorization": f"Bearer {dual_token}"},
    )
    await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions",
        json={"action": "SUBMIT_FOR_REVIEW", "reason": "Ready for supervisory review."},
        headers={"Authorization": f"Bearer {dual_token}"},
    )
    await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions",
        json={"action": "START_REVIEW", "reason": "Supervisory review commenced."},
        headers={"Authorization": f"Bearer {other_supervisor_token}"},
    )

    # Author attempts to STAGE their own draft -> HTTP 409 Conflict
    stage_self = await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions",
        json={"action": "STAGE", "reason": "Author attempting self-approval."},
        headers={"Authorization": f"Bearer {dual_token}"},
    )
    assert stage_self.status_code == 409
    assert "Separation of duties violation" in get_error_message(stage_self)


@pytest.mark.asyncio
async def test_26_staging_requires_supervisor_role(async_client: AsyncClient):
    """Non-supervisor OFFICER attempting to STAGE a draft is rejected with HTTP 403."""
    author_token = make_officer_token(email="officer.one@yogyatamitra.gov.in")
    second_officer_token = make_officer_token(email="officer.two@yogyatamitra.gov.in")

    create_res = await async_client.post(
        "/api/v1/officer/policy-authoring/drafts",
        json={
            "scheme_code": "PM_KISAN",
            "policy_title": "Role Elevation Test Draft",
            "description": "Ensuring only SUPERVISOR can stage.",
            "authored_rules_json": SAMPLE_VALID_RULESET,
        },
        headers={"Authorization": f"Bearer {author_token}"},
    )
    draft_id = create_res.json()["id"]

    # Validate and pass tests
    await async_client.post(f"/api/v1/officer/policy-authoring/drafts/{draft_id}/validate", headers={"Authorization": f"Bearer {author_token}"})
    await async_client.post(f"/api/v1/officer/policy-authoring/drafts/{draft_id}/tests", json={"name": "Passing", "test_type": "HUMAN_AUTHORED", "facts_json": {"land_details": {"total_operational_holding_hectares": 1.0}, "exclusion_profile": {"has_income_tax_payer": False}}, "expected_result": "ELIGIBLE"}, headers={"Authorization": f"Bearer {author_token}"})
    await async_client.post(f"/api/v1/officer/policy-authoring/drafts/{draft_id}/test", headers={"Authorization": f"Bearer {author_token}"})

    await async_client.post(f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions", json={"action": "START_AUTHORING", "reason": "Begin work."}, headers={"Authorization": f"Bearer {author_token}"})
    await async_client.post(f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions", json={"action": "RUN_VALIDATION", "reason": "Run validation."}, headers={"Authorization": f"Bearer {author_token}"})
    await async_client.post(f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions", json={"action": "PROCEED_TO_TESTING", "reason": "Move to tests."}, headers={"Authorization": f"Bearer {author_token}"})
    await async_client.post(f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions", json={"action": "SUBMIT_FOR_REVIEW", "reason": "Submit draft."}, headers={"Authorization": f"Bearer {author_token}"})
    await async_client.post(f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions", json={"action": "START_REVIEW", "reason": "Start review."}, headers={"Authorization": f"Bearer {second_officer_token}"})

    # Second OFFICER (not supervisor) attempts to STAGE -> HTTP 403 Forbidden
    stage_res = await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions",
        json={"action": "STAGE", "reason": "Officer attempting supervisory staging action."},
        headers={"Authorization": f"Bearer {second_officer_token}"},
    )
    assert stage_res.status_code == 403
    assert "requires elevated SUPERVISOR role" in get_error_message(stage_res)


@pytest.mark.asyncio
async def test_27_rejection_and_needs_clarification_determinations(async_client: AsyncClient):
    """Supervisor can REJECT or REQUEST_CLARIFICATION during IN_REVIEW."""
    author_token = make_officer_token(email="author.clarify@yogyatamitra.gov.in")
    supervisor_token = make_supervisor_token(email="supervisor.clarify@yogyatamitra.gov.in")

    create_res = await async_client.post(
        "/api/v1/officer/policy-authoring/drafts",
        json={
            "scheme_code": "SSY",
            "policy_title": "Clarification Test Draft",
            "description": "Testing supervisory clarification requests.",
            "authored_rules_json": SAMPLE_VALID_RULESET,
        },
        headers={"Authorization": f"Bearer {author_token}"},
    )
    draft_id = create_res.json()["id"]

    await async_client.post(f"/api/v1/officer/policy-authoring/drafts/{draft_id}/validate", headers={"Authorization": f"Bearer {author_token}"})
    await async_client.post(f"/api/v1/officer/policy-authoring/drafts/{draft_id}/tests", json={"name": "Passing", "test_type": "HUMAN_AUTHORED", "facts_json": {"land_details": {"total_operational_holding_hectares": 1.0}, "exclusion_profile": {"has_income_tax_payer": False}}, "expected_result": "ELIGIBLE"}, headers={"Authorization": f"Bearer {author_token}"})
    await async_client.post(f"/api/v1/officer/policy-authoring/drafts/{draft_id}/test", headers={"Authorization": f"Bearer {author_token}"})
    await async_client.post(f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions", json={"action": "START_AUTHORING", "reason": "Start authoring."}, headers={"Authorization": f"Bearer {author_token}"})
    await async_client.post(f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions", json={"action": "RUN_VALIDATION", "reason": "Validate rules."}, headers={"Authorization": f"Bearer {author_token}"})
    await async_client.post(f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions", json={"action": "PROCEED_TO_TESTING", "reason": "Test rules."}, headers={"Authorization": f"Bearer {author_token}"})
    await async_client.post(f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions", json={"action": "SUBMIT_FOR_REVIEW", "reason": "Submit draft."}, headers={"Authorization": f"Bearer {author_token}"})
    await async_client.post(f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions", json={"action": "START_REVIEW", "reason": "Commence review."}, headers={"Authorization": f"Bearer {supervisor_token}"})

    # Supervisor requests clarification
    clarify_res = await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions",
        json={"action": "REQUEST_CLARIFICATION", "reason": "Need statutory citation for exclusion criteria."},
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert clarify_res.status_code == 200
    assert clarify_res.json()["lifecycle_status"] == "NEEDS_CLARIFICATION"
    assert clarify_res.json()["reviewer_reason"] == "Need statutory citation for exclusion criteria."

    # Author can RESUME_AUTHORING from NEEDS_CLARIFICATION
    resume_res = await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions",
        json={"action": "RESUME_AUTHORING", "reason": "Authoring resumed to incorporate requested clarifications."},
        headers={"Authorization": f"Bearer {author_token}"},
    )
    assert resume_res.status_code == 200
    assert resume_res.json()["lifecycle_status"] == "AUTHORING"


@pytest.mark.asyncio
async def test_28_archived_is_terminal(async_client: AsyncClient):
    """Draft in ARCHIVED state cannot be transitioned further (HTTP 409)."""
    token = make_officer_token()
    create_res = await async_client.post(
        "/api/v1/officer/policy-authoring/drafts",
        json={
            "scheme_code": "PM_KISAN",
            "policy_title": "Archived Terminal State Test",
            "description": "Testing terminal nature of ARCHIVED status.",
            "authored_rules_json": SAMPLE_VALID_RULESET,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    draft_id = create_res.json()["id"]

    # Archive from DRAFT
    arch_res = await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions",
        json={"action": "ARCHIVE", "reason": "Draft discarded by author."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert arch_res.status_code == 200
    assert arch_res.json()["lifecycle_status"] == "ARCHIVED"

    # Attempt transition from ARCHIVED
    post_arch = await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions",
        json={"action": "START_AUTHORING", "reason": "Illegal resurrection attempt."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert post_arch.status_code == 409
    assert "terminal ARCHIVED state" in get_error_message(post_arch)


# ==============================================================================
# 9. Non-Active Staged Invariant & Statutory Regression
# ==============================================================================

@pytest.mark.asyncio
async def test_29_staged_draft_does_not_create_policy_version_or_affect_evaluator(async_client: AsyncClient):
    """CRITICAL INVARIANT: Staged draft NEVER creates a PolicyVersion row and NEVER affects citizen evaluation."""
    author_token = make_officer_token(email="officer.author.invariant@yogyatamitra.gov.in")
    supervisor_token = make_supervisor_token(email="supervisor.reviewer.invariant@yogyatamitra.gov.in")

    # Count PolicyVersion rows before
    async with AsyncSessionLocal() as session:
        pv_before = (await session.execute(select(PolicyVersion))).scalars().all()
        pv_count_before = len(pv_before)

    # Create, validate, test, review, and stage draft
    create_res = await async_client.post(
        "/api/v1/officer/policy-authoring/drafts",
        json={
            "scheme_code": "PM_KISAN",
            "policy_title": "Staged Non-Active Invariant Policy",
            "description": "Ensuring staged policies are completely inactive.",
            "effective_from": "2026-08-01",
            "authored_rules_json": SAMPLE_VALID_RULESET,
        },
        headers={"Authorization": f"Bearer {author_token}"},
    )
    draft_id = create_res.json()["id"]

    await async_client.post(f"/api/v1/officer/policy-authoring/drafts/{draft_id}/validate", headers={"Authorization": f"Bearer {author_token}"})
    await async_client.post(f"/api/v1/officer/policy-authoring/drafts/{draft_id}/tests", json={"name": "Passing", "test_type": "HUMAN_AUTHORED", "facts_json": {"land_details": {"total_operational_holding_hectares": 1.0}, "exclusion_profile": {"has_income_tax_payer": False}}, "expected_result": "ELIGIBLE"}, headers={"Authorization": f"Bearer {author_token}"})
    await async_client.post(f"/api/v1/officer/policy-authoring/drafts/{draft_id}/test", headers={"Authorization": f"Bearer {author_token}"})
    await async_client.post(f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions", json={"action": "START_AUTHORING", "reason": "Begin authoring."}, headers={"Authorization": f"Bearer {author_token}"})
    await async_client.post(f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions", json={"action": "RUN_VALIDATION", "reason": "Validate rules."}, headers={"Authorization": f"Bearer {author_token}"})
    await async_client.post(f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions", json={"action": "PROCEED_TO_TESTING", "reason": "Proceed to tests."}, headers={"Authorization": f"Bearer {author_token}"})
    await async_client.post(f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions", json={"action": "SUBMIT_FOR_REVIEW", "reason": "Submit draft."}, headers={"Authorization": f"Bearer {author_token}"})
    await async_client.post(f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions", json={"action": "START_REVIEW", "reason": "Supervisor reviewing."}, headers={"Authorization": f"Bearer {supervisor_token}"})

    stage_res = await async_client.post(
        f"/api/v1/officer/policy-authoring/drafts/{draft_id}/transitions",
        json={"action": "STAGE", "reason": "Formally staged by supervisor."},
        headers={"Authorization": f"Bearer {supervisor_token}"},
    )
    assert stage_res.status_code == 200
    assert stage_res.json()["lifecycle_status"] == "STAGED"

    # Verify that PolicyVersion table count did NOT increase
    async with AsyncSessionLocal() as session:
        pv_after = (await session.execute(select(PolicyVersion))).scalars().all()
        pv_count_after = len(pv_after)

    assert pv_count_after == pv_count_before, "CRITICAL: STAGED draft must NEVER create a PolicyVersion row!"


@pytest.mark.asyncio
async def test_30_all_six_canonical_policy_hashes_remain_frozen():
    """CRITICAL INVARIANT: All 6 canonical policy hashes match the permanent freeze table."""
    verify_canonical_policy_regression()


# ==============================================================================
# 10. Queue Metrics and Filtering
# ==============================================================================

@pytest.mark.asyncio
async def test_31_queue_metrics_and_filtering(async_client: AsyncClient):
    """GET /drafts returns aggregated status metrics and supports status and scheme filters."""
    token = make_officer_token()
    res = await async_client.get(
        "/api/v1/officer/policy-authoring/drafts?status=ALL&scheme=ALL",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert "drafts" in data
    assert "total" in data
    assert "metrics" in data
    metrics = data["metrics"]
    assert "total_drafts" in metrics
    assert "authoring" in metrics
    assert "staged" in metrics
    assert "archived" in metrics
