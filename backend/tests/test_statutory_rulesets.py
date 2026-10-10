"""Phase 5 Comprehensive Statutory Rulesets Test Suite.

Verifies:
- Requirements A through AJ and Section 26A test matrix
- PM-KISAN (v1.0-2018, v2.0-2019, v3.0-2023)
- SSY (v1.0-2016, v2.0-2019, v3.0-2024)
- Deterministic canonical hashing and anti-collision properties
- Statutory age, landholding, cut-off, succession, exclusion, and family constraints
- Strong Kleene UNKNOWN semantics on missing statutory facts
- Idempotent database materialization and strict PolicyHashConflictError enforcement
- Generic policy selection service across historical date boundaries
- End-to-end integration with DeterministicEvaluator, Explainability, and Audit records
- Scheme-agnostic generic evaluator integrity (zero scheme-specific branches)
"""

from __future__ import annotations

import asyncio
import copy
from datetime import date, datetime
import json
from pathlib import Path
import uuid
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import TestSessionLocal as AsyncSessionLocal
from app.engine.ast.nodes import ComparisonNode, LogicalNode, RuleASTNode, TemporalNode
from app.engine.ast.operators import ComparisonOperator, LogicalOperator, TemporalOperator
from app.engine.ast.validation import validate_ast
from app.engine.evaluator.context import EvaluationContext
from app.engine.evaluator.evaluator import DeterministicEvaluator
from app.engine.explainability.audit import create_audit_evaluation_record
from app.engine.explainability.provenance import PolicyProvenance, compute_canonical_rule_hash
from app.engine.explainability.trace_builder import build_explainability_trace
from app.engine.types import RuleTruthValue
from app.models.enums import EligibilityResult, SchemeStatus
from app.models.evaluation import EvaluationTrace
from app.models.scheme import PolicyVersion, RuleSet, Scheme
from app.services.policy_loader import (
    PolicyHashConflictError,
    PolicyValidationError,
    SchemeNotFoundError,
    discover_schemes_and_policies,
    get_default_schemes_data_dir,
    load_all_policies,
    load_policy_version,
    load_scheme,
)
from app.services.policy_selector import (
    PolicyVersionNotFoundError,
    get_policy_rule_ast,
    get_policy_version,
    select_policy_version,
)


# ==============================================================================
# Helper Functions & Fixtures
# ==============================================================================

@pytest_asyncio.fixture(scope="function", autouse=True)
async def ensure_statutory_database():
    """Ensure statutory policies are materialized into PostgreSQL for integration tests."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Scheme).where(Scheme.scheme_code == "PM_KISAN"))
        if not res.scalar_one_or_none():
            await load_all_policies(session=session)


@pytest.fixture(scope="module")
def schemes_data_dir() -> Path:
    """Path to the schemes_data directory."""
    return get_default_schemes_data_dir()


@pytest.fixture(scope="module")
def discovered_data(schemes_data_dir: Path):
    """Discovered schemes and policy files."""
    return discover_schemes_and_policies(schemes_data_dir)


# ==============================================================================
# A - H: Ingestion, Structure, Metadata & AST Integrity
# ==============================================================================

def test_a_all_six_policy_files_load(discovered_data):
    """Requirement A: All statutory policy files load successfully from disk (14 versions across 10 schemes)."""
    total_policies = sum(len(policies) for _, policies in discovered_data.values())
    assert total_policies == 14


def test_b_exactly_two_schemes_exist(discovered_data):
    """Requirement B: All 10 statutory schemes exist."""
    assert len(discovered_data) == 10
    scheme_codes = set(discovered_data.keys())
    assert scheme_codes == {
        "PM_KISAN", "SSY", "PM_KMY", "PMUY", "PM_VISHWAKARMA",
        "PMAY_G", "PMAY_U_2_0", "PM_SVANIDHI", "PMMVY", "IGNOAPS"
    }


def test_c_pm_kisan_has_exactly_three_policy_versions(discovered_data):
    """Requirement C: PM-KISAN has exactly three versions: v1.0-2018, v2.0-2019, v3.0-2023."""
    manifest, policies = discovered_data["PM_KISAN"]
    assert manifest.scheme_code == "PM_KISAN"
    version_codes = [p.policy_version_code for p in policies]
    assert version_codes == ["v1.0-2018", "v2.0-2019", "v3.0-2023"]


def test_d_ssy_has_exactly_three_policy_versions(discovered_data):
    """Requirement D: SSY has exactly three versions: v1.0-2016, v2.0-2019, v3.0-2024."""
    manifest, policies = discovered_data["SSY"]
    assert manifest.scheme_code == "SSY"
    version_codes = [p.policy_version_code for p in policies]
    assert version_codes == ["v1.0-2016", "v2.0-2019", "v3.0-2024"]


def test_e_all_asts_validate(discovered_data):
    """Requirement E: Every policy version contains a valid AST that passes strict validation."""
    for scheme_code, (_, policies) in discovered_data.items():
        for policy in policies:
            ast = validate_ast(policy.root_rule)
            assert isinstance(ast, LogicalNode)
            assert ast.operator == LogicalOperator.AND


def test_f_all_rule_ids_are_unique(discovered_data):
    """Requirement F: All rule IDs are unique within each ruleset."""
    for scheme_code, (_, policies) in discovered_data.items():
        for policy in policies:
            seen_ids = set()

            def _traverse(node):
                r_id = node.get("rule_id")
                assert r_id not in seen_ids, f"Duplicate rule_id {r_id} in {policy.policy_version_code}"
                seen_ids.add(r_id)
                for child in node.get("children", []):
                    _traverse(child)

            _traverse(policy.root_rule)
            assert len(seen_ids) >= 4, f"Ruleset {policy.policy_version_code} has too few rules"


def test_g_all_root_rules_resolve(discovered_data):
    """Requirement G: All root rules resolve into executable BaseRuleNodes."""
    for scheme_code, (_, policies) in discovered_data.items():
        for policy in policies:
            root = validate_ast(policy.root_rule)
            assert hasattr(root, "rule_id")
            assert root.rule_id.endswith("-ROOT")


def test_h_all_source_metadata_exists(discovered_data):
    """Requirement H: Statutory source metadata (title, URL, reference, document_id) exists."""
    for scheme_code, (_, policies) in discovered_data.items():
        for policy in policies:
            src = policy.source
            assert src.title and len(src.title) > 5
            assert src.url.startswith("https://")
            assert src.reference and len(src.reference) > 3
            assert src.document_identifier and len(src.document_identifier) > 3


# ==============================================================================
# I - L: Canonical Hashing & Determinism
# ==============================================================================

def test_i_all_canonical_hashes_are_generated(discovered_data):
    """Requirement I: 64-character SHA-256 canonical rule hashes are generated for all 14 versions."""
    hashes = set()
    for scheme_code, (_, policies) in discovered_data.items():
        for policy in policies:
            h = compute_canonical_rule_hash(policy.root_rule)
            assert len(h) == 64
            assert all(c in "0123456789abcdef" for c in h)
            hashes.add(h)
    assert len(hashes) == 14, "All 14 policy versions must have distinct canonical hashes"


def test_j_hashes_are_reproducible(discovered_data):
    """Requirement J: Hashes are deterministic and reproducible across repeated calls."""
    for scheme_code, (_, policies) in discovered_data.items():
        for policy in policies:
            h1 = compute_canonical_rule_hash(policy.root_rule)
            h2 = compute_canonical_rule_hash(policy.root_rule)
            assert h1 == h2


def test_k_changing_a_rule_changes_its_hash(discovered_data):
    """Requirement K: Modifying any rule property strictly alters the computed hash."""
    _, policies = discovered_data["PM_KISAN"]
    v1 = policies[0]
    base_hash = compute_canonical_rule_hash(v1.root_rule)

    # Mutate expected value
    mutated = copy.deepcopy(v1.root_rule)
    mutated["children"][1]["expected_value"] = 3.0
    mutated_hash = compute_canonical_rule_hash(mutated)
    assert base_hash != mutated_hash


def test_l_object_key_ordering_does_not_change_hash(discovered_data):
    """Requirement L: Dictionary key insertion order does not affect the canonical hash."""
    _, policies = discovered_data["SSY"]
    v1 = policies[0]
    original = v1.root_rule
    original_hash = compute_canonical_rule_hash(original)

    # Invert key order
    reversed_keys = {k: original[k] for k in reversed(list(original.keys()))}
    reversed_hash = compute_canonical_rule_hash(reversed_keys)
    assert original_hash == reversed_hash


# ==============================================================================
# M: Policy Version Boundaries & Date Selection
# ==============================================================================

@pytest.mark.asyncio
async def test_m_policy_version_boundary_tests():
    """Requirement M: Boundary date selection accurately maps dates to policy generations."""
    async with AsyncSessionLocal() as session:
        # PM-KISAN boundaries:
        # v1: 2018-12-01 to 2019-03-31
        # v2: 2019-04-01 to 2022-12-31
        # v3: 2023-01-01 to PRESENT

        # 1 day before v1 start -> not found
        pre_v1 = await select_policy_version(session, "PM_KISAN", date(2018, 11, 30))
        assert pre_v1 is None

        # v1 first day
        v1_first = await get_policy_version(session, "PM_KISAN", date(2018, 12, 1))
        assert v1_first.version_code == "v1.0-2018"

        # v1 last day
        v1_last = await get_policy_version(session, "PM_KISAN", date(2019, 3, 31))
        assert v1_last.version_code == "v1.0-2018"

        # v2 first day
        v2_first = await get_policy_version(session, "PM_KISAN", date(2019, 4, 1))
        assert v2_first.version_code == "v2.0-2019"

        # v2 last day
        v2_last = await get_policy_version(session, "PM_KISAN", date(2022, 12, 31))
        assert v2_last.version_code == "v2.0-2019"

        # v3 first day
        v3_first = await get_policy_version(session, "PM_KISAN", date(2023, 1, 1))
        assert v3_first.version_code == "v3.0-2023"

        # v3 future open-ended date
        v3_future = await get_policy_version(session, "PM_KISAN", date(2026, 9, 18))
        assert v3_future.version_code == "v3.0-2023"

        # SSY boundaries:
        # v1: 2016-03-18 to 2019-12-11
        # v2: 2019-12-12 to 2024-03-31
        # v3: 2024-04-01 to PRESENT
        ssy_v1_last = await get_policy_version(session, "SSY", date(2019, 12, 11))
        assert ssy_v1_last.version_code == "v1.0-2016"

        ssy_v2_first = await get_policy_version(session, "SSY", date(2019, 12, 12))
        assert ssy_v2_first.version_code == "v2.0-2019"

        ssy_v2_last = await get_policy_version(session, "SSY", date(2024, 3, 31))
        assert ssy_v2_last.version_code == "v2.0-2019"

        ssy_v3_first = await get_policy_version(session, "SSY", date(2024, 4, 1))
        assert ssy_v3_first.version_code == "v3.0-2024"


# ==============================================================================
# N - O: PM-KISAN Land Ceiling Distinction (Historical vs Current)
# ==============================================================================

@pytest.mark.asyncio
async def test_n_pm_kisan_historical_ceiling_applies_only_to_v1():
    """Requirement N: Landholding ceiling <= 2.0 ha applies strictly in v1.0-2018."""
    evaluator = DeterministicEvaluator()
    eval_date = date(2019, 1, 15)
    async with AsyncSessionLocal() as session:
        pv_v1 = await get_policy_version(session, "PM_KISAN", eval_date)
        ast_v1 = get_policy_rule_ast(pv_v1)

        # Baseline qualifying farmer with 1.5 ha
        ctx_qualifying = EvaluationContext(
            data={
                "family": {
                    "owns_cultivable_land": True,
                    "total_land_area_hectares": 1.5,
                    "is_institutional_landholder": False,
                    "has_constitutional_post_holder": False,
                    "has_public_representative": False,
                    "has_disqualified_government_employee": False,
                    "has_pensioner_above_ten_thousand": False,
                    "has_income_tax_payer": False,
                    "has_registered_practicing_professional": False,
                }
            },
            evaluation_date=eval_date,
        )
        res_qualifying = evaluator.evaluate(ast_v1, ctx_qualifying)
        assert res_qualifying.root_truth_value == RuleTruthValue.TRUE

        # Farmer with 2.5 ha under 2018 historical guidelines -> FAILS ceiling
        ctx_large_farmer = EvaluationContext(
            data={
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
                }
            },
            evaluation_date=eval_date,
        )
        res_large_farmer = evaluator.evaluate(ast_v1, ctx_large_farmer)
        assert res_large_farmer.root_truth_value == RuleTruthValue.FALSE
        assert "PMKISAN-HIST-LAND-CEILING-2HA" in res_large_farmer.failed_rules


@pytest.mark.asyncio
async def test_o_pm_kisan_v2_and_v3_do_not_impose_land_ceiling():
    """Requirement O: PM-KISAN v2 and v3 expanded coverage: farmers with > 2.0 ha qualify."""
    evaluator = DeterministicEvaluator()
    async with AsyncSessionLocal() as session:
        # Evaluate under v2.0-2019
        eval_date_v2 = date(2020, 5, 1)
        pv_v2 = await get_policy_version(session, "PM_KISAN", eval_date_v2)
        ast_v2 = get_policy_rule_ast(pv_v2)

        # Farmer with 5.5 ha landholding acquired before cut-off
        ctx_v2 = EvaluationContext(
            data={
                "family": {
                    "owns_cultivable_land": True,
                    "total_land_area_hectares": 5.5,
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
                }
            },
            evaluation_date=eval_date_v2,
        )
        res_v2 = evaluator.evaluate(ast_v2, ctx_v2)
        assert res_v2.root_truth_value == RuleTruthValue.TRUE

        # Evaluate under v3.0-2023 with 20.0 ha landholding
        eval_date_v3 = date(2024, 6, 1)
        pv_v3 = await get_policy_version(session, "PM_KISAN", eval_date_v3)
        ast_v3 = get_policy_rule_ast(pv_v3)
        ctx_v3 = EvaluationContext(
            data={
                "family": {
                    "owns_cultivable_land": True,
                    "total_land_area_hectares": 20.0,
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
                }
            },
            evaluation_date=eval_date_v3,
        )
        res_v3 = evaluator.evaluate(ast_v3, ctx_v3)
        assert res_v3.root_truth_value == RuleTruthValue.TRUE


# ==============================================================================
# P - R: SSY Age Rule Boundaries & Missing Facts
# ==============================================================================

@pytest.mark.asyncio
async def test_p_ssy_age_boundary_at_exactly_ten():
    """Requirement P: SSY HAS_NOT_ATTAINED_AGE operator boundary on 10th birthday."""
    evaluator = DeterministicEvaluator()
    eval_date = date(2024, 5, 1)
    async with AsyncSessionLocal() as session:
        pv = await get_policy_version(session, "SSY", eval_date)
        ast = get_policy_rule_ast(pv)

        # Girl child born 2014-05-10
        dob = "2014-05-10"

        # Case 1: 1 day before 10th birthday (2024-05-09) -> TRUE
        ctx_before = EvaluationContext(
            data={
                "beneficiary": {"gender": "FEMALE", "is_indian_resident": True, "date_of_birth": dob},
                "account": {"opening_date": "2024-05-09", "is_first_account_for_child": True},
                "guardian": {"is_natural_guardian": True, "is_court_appointed_legal_guardian": False},
                "family": {"active_ssy_accounts_count": 0, "has_multiple_birth_exception": False},
            },
            evaluation_date=date(2024, 5, 9),
        )
        res_before = evaluator.evaluate(ast, ctx_before)
        assert res_before.root_truth_value == RuleTruthValue.TRUE

        # Case 2: On exactly 10th birthday (2024-05-10) -> FALSE (attained age 10)
        ctx_exact = EvaluationContext(
            data={
                "beneficiary": {"gender": "FEMALE", "is_indian_resident": True, "date_of_birth": dob},
                "account": {"opening_date": "2024-05-10", "is_first_account_for_child": True},
                "guardian": {"is_natural_guardian": True, "is_court_appointed_legal_guardian": False},
                "family": {"active_ssy_accounts_count": 0, "has_multiple_birth_exception": False},
            },
            evaluation_date=date(2024, 5, 10),
        )
        res_exact = evaluator.evaluate(ast, ctx_exact)
        assert res_exact.root_truth_value == RuleTruthValue.FALSE
        assert "SSY-AGE-LIMIT-10" in res_exact.failed_rules

        # Case 3: 1 day after 10th birthday (2024-05-11) -> FALSE
        ctx_after = EvaluationContext(
            data={
                "beneficiary": {"gender": "FEMALE", "is_indian_resident": True, "date_of_birth": dob},
                "account": {"opening_date": "2024-05-11", "is_first_account_for_child": True},
                "guardian": {"is_natural_guardian": True, "is_court_appointed_legal_guardian": False},
                "family": {"active_ssy_accounts_count": 0, "has_multiple_birth_exception": False},
            },
            evaluation_date=date(2024, 5, 11),
        )
        res_after = evaluator.evaluate(ast, ctx_after)
        assert res_after.root_truth_value == RuleTruthValue.FALSE


@pytest.mark.asyncio
async def test_q_ssy_missing_dob_produces_unknown():
    """Requirement Q: Missing beneficiary.date_of_birth produces UNKNOWN, not FALSE."""
    evaluator = DeterministicEvaluator()
    eval_date = date(2024, 5, 1)
    async with AsyncSessionLocal() as session:
        pv = await get_policy_version(session, "SSY", eval_date)
        ast = get_policy_rule_ast(pv)

        ctx_missing_dob = EvaluationContext(
            data={
                "beneficiary": {"gender": "FEMALE", "is_indian_resident": True},  # date_of_birth missing
                "account": {"opening_date": "2024-05-09", "is_first_account_for_child": True},
                "guardian": {"is_natural_guardian": True, "is_court_appointed_legal_guardian": False},
                "family": {"active_ssy_accounts_count": 0, "has_multiple_birth_exception": False},
            },
            evaluation_date=eval_date,
        )
        res = evaluator.evaluate(ast, ctx_missing_dob)
        assert res.root_truth_value == RuleTruthValue.UNKNOWN
        assert "beneficiary.date_of_birth" in res.all_missing_fields


@pytest.mark.asyncio
async def test_r_ssy_missing_opening_date_produces_unknown():
    """Requirement R: Missing account.opening_date produces UNKNOWN."""
    evaluator = DeterministicEvaluator()
    eval_date = date(2024, 5, 1)
    async with AsyncSessionLocal() as session:
        pv = await get_policy_version(session, "SSY", eval_date)
        ast = get_policy_rule_ast(pv)

        ctx_missing_as_of = EvaluationContext(
            data={
                "beneficiary": {"gender": "FEMALE", "is_indian_resident": True, "date_of_birth": "2016-01-01"},
                "account": {"is_first_account_for_child": True},  # opening_date missing
                "guardian": {"is_natural_guardian": True, "is_court_appointed_legal_guardian": False},
                "family": {"active_ssy_accounts_count": 0, "has_multiple_birth_exception": False},
            },
            evaluation_date=eval_date,
        )
        res = evaluator.evaluate(ast, ctx_missing_as_of)
        assert res.root_truth_value == RuleTruthValue.UNKNOWN
        assert "account.opening_date" in res.all_missing_fields


# ==============================================================================
# S & 20: SSY Family Constraints & Guardian Qualification
# ==============================================================================

@pytest.mark.asyncio
async def test_s_ssy_family_account_constraints():
    """Requirement S: Maximum two accounts per family unless multiple-birth exception applies."""
    evaluator = DeterministicEvaluator()
    eval_date = date(2024, 5, 1)
    async with AsyncSessionLocal() as session:
        pv = await get_policy_version(session, "SSY", eval_date)
        ast = get_policy_rule_ast(pv)

        base_data = {
            "beneficiary": {"gender": "FEMALE", "is_indian_resident": True, "date_of_birth": "2018-01-01"},
            "account": {"opening_date": "2024-01-01", "is_first_account_for_child": True},
            "guardian": {"is_natural_guardian": True, "is_court_appointed_legal_guardian": False},
        }

        # 0 or 1 active account -> passes
        ctx_one = EvaluationContext(
            data={**base_data, "family": {"active_ssy_accounts_count": 1, "has_multiple_birth_exception": False}},
            evaluation_date=eval_date,
        )
        assert evaluator.evaluate(ast, ctx_one).root_truth_value == RuleTruthValue.TRUE

        # 2 active accounts, no exception -> FAILS
        ctx_two_no_excl = EvaluationContext(
            data={**base_data, "family": {"active_ssy_accounts_count": 2, "has_multiple_birth_exception": False}},
            evaluation_date=eval_date,
        )
        assert evaluator.evaluate(ast, ctx_two_no_excl).root_truth_value == RuleTruthValue.FALSE

        # 2 active accounts WITH multiple birth exception -> PASSES
        ctx_two_with_excl = EvaluationContext(
            data={**base_data, "family": {"active_ssy_accounts_count": 2, "has_multiple_birth_exception": True}},
            evaluation_date=eval_date,
        )
        assert evaluator.evaluate(ast, ctx_two_with_excl).root_truth_value == RuleTruthValue.TRUE


@pytest.mark.asyncio
async def test_ssy_guardian_qualification():
    """Requirement 20: Grandparents do not qualify as opening guardians unless court-appointed."""
    evaluator = DeterministicEvaluator()
    eval_date = date(2024, 5, 1)
    async with AsyncSessionLocal() as session:
        pv = await get_policy_version(session, "SSY", eval_date)
        ast = get_policy_rule_ast(pv)

        base_data = {
            "beneficiary": {"gender": "FEMALE", "is_indian_resident": True, "date_of_birth": "2018-01-01"},
            "account": {"opening_date": "2024-01-01", "is_first_account_for_child": True},
            "family": {"active_ssy_accounts_count": 0, "has_multiple_birth_exception": False},
        }

        # Case 1: Natural guardian (Mother or Father) -> PASSES
        ctx_natural = EvaluationContext(
            data={**base_data, "guardian": {"is_natural_guardian": True, "is_court_appointed_legal_guardian": False}},
            evaluation_date=eval_date,
        )
        assert evaluator.evaluate(ast, ctx_natural).root_truth_value == RuleTruthValue.TRUE

        # Case 2: Grandparent (not natural, NOT court-appointed) -> FAILS
        ctx_grandparent = EvaluationContext(
            data={**base_data, "guardian": {"is_natural_guardian": False, "is_court_appointed_legal_guardian": False}},
            evaluation_date=eval_date,
        )
        res_gp = evaluator.evaluate(ast, ctx_grandparent)
        assert res_gp.root_truth_value == RuleTruthValue.FALSE
        assert "SSY-GUARDIAN-ELIGIBILITY" in res_gp.failed_rules

        # Case 3: Court-appointed legal guardian (e.g. legal adoption/court order) -> PASSES
        ctx_court_guardian = EvaluationContext(
            data={**base_data, "guardian": {"is_natural_guardian": False, "is_court_appointed_legal_guardian": True}},
            evaluation_date=eval_date,
        )
        assert evaluator.evaluate(ast, ctx_court_guardian).root_truth_value == RuleTruthValue.TRUE


# ==============================================================================
# T: PM-KISAN Statutory Exclusion Categories
# ==============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize("exclusion_field", [
    "is_institutional_landholder",
    "has_constitutional_post_holder",
    "has_public_representative",
    "has_disqualified_government_employee",
    "has_pensioner_above_ten_thousand",
    "has_income_tax_payer",
    "has_registered_practicing_professional",
])
async def test_t_pm_kisan_all_seven_statutory_exclusions(exclusion_field):
    """Requirement T: Declarative evaluation of all 7 PM-KISAN statutory exclusion categories."""
    evaluator = DeterministicEvaluator()
    eval_date = date(2024, 1, 1)
    async with AsyncSessionLocal() as session:
        pv = await get_policy_version(session, "PM_KISAN", eval_date)
        ast = get_policy_rule_ast(pv)

        family_data = {
            "owns_cultivable_land": True,
            "is_institutional_landholder": False,
            "has_constitutional_post_holder": False,
            "has_public_representative": False,
            "has_disqualified_government_employee": False,
            "has_pensioner_above_ten_thousand": False,
            "has_income_tax_payer": False,
            "has_registered_practicing_professional": False,
            "is_nri": False,
        }
        # Trigger the specific exclusion
        family_data[exclusion_field] = True

        ctx = EvaluationContext(
            data={
                "family": family_data,
                "land": {"transferred_after_cutoff": False},
            },
            evaluation_date=eval_date,
        )
        res = evaluator.evaluate(ast, ctx)
        assert res.root_truth_value == RuleTruthValue.FALSE
        assert len(res.failed_rules) >= 1


# ==============================================================================
# U: PM-KISAN Cut-off & Succession on Death vs Living Partition
# ==============================================================================

@pytest.mark.asyncio
async def test_u_pm_kisan_succession_versus_living_partition():
    """Requirement U: Post-cutoff transfer requires bona-fide succession due to death of landowner."""
    evaluator = DeterministicEvaluator()
    eval_date = date(2023, 6, 1)
    async with AsyncSessionLocal() as session:
        pv = await get_policy_version(session, "PM_KISAN", eval_date)
        ast = get_policy_rule_ast(pv)

        base_family = {
            "owns_cultivable_land": True,
            "is_institutional_landholder": False,
            "has_constitutional_post_holder": False,
            "has_public_representative": False,
            "has_disqualified_government_employee": False,
            "has_pensioner_above_ten_thousand": False,
            "has_income_tax_payer": False,
            "has_registered_practicing_professional": False,
            "is_nri": False,
        }

        # Case 1: Pre-cutoff ownership (transferred_after_cutoff == False) -> PASSES
        ctx_pre_cutoff = EvaluationContext(
            data={
                "family": base_family,
                "land": {"transferred_after_cutoff": False},
            },
            evaluation_date=eval_date,
        )
        assert evaluator.evaluate(ast, ctx_pre_cutoff).root_truth_value == RuleTruthValue.TRUE

        # Case 2: Post-cutoff transfer via partition among LIVING co-owners -> FAILS
        ctx_living_partition = EvaluationContext(
            data={
                "family": base_family,
                "land": {
                    "transferred_after_cutoff": True,
                    "acquisition_mode": "PARTITION",
                    "previous_owner_deceased": False,
                },
            },
            evaluation_date=eval_date,
        )
        res_living = evaluator.evaluate(ast, ctx_living_partition)
        assert res_living.root_truth_value == RuleTruthValue.FALSE
        assert "PMKISAN-LAND-CUTOFF-2019" in res_living.failed_rules

        # Case 3: Post-cutoff transfer via bona-fide succession on death -> PASSES
        ctx_succession = EvaluationContext(
            data={
                "family": base_family,
                "land": {
                    "transferred_after_cutoff": True,
                    "acquisition_mode": "SUCCESSION",
                    "previous_owner_deceased": True,
                },
            },
            evaluation_date=eval_date,
        )
        res_succ = evaluator.evaluate(ast, ctx_succession)
        assert res_succ.root_truth_value == RuleTruthValue.TRUE


# ==============================================================================
# V: UNKNOWN Semantics for Missing Statutory Facts
# ==============================================================================

@pytest.mark.asyncio
async def test_v_missing_statutory_facts_produce_unknown():
    """Requirement V: Missing land or exclusion facts evaluate to UNKNOWN, not FALSE."""
    evaluator = DeterministicEvaluator()
    eval_date = date(2023, 6, 1)
    async with AsyncSessionLocal() as session:
        pv = await get_policy_version(session, "PM_KISAN", eval_date)
        ast = get_policy_rule_ast(pv)

        # Completely missing family data
        ctx_empty = EvaluationContext(data={}, evaluation_date=eval_date)
        res = evaluator.evaluate(ast, ctx_empty)
        assert res.root_truth_value == RuleTruthValue.UNKNOWN
        assert len(res.all_missing_fields) > 0


# ==============================================================================
# W - X: Bilingual Fidelity
# ==============================================================================

def test_w_bilingual_descriptions_exist_on_every_rule(discovered_data):
    """Requirement W: Every executable rule node has non-empty English and Hindi statutory descriptions."""
    for scheme_code, (_, policies) in discovered_data.items():
        for policy in policies:
            def _check_bilingual(node):
                assert node.get("description_en"), f"Missing description_en in {node.get('rule_id')}"
                assert node.get("description_hi"), f"Missing description_hi in {node.get('rule_id')}"
                assert len(node["description_en"]) > 5
                assert len(node["description_hi"]) > 5
                for child in node.get("children", []):
                    _check_bilingual(child)

            _check_bilingual(policy.root_rule)


def test_x_bilingual_descriptions_are_semantically_consistent(discovered_data):
    """Requirement X: Verified statutory correspondence between English and Hindi text."""
    _, policies = discovered_data["SSY"]
    v1_rules = policies[0].root_rule["children"]
    gender_rule = next(r for r in v1_rules if r["rule_id"] == "SSY-BENEFICIARY-GENDER")
    assert "girl child" in gender_rule["description_en"].lower()
    assert "बालिका" in gender_rule["description_hi"] or "कन्या" in gender_rule["description_hi"]


# ==============================================================================
# Y - Z: Idempotency and Anti-Overwrite Hardening
# ==============================================================================

@pytest.mark.asyncio
async def test_y_policy_loader_is_idempotent():
    """Requirement Y: Executing load_all_policies repeatedly does not create duplicate rows."""
    async with AsyncSessionLocal() as session:
        res1 = await load_all_policies(session=session)
    assert res1["schemes_processed"] == 10
    assert res1["total_versions_created"] == 0
    assert res1["total_versions_retained"] == 14

    # Check total rows in DB
    async with AsyncSessionLocal() as session:
        schemes_cnt = (await session.execute(select(Scheme))).scalars().all()
        assert len(schemes_cnt) == 10

        versions_cnt = (await session.execute(select(PolicyVersion))).scalars().all()
        assert len(versions_cnt) == 14

        rulesets_cnt = (await session.execute(select(RuleSet))).scalars().all()
        assert len(rulesets_cnt) == 14


@pytest.mark.asyncio
async def test_z_conflicting_hash_cannot_overwrite_stored_policy(discovered_data):
    """Requirement Z: Attempting to overwrite a stored policy version with conflicting hash raises PolicyHashConflictError."""
    manifest, policies = discovered_data["PM_KISAN"]
    original_policy = policies[0]

    # Create a corrupted copy with different AST definition
    corrupted_policy = copy.deepcopy(original_policy)
    corrupted_policy.root_rule["children"][0]["expected_value"] = False  # Changed criteria

    async with AsyncSessionLocal() as session:
        scheme_stmt = select(Scheme).where(Scheme.scheme_code == "PM_KISAN")
        scheme_res = await session.execute(scheme_stmt)
        scheme = scheme_res.scalar_one()

        with pytest.raises(PolicyHashConflictError) as exc_info:
            await load_policy_version(session, scheme, corrupted_policy)

        await session.rollback()
        assert "already exists with hash" in str(exc_info.value)
        assert "conflicting hash" in str(exc_info.value)


# ==============================================================================
# AA - AD: Architectural Boundaries & Evaluator Neutrality
# ==============================================================================

@pytest.mark.asyncio
async def test_aa_historical_policy_persists_correctly():
    """Requirement AA: Historical policies remain immutable in DB."""
    async with AsyncSessionLocal() as session:
        v1 = await get_policy_version(session, "PM_KISAN", date(2018, 12, 15))
        assert v1.version_code == "v1.0-2018"
        assert v1.rule_definition_hash is not None
        assert v1.rule_set is not None


@pytest.mark.asyncio
async def test_ab_and_ac_exactly_two_schemes_in_database():
    """Requirements AB & AC: All 10 statutory schemes exist in PostgreSQL."""
    async with AsyncSessionLocal() as session:
        schemes = (await session.execute(select(Scheme))).scalars().all()
        assert len(schemes) == 10
        codes = {s.scheme_code for s in schemes}
        assert codes == {
            "PM_KISAN", "SSY", "PM_KMY", "PMUY", "PM_VISHWAKARMA",
            "PMAY_G", "PMAY_U_2_0", "PM_SVANIDHI", "PMMVY", "IGNOAPS"
        }


def test_ad_no_scheme_specific_logic_in_generic_evaluator():
    """Requirement AD: Zero scheme-specific logic inside backend/app/engine/."""
    backend_dir = Path(__file__).resolve().parent.parent
    engine_dir = backend_dir / "app" / "engine"
    assert engine_dir.exists()

    forbidden_terms = [
        "pmkisan",
        "pm_kisan",
        "pm-kisan",
        "sukanya",
        "ssy",
        "kisan",
        "farmer",
        "girl_child",
    ]

    for py_file in engine_dir.rglob("*.py"):
        with open(py_file, "r", encoding="utf-8") as f:
            content = f.read().lower()
        for term in forbidden_terms:
            assert term not in content, f"Forbidden scheme-specific term '{term}' found in engine file {py_file.name}!"


# ==============================================================================
# AE - AJ: Provenance, Explainability Trace, Audit Record Integration
# ==============================================================================

@pytest.mark.asyncio
async def test_ae_policy_provenance_survives_persistence():
    """Requirement AE: Cryptographic provenance bindings match database records."""
    async with AsyncSessionLocal() as session:
        pv = await get_policy_version(session, "SSY", date(2024, 6, 1))
        prov = PolicyProvenance(
            scheme_id=pv.scheme_id,
            scheme_code=pv.scheme.scheme_code,
            policy_version_id=pv.id,
            policy_version_code=pv.version_code,
            rule_set_id=pv.rule_set.id,
            rule_set_version=pv.rule_set.rule_set_version,
            canonical_rule_hash=pv.rule_definition_hash,
            evaluation_date=date(2024, 6, 1),
            effective_from=pv.effective_from,
            effective_to=pv.effective_to,
        )
        assert prov.canonical_rule_hash == pv.rule_definition_hash
        assert prov.scheme_code == "SSY"


@pytest.mark.asyncio
async def test_ah_explainability_trace_works_against_real_rulesets():
    """Requirement AH: build_explainability_trace generates bilingual explainability for statutory rules."""
    evaluator = DeterministicEvaluator()
    eval_date = date(2024, 6, 1)
    async with AsyncSessionLocal() as session:
        pv = await get_policy_version(session, "SSY", eval_date)
        ast = get_policy_rule_ast(pv)

        ctx = EvaluationContext(
            data={
                "beneficiary": {"gender": "FEMALE", "is_indian_resident": True, "date_of_birth": "2018-01-01"},
                "account": {"opening_date": "2024-01-01", "is_first_account_for_child": True},
                "guardian": {"is_natural_guardian": True, "is_court_appointed_legal_guardian": False},
                "family": {"active_ssy_accounts_count": 0, "has_multiple_birth_exception": False},
            },
            evaluation_date=eval_date,
        )
        res = evaluator.evaluate(ast, ctx)
        assert res.root_truth_value == RuleTruthValue.TRUE

        prov = PolicyProvenance(
            scheme_id=pv.scheme_id,
            scheme_code=pv.scheme.scheme_code,
            policy_version_id=pv.id,
            policy_version_code=pv.version_code,
            rule_set_id=pv.rule_set.id,
            rule_set_version=pv.rule_set.rule_set_version,
            canonical_rule_hash=pv.rule_definition_hash,
            evaluation_date=eval_date,
            effective_from=pv.effective_from,
            effective_to=pv.effective_to,
        )
        trace = build_explainability_trace(res, prov)
        assert trace.overall_result == EligibilityResult.ELIGIBLE
        assert len(trace.ordered_nodes) >= 6
        assert all(n.explanation_en and n.explanation_hi for n in trace.ordered_nodes)


@pytest.mark.asyncio
async def test_ai_audit_record_captures_correct_policy_version_and_hash():
    """Requirement AI: Audit record binds statutory policy version code and canonical hash."""
    evaluator = DeterministicEvaluator()
    eval_date = date(2024, 1, 1)
    async with AsyncSessionLocal() as session:
        pv = await get_policy_version(session, "PM_KISAN", eval_date)
        ast = get_policy_rule_ast(pv)

        citizen_id = uuid.uuid4()
        ctx = EvaluationContext(
            data={
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
            evaluation_date=eval_date,
        )
        res = evaluator.evaluate(ast, ctx)
        assert res.root_truth_value == RuleTruthValue.TRUE

        prov = PolicyProvenance(
            scheme_id=pv.scheme_id,
            scheme_code="PM_KISAN",
            policy_version_id=pv.id,
            policy_version_code=pv.version_code,
            rule_set_id=pv.rule_set.id,
            rule_set_version=pv.rule_set.rule_set_version,
            canonical_rule_hash=pv.rule_definition_hash,
            evaluation_date=eval_date,
            effective_from=pv.effective_from,
            effective_to=pv.effective_to,
        )
        trace = build_explainability_trace(res, prov)

        audit_rec = create_audit_evaluation_record(
            citizen_ref="CITIZEN-001",
            input_data=dict(ctx.data),
            provenance=prov,
            explainability_trace=trace,
            evaluation_id=citizen_id,
        )

        assert audit_rec.policy_version_code == "v3.0-2023"
        assert audit_rec.provenance.canonical_rule_hash == pv.rule_definition_hash
        assert audit_rec.final_result == EligibilityResult.ELIGIBLE


@pytest.mark.asyncio
async def test_aj_historical_evaluation_continues_to_reference_original_policy():
    """Requirement AJ: Historical evaluation against v1 preserves v1 hash and ceiling rules."""
    evaluator = DeterministicEvaluator()
    eval_date = date(2019, 2, 1)
    async with AsyncSessionLocal() as session:
        pv_hist = await get_policy_version(session, "PM_KISAN", eval_date)
        ast_hist = get_policy_rule_ast(pv_hist)

        assert pv_hist.version_code == "v1.0-2018"
        # Historical farmer with 1.0 ha
        ctx = EvaluationContext(
            data={
                "family": {
                    "owns_cultivable_land": True,
                    "total_land_area_hectares": 1.0,
                    "is_institutional_landholder": False,
                    "has_constitutional_post_holder": False,
                    "has_public_representative": False,
                    "has_disqualified_government_employee": False,
                    "has_pensioner_above_ten_thousand": False,
                    "has_income_tax_payer": False,
                    "has_registered_practicing_professional": False,
                }
            },
            evaluation_date=eval_date,
        )
        res = evaluator.evaluate(ast_hist, ctx)
        assert res.root_truth_value == RuleTruthValue.TRUE

        prov = PolicyProvenance(
            scheme_id=pv_hist.scheme_id,
            scheme_code="PM_KISAN",
            policy_version_id=pv_hist.id,
            policy_version_code=pv_hist.version_code,
            rule_set_id=pv_hist.rule_set.id,
            rule_set_version=pv_hist.rule_set.rule_set_version,
            canonical_rule_hash=pv_hist.rule_definition_hash,
            evaluation_date=eval_date,
            effective_from=pv_hist.effective_from,
            effective_to=pv_hist.effective_to,
        )
        trace = build_explainability_trace(res, prov)
        audit_rec = create_audit_evaluation_record(
            citizen_ref="CITIZEN-HIST-001",
            input_data=dict(ctx.data),
            provenance=prov,
            explainability_trace=trace,
            evaluation_id=uuid.uuid4(),
        )
        assert audit_rec.policy_version_code == "v1.0-2018"
        assert audit_rec.provenance.canonical_rule_hash == pv_hist.rule_definition_hash


# ==============================================================================
# AK: PM-KISAN Non-Resident Indian (NRI) Statutory Exclusion Semantics
# ==============================================================================

@pytest.mark.asyncio
async def test_ak_pm_kisan_nri_exclusion_semantics():
    """Requirement AK: Comprehensive NRI exclusion verification under DA&FW guidelines.
    
    Verifies:
    1. Historical v1.0-2018 invariant: No NRI exclusion existed in original 2018 guidelines;
       evaluation against v1 ignores NRI flags and does not contain PMKISAN-EXCL-NRI.
    2. Qualifying non-NRI farmer family: family.is_nri == False -> ELIGIBLE (RuleTruthValue.TRUE).
    3. Excluded NRI farmer family: family.is_nri == True -> INELIGIBLE (RuleTruthValue.FALSE) with PMKISAN-EXCL-NRI in failed_rules.
    4. Non-NRI family with unrelated NRI member/relative: family.is_nri == False with secondary flags -> ELIGIBLE.
       (Ensures "farmer family is NRI" is evaluated, not broad "farmer family has an NRI member").
    5. Missing NRI fact -> UNKNOWN / INSUFFICIENT_INFORMATION with 'family.is_nri' in all_missing_fields.
    6. Interaction with existing exclusions:
       - Both NRI and another exclusion triggered -> multiple failed rules captured, INELIGIBLE.
    7. Strong Kleene dominance:
       - Another exclusion triggered (institutional) while NRI fact is missing -> FALSE dominates UNKNOWN (INELIGIBLE).
    """
    evaluator = DeterministicEvaluator()

    async with AsyncSessionLocal() as session:
        # 1. Historical v1.0-2018 case: Section 3 in 2018 had no NRI exclusion
        eval_date_v1 = date(2019, 1, 15)
        pv_v1 = await get_policy_version(session, "PM_KISAN", eval_date_v1)
        ast_v1 = get_policy_rule_ast(pv_v1)
        
        ctx_v1_nri = EvaluationContext(
            data={
                "family": {
                    "owns_cultivable_land": True,
                    "total_land_area_hectares": 1.5,
                    "is_institutional_landholder": False,
                    "has_constitutional_post_holder": False,
                    "has_public_representative": False,
                    "has_disqualified_government_employee": False,
                    "has_pensioner_above_ten_thousand": False,
                    "has_income_tax_payer": False,
                    "has_registered_practicing_professional": False,
                    "is_nri": True,  # Would disqualify under v2/v3, but v1 has no NRI exclusion
                }
            },
            evaluation_date=eval_date_v1,
        )
        res_v1 = evaluator.evaluate(ast_v1, ctx_v1_nri)
        assert res_v1.root_truth_value == RuleTruthValue.TRUE
        assert "PMKISAN-EXCL-NRI" not in res_v1.failed_rules
        assert "PMKISAN-EXCL-NRI" not in res_v1.satisfied_rules

        # 2-7: v3.0-2023 evaluation
        eval_date_v3 = date(2024, 1, 1)
        pv_v3 = await get_policy_version(session, "PM_KISAN", eval_date_v3)
        ast_v3 = get_policy_rule_ast(pv_v3)

        qualifying_family = {
            "owns_cultivable_land": True,
            "is_institutional_landholder": False,
            "has_constitutional_post_holder": False,
            "has_public_representative": False,
            "has_disqualified_government_employee": False,
            "has_pensioner_above_ten_thousand": False,
            "has_income_tax_payer": False,
            "has_registered_practicing_professional": False,
            "is_nri": False,
        }
        land_data = {"transferred_after_cutoff": False}

        # 2. Qualifying Non-NRI farmer family
        ctx_qualifying = EvaluationContext(
            data={"family": dict(qualifying_family), "land": land_data},
            evaluation_date=eval_date_v3,
        )
        res_qualifying = evaluator.evaluate(ast_v3, ctx_qualifying)
        assert res_qualifying.root_truth_value == RuleTruthValue.TRUE
        assert res_qualifying.overall_result == EligibilityResult.ELIGIBLE
        assert "PMKISAN-EXCL-NRI" in res_qualifying.satisfied_rules

        # 3. Excluded NRI farmer family
        nri_family = dict(qualifying_family)
        nri_family["is_nri"] = True
        ctx_nri = EvaluationContext(
            data={"family": nri_family, "land": land_data},
            evaluation_date=eval_date_v3,
        )
        res_nri = evaluator.evaluate(ast_v3, ctx_nri)
        assert res_nri.root_truth_value == RuleTruthValue.FALSE
        assert res_nri.overall_result == EligibilityResult.INELIGIBLE
        assert "PMKISAN-EXCL-NRI" in res_nri.failed_rules

        # 4. Non-NRI family with unrelated NRI member/relative: family itself is not NRI
        extended_nri_family = dict(qualifying_family)
        extended_nri_family["is_nri"] = False
        extended_nri_family["has_nri_relative"] = True
        ctx_ext = EvaluationContext(
            data={"family": extended_nri_family, "land": land_data},
            evaluation_date=eval_date_v3,
        )
        res_ext = evaluator.evaluate(ast_v3, ctx_ext)
        assert res_ext.root_truth_value == RuleTruthValue.TRUE
        assert "PMKISAN-EXCL-NRI" in res_ext.satisfied_rules

        # 5. Missing NRI fact -> UNKNOWN / INSUFFICIENT_INFORMATION
        missing_nri_family = dict(qualifying_family)
        del missing_nri_family["is_nri"]
        ctx_missing = EvaluationContext(
            data={"family": missing_nri_family, "land": land_data},
            evaluation_date=eval_date_v3,
        )
        res_missing = evaluator.evaluate(ast_v3, ctx_missing)
        assert res_missing.root_truth_value == RuleTruthValue.UNKNOWN
        assert res_missing.overall_result == EligibilityResult.INSUFFICIENT_INFORMATION
        assert "family.is_nri" in res_missing.all_missing_fields
        assert "PMKISAN-EXCL-NRI" in res_missing.unknown_rules

        # 6. Interaction: Both NRI and Income Tax payer triggered
        dual_exclusion_family = dict(qualifying_family)
        dual_exclusion_family["is_nri"] = True
        dual_exclusion_family["has_income_tax_payer"] = True
        ctx_dual = EvaluationContext(
            data={"family": dual_exclusion_family, "land": land_data},
            evaluation_date=eval_date_v3,
        )
        res_dual = evaluator.evaluate(ast_v3, ctx_dual)
        assert res_dual.root_truth_value == RuleTruthValue.FALSE
        assert res_dual.overall_result == EligibilityResult.INELIGIBLE
        assert "PMKISAN-EXCL-NRI" in res_dual.failed_rules
        assert "PMKISAN-EXCL-INCOME-TAX" in res_dual.failed_rules

        # 7. Disqualified by Institutional Landholder while NRI is missing -> FALSE dominates UNKNOWN
        inst_missing_nri_family = dict(missing_nri_family)
        inst_missing_nri_family["is_institutional_landholder"] = True
        ctx_inst_missing = EvaluationContext(
            data={"family": inst_missing_nri_family, "land": land_data},
            evaluation_date=eval_date_v3,
        )
        res_inst_missing = evaluator.evaluate(ast_v3, ctx_inst_missing)
        assert res_inst_missing.root_truth_value == RuleTruthValue.FALSE
        assert res_inst_missing.overall_result == EligibilityResult.INELIGIBLE
        assert "PMKISAN-EXCL-INSTITUTIONAL" in res_inst_missing.failed_rules
