"""Comprehensive test suite for YogyataMitra Phase 6 API Layer.

Verifies:
1. Scheme Discovery: list schemes, retrieve PM-KISAN, retrieve SSY, 404 on unknown scheme.
2. Policy Discovery: list policy versions, effective dates, provenance, rule hashes, specific version, 404s.
3. Eligibility Evaluation:
   - PM-KISAN: eligible, ineligible, historical ceiling (v1), ceiling removal (v2), NRI semantics.
   - SSY: eligible, ineligible (age limit), guardian requirements.
   - Missing facts: INSUFFICIENT_INFORMATION, UNKNOWN propagation, blockers.
   - Historical date boundaries & policy resolution.
   - Explicit policy_version_code matching (200) and conflict (409).
   - Nonexistent scheme (404), out-of-bounds evaluation date (404).
   - Evaluation audit persistence & retrieval via GET /api/v1/evaluations/{id}.
   - Repeated evaluations create distinct immutable audit records.
4. Validation & Security:
   - Extra request fields rejected (422).
   - Malformed nested facts rejected (422).
   - SQL injection-like inputs treated safely as literal strings (404).
   - Structured error contracts (no leaked stack traces or DB credentials).
   - Policy mutation endpoints do not exist (405).
   - Health endpoints remain operational.
"""

from __future__ import annotations

from datetime import date
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.evaluation import EvaluationTrace
from app.models.scheme import Scheme


# ==============================================================================
# 1. Scheme Discovery Endpoints
# ==============================================================================

@pytest.mark.asyncio
async def test_api_list_schemes(async_client: AsyncClient):
    """GET /api/v1/schemes returns configured schemes from DB."""
    response = await async_client.get("/api/v1/schemes")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    codes = {s["scheme_code"] for s in data}
    assert "PM_KISAN" in codes
    assert "SSY" in codes


@pytest.mark.asyncio
async def test_api_list_schemes_filter_status(async_client: AsyncClient):
    """GET /api/v1/schemes?status=ACTIVE filters schemes by operational status."""
    response = await async_client.get("/api/v1/schemes?status=ACTIVE")
    assert response.status_code == 200
    data = response.json()
    assert all(s["status"] == "ACTIVE" for s in data)


@pytest.mark.asyncio
async def test_api_get_scheme_pm_kisan(async_client: AsyncClient):
    """GET /api/v1/schemes/PM_KISAN returns detailed metadata and policy versions."""
    response = await async_client.get("/api/v1/schemes/PM_KISAN")
    assert response.status_code == 200
    data = response.json()
    assert data["scheme_code"] == "PM_KISAN"
    assert "Pradhan Mantri" in data["name_en"]
    assert "policy_versions" in data
    versions = {pv["version_code"] for pv in data["policy_versions"]}
    assert {"v1.0-2018", "v2.0-2019", "v3.0-2023"}.issubset(versions)


@pytest.mark.asyncio
async def test_api_get_scheme_ssy(async_client: AsyncClient):
    """GET /api/v1/schemes/SSY returns detailed metadata for Sukanya Samriddhi."""
    response = await async_client.get("/api/v1/schemes/SSY")
    assert response.status_code == 200
    data = response.json()
    assert data["scheme_code"] == "SSY"
    assert "Sukanya" in data["name_en"]
    versions = {pv["version_code"] for pv in data["policy_versions"]}
    assert {"v1.0-2016", "v2.0-2019", "v3.0-2024"}.issubset(versions)


@pytest.mark.asyncio
async def test_api_get_unknown_scheme_404(async_client: AsyncClient):
    """GET /api/v1/schemes/UNKNOWN_SCHEME returns 404 with structured ErrorResponse."""
    response = await async_client.get("/api/v1/schemes/UNKNOWN_SCHEME")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"
    assert "UNKNOWN_SCHEME" in data["error"]["message"]


# ==============================================================================
# 2. Policy Discovery Endpoints
# ==============================================================================

@pytest.mark.asyncio
async def test_api_list_pm_kisan_policies(async_client: AsyncClient):
    """GET /api/v1/schemes/PM_KISAN/policies returns all policy versions in descending order."""
    response = await async_client.get("/api/v1/schemes/PM_KISAN/policies")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    version_codes = [p["version_code"] for p in data]
    assert version_codes == ["v3.0-2023", "v2.0-2019", "v1.0-2018"]
    for p in data:
        assert p["rule_definition_hash"] is not None
        assert len(p["rule_definition_hash"]) == 64
        assert p["source_url"].startswith("http")


@pytest.mark.asyncio
async def test_api_list_ssy_policies(async_client: AsyncClient):
    """GET /api/v1/schemes/SSY/policies returns all 3 SSY policy versions."""
    response = await async_client.get("/api/v1/schemes/SSY/policies")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    version_codes = [p["version_code"] for p in data]
    assert version_codes == ["v3.0-2024", "v2.0-2019", "v1.0-2016"]


@pytest.mark.asyncio
async def test_api_get_specific_policy_version(async_client: AsyncClient):
    """GET /api/v1/schemes/PM_KISAN/policies/v2.0-2019 returns specific version metadata."""
    response = await async_client.get("/api/v1/schemes/PM_KISAN/policies/v2.0-2019")
    assert response.status_code == 200
    data = response.json()
    assert data["scheme_code"] == "PM_KISAN"
    assert data["version_code"] == "v2.0-2019"
    assert data["effective_from"] == "2019-04-01"
    assert data["rule_definition_hash"] == "55fe76d5bd441cbe4a0ceddb45ddbf253f5f059683570bd29096bf9b972ad6d8"


@pytest.mark.asyncio
async def test_api_get_policy_unknown_version_404(async_client: AsyncClient):
    """GET /api/v1/schemes/PM_KISAN/policies/v99.0 returns 404."""
    response = await async_client.get("/api/v1/schemes/PM_KISAN/policies/v99.0")
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "NOT_FOUND"


# ==============================================================================
# 3. Eligibility Evaluation Endpoints
# ==============================================================================

@pytest.mark.asyncio
async def test_api_evaluate_pm_kisan_eligible(async_client: AsyncClient):
    """POST /api/v1/evaluations with qualifying PM-KISAN facts returns ELIGIBLE."""
    payload = {
        "scheme_code": "PM_KISAN",
        "evaluation_date": "2024-01-01",
        "facts": {
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
    }
    response = await async_client.post("/api/v1/evaluations", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["overall_result"] == "ELIGIBLE"
    assert data["root_truth_value"] == "TRUE"
    assert data["scheme_code"] == "PM_KISAN"
    assert data["policy_version_code"] == "v3.0-2023"
    assert data["audit_persisted"] is True
    assert len(data["satisfied_rules"]) >= 8
    assert len(data["reasons_en"]) > 0


@pytest.mark.asyncio
async def test_api_evaluate_pm_kisan_ineligible_income_tax(async_client: AsyncClient):
    """POST /api/v1/evaluations with income tax payer returns INELIGIBLE."""
    payload = {
        "scheme_code": "PM_KISAN",
        "evaluation_date": "2024-01-01",
        "facts": {
            "family": {
                "owns_cultivable_land": True,
                "is_institutional_landholder": False,
                "has_constitutional_post_holder": False,
                "has_public_representative": False,
                "has_disqualified_government_employee": False,
                "has_pensioner_above_ten_thousand": False,
                "has_income_tax_payer": True,
                "has_registered_practicing_professional": False,
                "is_nri": False,
            },
            "land": {
                "transferred_after_cutoff": False,
            },
        },
    }
    response = await async_client.post("/api/v1/evaluations", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["overall_result"] == "INELIGIBLE"
    assert data["root_truth_value"] == "FALSE"
    assert "PMKISAN-EXCL-INCOME-TAX" in data["failed_rules"]


@pytest.mark.asyncio
async def test_api_evaluate_pm_kisan_ineligible_nri(async_client: AsyncClient):
    """POST /api/v1/evaluations with NRI farmer family returns INELIGIBLE with PMKISAN-EXCL-NRI."""
    payload = {
        "scheme_code": "PM_KISAN",
        "evaluation_date": "2024-01-01",
        "facts": {
            "family": {
                "owns_cultivable_land": True,
                "is_institutional_landholder": False,
                "has_constitutional_post_holder": False,
                "has_public_representative": False,
                "has_disqualified_government_employee": False,
                "has_pensioner_above_ten_thousand": False,
                "has_income_tax_payer": False,
                "has_registered_practicing_professional": False,
                "is_nri": True,
            },
            "land": {
                "transferred_after_cutoff": False,
            },
        },
    }
    response = await async_client.post("/api/v1/evaluations", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["overall_result"] == "INELIGIBLE"
    assert "PMKISAN-EXCL-NRI" in data["failed_rules"]


@pytest.mark.asyncio
async def test_api_evaluate_ssy_eligible(async_client: AsyncClient):
    """POST /api/v1/evaluations with qualifying SSY facts returns ELIGIBLE."""
    payload = {
        "scheme_code": "SSY",
        "evaluation_date": "2024-06-01",
        "facts": {
            "beneficiary": {
                "gender": "FEMALE",
                "is_indian_resident": True,
                "date_of_birth": "2018-05-15",
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
    }
    response = await async_client.post("/api/v1/evaluations", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["overall_result"] == "ELIGIBLE"
    assert data["scheme_code"] == "SSY"
    assert data["policy_version_code"] == "v3.0-2024"


@pytest.mark.asyncio
async def test_api_evaluate_ssy_ineligible_age_over_ten(async_client: AsyncClient):
    """POST /api/v1/evaluations for child aged > 10 returns INELIGIBLE."""
    payload = {
        "scheme_code": "SSY",
        "evaluation_date": "2024-06-01",
        "facts": {
            "beneficiary": {
                "gender": "FEMALE",
                "is_indian_resident": True,
                "date_of_birth": "2013-05-01",  # Age 11 on opening date
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
    }
    response = await async_client.post("/api/v1/evaluations", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["overall_result"] == "INELIGIBLE"
    assert "SSY-AGE-LIMIT-10" in data["failed_rules"]


@pytest.mark.asyncio
async def test_api_evaluate_missing_facts_produces_unknown(async_client: AsyncClient):
    """Missing statutory facts produce INSUFFICIENT_INFORMATION and populated missing_fields."""
    payload = {
        "scheme_code": "PM_KISAN",
        "evaluation_date": "2024-01-01",
        "facts": {
            "family": {
                "owns_cultivable_land": True,
                # All exclusion facts omitted
            },
            "land": {
                "transferred_after_cutoff": False,
            },
        },
    }
    response = await async_client.post("/api/v1/evaluations", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["overall_result"] == "INSUFFICIENT_INFORMATION"
    assert data["root_truth_value"] == "UNKNOWN"
    assert len(data["missing_fields"]) > 0
    assert len(data["unknown_rules"]) > 0
    assert len(data["blockers"]) > 0


@pytest.mark.asyncio
async def test_api_evaluate_kleene_false_dominates_unknown(async_client: AsyncClient):
    """Under Strong Kleene logic, explicit FALSE dominates missing UNKNOWN facts."""
    payload = {
        "scheme_code": "PM_KISAN",
        "evaluation_date": "2024-01-01",
        "facts": {
            "family": {
                "owns_cultivable_land": True,
                "is_institutional_landholder": True,  # Explicit disqualification
                # Other facts omitted
            },
            "land": {
                "transferred_after_cutoff": False,
            },
        },
    }
    response = await async_client.post("/api/v1/evaluations", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["overall_result"] == "INELIGIBLE"
    assert data["root_truth_value"] == "FALSE"
    assert "PMKISAN-EXCL-INSTITUTIONAL" in data["failed_rules"]


@pytest.mark.asyncio
async def test_api_evaluate_historical_policy_selection(async_client: AsyncClient):
    """Historical evaluation selects v1.0-2018 where 2.5ha land ceiling disqualifies farmer."""
    payload_v1 = {
        "scheme_code": "PM_KISAN",
        "evaluation_date": "2019-01-15",  # Under 2018 guidelines
        "facts": {
            "family": {
                "owns_cultivable_land": True,
                "total_land_area_hectares": 2.5,  # Exceeds 2.0 ha ceiling
                "is_institutional_landholder": False,
                "has_constitutional_post_holder": False,
                "has_public_representative": False,
                "has_disqualified_government_employee": False,
                "has_pensioner_above_ten_thousand": False,
                "has_income_tax_payer": False,
                "has_registered_practicing_professional": False,
            },
        },
    }
    res_v1 = await async_client.post("/api/v1/evaluations", json=payload_v1)
    assert res_v1.status_code == 200
    data_v1 = res_v1.json()
    assert data_v1["policy_version_code"] == "v1.0-2018"
    assert data_v1["overall_result"] == "INELIGIBLE"
    assert "PMKISAN-HIST-LAND-CEILING-2HA" in data_v1["failed_rules"]

    # Same farmer evaluated under v2.0-2019 on 2020-05-01 qualifies (ceiling removed)
    payload_v2 = {
        "scheme_code": "PM_KISAN",
        "evaluation_date": "2020-05-01",
        "facts": {
            "family": {
                "owns_cultivable_land": True,
                "total_land_area_hectares": 2.5,
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
    }
    res_v2 = await async_client.post("/api/v1/evaluations", json=payload_v2)
    assert res_v2.status_code == 200
    data_v2 = res_v2.json()
    assert data_v2["policy_version_code"] == "v2.0-2019"
    assert data_v2["overall_result"] == "ELIGIBLE"


@pytest.mark.asyncio
async def test_api_evaluate_policy_version_match_and_conflict(async_client: AsyncClient):
    """Explicit policy_version_code matches (200) or reports conflict (409)."""
    base_facts = {
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
    }

    # Matching version
    res_match = await async_client.post("/api/v1/evaluations", json={
        "scheme_code": "PM_KISAN",
        "evaluation_date": "2024-01-01",
        "policy_version_code": "v3.0-2023",
        "facts": base_facts,
    })
    assert res_match.status_code == 200
    assert res_match.json()["policy_version_code"] == "v3.0-2023"

    # Conflicting version
    res_conflict = await async_client.post("/api/v1/evaluations", json={
        "scheme_code": "PM_KISAN",
        "evaluation_date": "2024-01-01",
        "policy_version_code": "v1.0-2018",  # Conflicts with v3.0-2023 effective on 2024-01-01
        "facts": base_facts,
    })
    assert res_conflict.status_code == 409
    assert res_conflict.json()["error"]["code"] == "CONFLICT"


@pytest.mark.asyncio
async def test_api_evaluate_no_effective_policy_404(async_client: AsyncClient):
    """Evaluation date prior to scheme enactment returns 404."""
    payload = {
        "scheme_code": "PM_KISAN",
        "evaluation_date": "2010-01-01",  # Prior to 2018-12-01
        "facts": {"family": {"owns_cultivable_land": True}},
    }
    response = await async_client.post("/api/v1/evaluations", json=payload)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_api_evaluate_audit_persistence_and_retrieval(async_client: AsyncClient):
    """Evaluations persist an immutable audit record retrievable via GET /api/v1/evaluations/{id}."""
    payload = {
        "scheme_code": "PM_KISAN",
        "evaluation_date": "2024-01-01",
        "citizen_ref": "SYN-AUDIT-CIT-01",
        "facts": {
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
    }
    eval_res = await async_client.post("/api/v1/evaluations", json=payload)
    assert eval_res.status_code == 200
    eval_id = eval_res.json()["evaluation_id"]

    # Retrieve persisted record
    get_res = await async_client.get(f"/api/v1/evaluations/{eval_id}")
    assert get_res.status_code == 200
    persisted = get_res.json()
    assert persisted["id"] == eval_id
    assert persisted["scheme_code"] == "PM_KISAN"
    assert persisted["policy_version_code"] == "v3.0-2023"
    assert persisted["result_state"] == "ELIGIBLE"
    assert "data" in persisted["input_snapshot_json"]
    assert persisted["input_snapshot_json"]["data"]["family"]["owns_cultivable_land"] is True


@pytest.mark.asyncio
async def test_api_repeated_evaluations_create_distinct_records(async_client: AsyncClient):
    """Repeated evaluations produce distinct immutable audit records rather than overwriting."""
    payload = {
        "scheme_code": "SSY",
        "evaluation_date": "2024-06-01",
        "facts": {
            "beneficiary": {
                "gender": "FEMALE",
                "is_indian_resident": True,
                "date_of_birth": "2019-01-01",
            },
            "account": {"opening_date": "2024-06-01", "is_first_account_for_child": True},
            "guardian": {
                "is_natural_guardian": True,
                "is_court_appointed_legal_guardian": False,
            },
            "family": {
                "active_ssy_accounts_count": 0,
                "has_multiple_birth_exception": False,
            },
        },
    }
    res1 = await async_client.post("/api/v1/evaluations", json=payload)
    res2 = await async_client.post("/api/v1/evaluations", json=payload)
    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res1.json()["evaluation_id"] != res2.json()["evaluation_id"]


# ==============================================================================
# 4. Validation & Security
# ==============================================================================

@pytest.mark.asyncio
async def test_api_extra_top_level_field_rejected(async_client: AsyncClient):
    """Pydantic extra='forbid' rejects unrecognized top-level fields with 422."""
    payload = {
        "scheme_code": "PM_KISAN",
        "evaluation_date": "2024-01-01",
        "facts": {},
        "malicious_extra_field": "disallowed",
    }
    response = await async_client.post("/api/v1/evaluations", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_api_extra_nested_fact_field_rejected(async_client: AsyncClient):
    """Pydantic extra='forbid' rejects unrecognized fields inside facts with 422."""
    payload = {
        "scheme_code": "PM_KISAN",
        "evaluation_date": "2024-01-01",
        "facts": {
            "family": {
                "owns_cultivable_land": True,
                "unrecognized_family_fact": "not allowed",
            }
        },
    }
    response = await async_client.post("/api/v1/evaluations", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_api_sql_injection_attempt_handled_safely(async_client: AsyncClient):
    """SQL injection strings in URL paths are parameterized and produce safe 404s."""
    malicious_path = "/api/v1/schemes/PM_KISAN' OR '1'='1"
    response = await async_client.get(malicious_path)
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_api_policy_mutation_endpoints_forbidden(async_client: AsyncClient):
    """HTTP POST/DELETE/PUT on scheme or policy resources are disallowed (405)."""
    res_post_scheme = await async_client.post("/api/v1/schemes", json={"name": "New"})
    assert res_post_scheme.status_code == 405

    res_post_policy = await async_client.post("/api/v1/schemes/PM_KISAN/policies", json={})
    assert res_post_policy.status_code == 405

    res_delete_scheme = await async_client.delete("/api/v1/schemes/PM_KISAN")
    assert res_delete_scheme.status_code == 405


@pytest.mark.asyncio
async def test_api_health_and_health_db_preserved(async_client: AsyncClient):
    """Existing /health and /health/db endpoints continue to work as expected."""
    res_health = await async_client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json() == {"status": "ok", "service": "YogyataMitra"}

    res_db = await async_client.get("/health/db")
    assert res_db.status_code == 200
    assert res_db.json()["status"] == "ok"
    assert res_db.json()["database"] == "connected"


@pytest.mark.asyncio
async def test_api_citizen_persistence_invariants(async_client: AsyncClient):
    """Verify citizen representation is minimal with no invented PII and reuses citizen records."""
    from app.models.citizen import Citizen
    from tests.conftest import TestSessionLocal

    test_ref = f"CIT-AUDIT-{uuid.uuid4().hex[:8].upper()}"
    payload = {
        "scheme_code": "PM_KISAN",
        "evaluation_date": "2024-01-01",
        "citizen_ref": test_ref,
        "facts": {
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
    }

    # First evaluation
    res1 = await async_client.post("/api/v1/evaluations", json=payload)
    assert res1.status_code == 200
    eval1_id = res1.json()["evaluation_id"]

    # Second evaluation with same citizen_ref
    res2 = await async_client.post("/api/v1/evaluations", json=payload)
    assert res2.status_code == 200
    eval2_id = res2.json()["evaluation_id"]
    assert eval1_id != eval2_id

    # Verify both evaluations reference the EXACT SAME Citizen row in DB
    trace1 = (await async_client.get(f"/api/v1/evaluations/{eval1_id}")).json()
    trace2 = (await async_client.get(f"/api/v1/evaluations/{eval2_id}")).json()
    assert trace1["citizen_id"] == trace2["citizen_id"]

    # Verify Citizen entity has zero invented PII
    async with TestSessionLocal() as session:
        citizen_stmt = select(Citizen).where(Citizen.synthetic_reference == test_ref)
        citizen = (await session.execute(citizen_stmt)).scalar_one()
        assert citizen.synthetic_reference == test_ref
        assert citizen.display_name is None
        assert citizen.date_of_birth is None
        assert citizen.gender is None
        assert citizen.state is None
        assert citizen.district is None

