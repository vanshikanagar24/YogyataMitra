"""Unit and integration tests for the DeterministicEvaluator and Kleene tri-state logic."""

from datetime import date, datetime
from decimal import Decimal
import json
import pytest

from app.engine import (
    AggregationNode,
    AggregationOperator,
    CollectionNode,
    CollectionOperator,
    ComparisonNode,
    ComparisonOperator,
    ContextOperator,
    ContextScopeNode,
    DeterministicEvaluator,
    EvaluationContext,
    EvaluationResult,
    ExistenceNode,
    ExistenceOperator,
    InvalidCollectionOperationError,
    InvalidTemporalArgumentError,
    LogicalNode,
    LogicalOperator,
    RuleTruthValue,
    TemporalNode,
    TemporalOperator,
    TypeMismatchError,
    kleene_and,
    kleene_not,
    kleene_or,
)
from app.models.enums import EligibilityResult


# ============================================================================
# 1. Kleene Tri-State Logic Truth Table Tests
# ============================================================================

def test_kleene_logic_truth_tables():
    T = RuleTruthValue.TRUE
    F = RuleTruthValue.FALSE
    U = RuleTruthValue.UNKNOWN

    # NOT
    assert kleene_not(T) == F
    assert kleene_not(F) == T
    assert kleene_not(U) == U

    # AND
    assert kleene_and([T, T]) == T
    assert kleene_and([T, U]) == U
    assert kleene_and([F, U]) == F  # False dominates Unknown
    assert kleene_and([F, T]) == F
    assert kleene_and([U, U]) == U
    assert kleene_and([T, T, F]) == F
    assert kleene_and([T, T, U]) == U

    # OR
    assert kleene_or([T, T]) == T
    assert kleene_or([T, U]) == T  # True dominates Unknown
    assert kleene_or([F, U]) == U
    assert kleene_or([F, F]) == F
    assert kleene_or([U, U]) == U
    assert kleene_or([F, F, T]) == T


# ============================================================================
# 2. EvaluationContext Tests
# ============================================================================

def test_context_resolution_and_immutability():
    data = {
        "citizen": {
            "name": "Ramesh",
            "age": 45,
            "null_field": None,
        },
        "parcels": [{"id": 1, "area": 1.5}, {"id": 2, "area": 0.8}],
    }
    ctx = EvaluationContext(data=data, evaluation_date=date(2026, 9, 18))

    # Dot-path traversal
    val, exists = ctx.resolve_path("citizen.name")
    assert exists is True
    assert val == "Ramesh"

    # Numeric list index traversal
    val, exists = ctx.resolve_path("parcels.0.area")
    assert exists is True
    assert val == 1.5

    # Evaluation date built-in
    val, exists = ctx.resolve_path("evaluation_date")
    assert exists is True
    assert val == date(2026, 9, 18)

    # Distinguish None from Non-existent
    val, exists = ctx.resolve_path("citizen.null_field")
    assert exists is True
    assert val is None

    val, exists = ctx.resolve_path("citizen.non_existent")
    assert exists is False
    assert val is None

    # Scoped context
    scoped = ctx.with_scope({"member": {"role": "SPOUSE", "tax_payee": False}})
    val, exists = scoped.resolve_path("member.tax_payee")
    assert exists is True
    assert val is False

    # Original context remains unchanged
    _, exists_orig = ctx.resolve_path("member.tax_payee")
    assert exists_orig is False


# ============================================================================
# 3. Comparison Node Evaluator Tests
# ============================================================================

def test_comparison_evaluator_all_operators():
    evaluator = DeterministicEvaluator()
    data = {
        "age": 25,
        "income": 150000,
        "state": "UP",
        "date_joined": "2018-05-10",
        "category": "OBC",
    }
    ctx = EvaluationContext(data=data, evaluation_date=date(2026, 1, 1))

    # EQ
    node_eq = ComparisonNode(field_path="state", operator=ComparisonOperator.EQ, expected_value="UP")
    assert evaluator.evaluate(node_eq, ctx).root_truth_value == RuleTruthValue.TRUE

    # NEQ
    node_neq = ComparisonNode(field_path="state", operator=ComparisonOperator.NEQ, expected_value="DL")
    assert evaluator.evaluate(node_neq, ctx).root_truth_value == RuleTruthValue.TRUE

    # GT / GTE
    node_gt = ComparisonNode(field_path="age", operator=ComparisonOperator.GT, expected_value=18)
    assert evaluator.evaluate(node_gt, ctx).root_truth_value == RuleTruthValue.TRUE

    node_gte = ComparisonNode(field_path="age", operator=ComparisonOperator.GTE, expected_value=25)
    assert evaluator.evaluate(node_gte, ctx).root_truth_value == RuleTruthValue.TRUE

    # LT / LTE
    node_lt = ComparisonNode(field_path="income", operator=ComparisonOperator.LT, expected_value=200000)
    assert evaluator.evaluate(node_lt, ctx).root_truth_value == RuleTruthValue.TRUE

    node_lte = ComparisonNode(field_path="income", operator=ComparisonOperator.LTE, expected_value=150000)
    assert evaluator.evaluate(node_lte, ctx).root_truth_value == RuleTruthValue.TRUE

    # IN / NOT_IN
    node_in = ComparisonNode(field_path="category", operator=ComparisonOperator.IN, expected_value=["SC", "ST", "OBC"])
    assert evaluator.evaluate(node_in, ctx).root_truth_value == RuleTruthValue.TRUE

    node_not_in = ComparisonNode(field_path="category", operator=ComparisonOperator.NOT_IN, expected_value=["GENERAL"])
    assert evaluator.evaluate(node_not_in, ctx).root_truth_value == RuleTruthValue.TRUE

    # Date comparison (string in data vs date expected, and vice versa)
    node_date = ComparisonNode(
        field_path="date_joined",
        operator=ComparisonOperator.LTE,
        expected_value="2019-02-01",
    )
    assert evaluator.evaluate(node_date, ctx).root_truth_value == RuleTruthValue.TRUE


def test_comparison_missing_field_evaluates_to_unknown():
    evaluator = DeterministicEvaluator()
    ctx = EvaluationContext(data={}, evaluation_date=date(2026, 1, 1))

    node = ComparisonNode(
        rule_id="RULE_ANNUAL_INCOME",
        field_path="citizen.annual_income",
        operator=ComparisonOperator.LTE,
        expected_value=250000,
    )
    res = evaluator.evaluate(node, ctx)
    assert res.root_truth_value == RuleTruthValue.UNKNOWN
    assert res.overall_result == EligibilityResult.INSUFFICIENT_INFORMATION
    assert "citizen.annual_income" in res.all_missing_fields
    assert "RULE_ANNUAL_INCOME" in res.unknown_rules


# ============================================================================
# 4. Existence Node Evaluator Tests
# ============================================================================

def test_existence_evaluator():
    evaluator = DeterministicEvaluator()
    ctx = EvaluationContext(
        data={"present_val": "ABC", "null_val": None},
        evaluation_date=date(2026, 1, 1),
    )

    # EXISTS
    assert evaluator.evaluate(
        ExistenceNode(field_path="present_val", operator=ExistenceOperator.EXISTS), ctx
    ).root_truth_value == RuleTruthValue.TRUE

    assert evaluator.evaluate(
        ExistenceNode(field_path="null_val", operator=ExistenceOperator.EXISTS), ctx
    ).root_truth_value == RuleTruthValue.TRUE

    res_absent = evaluator.evaluate(
        ExistenceNode(field_path="absent_field", operator=ExistenceOperator.EXISTS), ctx
    )
    assert res_absent.root_truth_value == RuleTruthValue.FALSE
    assert "absent_field" in res_absent.all_missing_fields

    # IS_MISSING
    assert evaluator.evaluate(
        ExistenceNode(field_path="present_val", operator=ExistenceOperator.IS_MISSING), ctx
    ).root_truth_value == RuleTruthValue.FALSE

    assert evaluator.evaluate(
        ExistenceNode(field_path="null_val", operator=ExistenceOperator.IS_MISSING), ctx
    ).root_truth_value == RuleTruthValue.FALSE

    assert evaluator.evaluate(
        ExistenceNode(field_path="absent_field", operator=ExistenceOperator.IS_MISSING), ctx
    ).root_truth_value == RuleTruthValue.TRUE


# ============================================================================
# 5. Temporal / Age Evaluator Tests (SSY Exact Age 10 Boundary & Leap Year)
# ============================================================================

def test_temporal_has_not_attained_age_ssy_boundary():
    evaluator = DeterministicEvaluator()
    rule = TemporalNode(
        rule_id="SSY_AGE_LIMIT",
        operator=TemporalOperator.HAS_NOT_ATTAINED_AGE,
        dob_field="girl_child.dob",
        as_of_field="evaluation_date",
        age_limit=10,
    )

    # DOB: 2014-05-15
    dob_str = "2014-05-15"

    # Case A: Day BEFORE 10th birthday -> Age 9 -> HAS NOT ATTAINED 10 -> TRUE
    ctx_before = EvaluationContext(
        data={"girl_child": {"dob": dob_str}},
        evaluation_date=date(2024, 5, 14),
    )
    res_before = evaluator.evaluate(rule, ctx_before)
    assert res_before.root_truth_value == RuleTruthValue.TRUE
    assert res_before.overall_result == EligibilityResult.ELIGIBLE

    # Case B: ON 10th birthday -> Age 10 -> HAS ATTAINED 10 -> FALSE
    ctx_on_bday = EvaluationContext(
        data={"girl_child": {"dob": dob_str}},
        evaluation_date=date(2024, 5, 15),
    )
    res_on = evaluator.evaluate(rule, ctx_on_bday)
    assert res_on.root_truth_value == RuleTruthValue.FALSE
    assert res_on.overall_result == EligibilityResult.INELIGIBLE
    assert "SSY_AGE_LIMIT" in res_on.failed_rules

    # Case C: Day AFTER 10th birthday -> Age 10 -> FALSE
    ctx_after = EvaluationContext(
        data={"girl_child": {"dob": dob_str}},
        evaluation_date=date(2024, 5, 16),
    )
    res_after = evaluator.evaluate(rule, ctx_after)
    assert res_after.root_truth_value == RuleTruthValue.FALSE


def test_temporal_leap_year_handling():
    evaluator = DeterministicEvaluator()
    rule = TemporalNode(
        operator=TemporalOperator.AGE_AT,
        dob_field="dob",
        comparison_operator=ComparisonOperator.EQ,
        expected_years=1,
    )

    # Born on Leap Day Feb 29, 2020
    dob = "2020-02-29"

    # On Feb 28, 2021 -> has not completed 1 full year -> age is 0
    ctx_feb28 = EvaluationContext(data={"dob": dob}, evaluation_date=date(2021, 2, 28))
    assert evaluator.evaluate(rule, ctx_feb28).root_truth_value == RuleTruthValue.FALSE

    # On March 1, 2021 -> has completed 1 year -> age is 1
    ctx_mar01 = EvaluationContext(data={"dob": dob}, evaluation_date=date(2021, 3, 1))
    assert evaluator.evaluate(rule, ctx_mar01).root_truth_value == RuleTruthValue.TRUE


def test_temporal_future_dob_raises_error():
    evaluator = DeterministicEvaluator()
    rule = TemporalNode(
        operator=TemporalOperator.HAS_NOT_ATTAINED_AGE,
        dob_field="dob",
        age_limit=10,
    )
    ctx = EvaluationContext(data={"dob": "2030-01-01"}, evaluation_date=date(2026, 1, 1))
    with pytest.raises(InvalidTemporalArgumentError):
        evaluator.evaluate(rule, ctx)


# ============================================================================
# 6. Collection Evaluator Tests (COUNT, FOR_ALL, EXISTS_IN)
# ============================================================================

def test_collection_count():
    evaluator = DeterministicEvaluator()

    # COUNT without predicate
    node_count = CollectionNode(
        rule_id="COUNT_GIRLS",
        operator=CollectionOperator.COUNT,
        collection_path="girls",
        comparison_operator=ComparisonOperator.LTE,
        expected_count=2,
    )

    ctx_2 = EvaluationContext(data={"girls": ["A", "B"]}, evaluation_date=date(2026, 1, 1))
    assert evaluator.evaluate(node_count, ctx_2).root_truth_value == RuleTruthValue.TRUE

    ctx_3 = EvaluationContext(data={"girls": ["A", "B", "C"]}, evaluation_date=date(2026, 1, 1))
    assert evaluator.evaluate(node_count, ctx_3).root_truth_value == RuleTruthValue.FALSE

    # COUNT with predicate (only count cultivable parcels)
    pred = ComparisonNode(
        field_path="parcel.is_cultivable",
        operator=ComparisonOperator.EQ,
        expected_value=True,
    )
    node_cultivable = CollectionNode(
        operator=CollectionOperator.COUNT,
        collection_path="parcels",
        item_alias="parcel",
        predicate=pred,
        comparison_operator=ComparisonOperator.GTE,
        expected_count=1,
    )

    ctx_parcels = EvaluationContext(
        data={"parcels": [{"is_cultivable": False}, {"is_cultivable": True}]},
        evaluation_date=date(2026, 1, 1),
    )
    assert evaluator.evaluate(node_cultivable, ctx_parcels).root_truth_value == RuleTruthValue.TRUE


def test_collection_for_all():
    evaluator = DeterministicEvaluator()
    predicate = ComparisonNode(
        field_path="item.is_citizen_of_india",
        operator=ComparisonOperator.EQ,
        expected_value=True,
    )
    node = CollectionNode(
        operator=CollectionOperator.FOR_ALL,
        collection_path="members",
        item_alias="item",
        predicate=predicate,
    )

    # Empty collection is vacuously TRUE
    ctx_empty = EvaluationContext(data={"members": []}, evaluation_date=date(2026, 1, 1))
    assert evaluator.evaluate(node, ctx_empty).root_truth_value == RuleTruthValue.TRUE

    # All pass -> TRUE
    ctx_all_pass = EvaluationContext(
        data={"members": [{"is_citizen_of_india": True}, {"is_citizen_of_india": True}]},
        evaluation_date=date(2026, 1, 1),
    )
    assert evaluator.evaluate(node, ctx_all_pass).root_truth_value == RuleTruthValue.TRUE

    # One fails -> FALSE
    ctx_one_fail = EvaluationContext(
        data={"members": [{"is_citizen_of_india": True}, {"is_citizen_of_india": False}]},
        evaluation_date=date(2026, 1, 1),
    )
    assert evaluator.evaluate(node, ctx_one_fail).root_truth_value == RuleTruthValue.FALSE

    # One unknown, none false -> UNKNOWN
    ctx_one_unk = EvaluationContext(
        data={"members": [{"is_citizen_of_india": True}, {}]},
        evaluation_date=date(2026, 1, 1),
    )
    assert evaluator.evaluate(node, ctx_one_unk).root_truth_value == RuleTruthValue.UNKNOWN


def test_collection_exists_in():
    evaluator = DeterministicEvaluator()
    predicate = ComparisonNode(
        field_path="member.is_pensioner",
        operator=ComparisonOperator.EQ,
        expected_value=True,
    )
    node = CollectionNode(
        operator=CollectionOperator.EXISTS_IN,
        collection_path="members",
        item_alias="member",
        predicate=predicate,
    )

    # Empty collection -> FALSE
    ctx_empty = EvaluationContext(data={"members": []}, evaluation_date=date(2026, 1, 1))
    assert evaluator.evaluate(node, ctx_empty).root_truth_value == RuleTruthValue.FALSE

    # One true -> TRUE
    ctx_true = EvaluationContext(
        data={"members": [{"is_pensioner": False}, {"is_pensioner": True}]},
        evaluation_date=date(2026, 1, 1),
    )
    assert evaluator.evaluate(node, ctx_true).root_truth_value == RuleTruthValue.TRUE

    # All false -> FALSE
    ctx_false = EvaluationContext(
        data={"members": [{"is_pensioner": False}, {"is_pensioner": False}]},
        evaluation_date=date(2026, 1, 1),
    )
    assert evaluator.evaluate(node, ctx_false).root_truth_value == RuleTruthValue.FALSE


# ============================================================================
# 7. Aggregation Node Tests (AGGREGATE_SUM)
# ============================================================================

def test_aggregation_sum():
    evaluator = DeterministicEvaluator()
    node = AggregationNode(
        rule_id="RULE_LAND_CEILING_2HA",
        operator=AggregationOperator.AGGREGATE_SUM,
        collection_path="parcels",
        value_field="area_ha",
        comparison_operator=ComparisonOperator.LTE,
        expected_value=2.0,
    )

    # Sum = 1.2 + 0.7 = 1.9 <= 2.0 -> TRUE
    ctx_pass = EvaluationContext(
        data={"parcels": [{"area_ha": 1.2}, {"area_ha": 0.7}]},
        evaluation_date=date(2026, 1, 1),
    )
    assert evaluator.evaluate(node, ctx_pass).root_truth_value == RuleTruthValue.TRUE

    # Sum = 1.5 + 1.0 = 2.5 <= 2.0 -> FALSE
    ctx_fail = EvaluationContext(
        data={"parcels": [{"area_ha": 1.5}, {"area_ha": 1.0}]},
        evaluation_date=date(2026, 1, 1),
    )
    assert evaluator.evaluate(node, ctx_fail).root_truth_value == RuleTruthValue.FALSE

    # Missing field in one parcel -> UNKNOWN
    ctx_missing = EvaluationContext(
        data={"parcels": [{"area_ha": 1.5}, {"area_ha": None}]},
        evaluation_date=date(2026, 1, 1),
    )
    res = evaluator.evaluate(node, ctx_missing)
    assert res.root_truth_value == RuleTruthValue.UNKNOWN
    assert "parcels[1].area_ha" in res.all_missing_fields


# ============================================================================
# 8. Context Scope Evaluator Tests
# ============================================================================

def test_context_scope_evaluator():
    evaluator = DeterministicEvaluator()
    inner_rule = ComparisonNode(
        rule_id="FATHER_NOT_INCOME_TAX_PAYEE",
        field_path="father.pays_income_tax",
        operator=ComparisonOperator.EQ,
        expected_value=False,
    )
    scope_node = ContextScopeNode(
        rule_id="CHECK_FATHER_TAX",
        operator=ContextOperator.EVALUATE_FAMILY_MEMBER,
        collection_path="family.members",
        selector_field="role",
        selector_value="FATHER",
        member_alias="father",
        rule=inner_rule,
    )

    # Match found and satisfies
    ctx_pass = EvaluationContext(
        data={"family": {"members": [{"role": "FATHER", "pays_income_tax": False}]}},
        evaluation_date=date(2026, 1, 1),
    )
    assert evaluator.evaluate(scope_node, ctx_pass).root_truth_value == RuleTruthValue.TRUE

    # Member not found in family -> UNKNOWN
    ctx_absent = EvaluationContext(
        data={"family": {"members": [{"role": "MOTHER", "pays_income_tax": False}]}},
        evaluation_date=date(2026, 1, 1),
    )
    res_absent = evaluator.evaluate(scope_node, ctx_absent)
    assert res_absent.root_truth_value == RuleTruthValue.UNKNOWN
    assert "family.members[role=FATHER]" in res_absent.all_missing_fields


# ============================================================================
# 9. Complex Composite Ruleset & Trace Verification
# ============================================================================

def test_composite_ruleset_trace_and_bilingual_explanation():
    evaluator = DeterministicEvaluator()

    # Rule: Farmer must have cultivable land AND must not be an institutional landholder
    r1 = ComparisonNode(
        rule_id="RULE_HAS_LAND",
        description_en="Citizen owns cultivable agricultural land",
        description_hi="नागरिक के पास कृषि योग्य भूमि है",
        field_path="land.is_cultivable",
        operator=ComparisonOperator.EQ,
        expected_value=True,
    )
    r2 = ComparisonNode(
        rule_id="RULE_INSTITUTIONAL",
        description_en="Citizen is an institutional landholder",
        description_hi="नागरिक संस्थागत भूमिधारक है",
        field_path="citizen.is_institutional_landholder",
        operator=ComparisonOperator.EQ,
        expected_value=True,
    )
    r2_not = LogicalNode(
        rule_id="RULE_NOT_INSTITUTIONAL",
        description_en="Citizen is not an institutional landholder",
        description_hi="नागरिक संस्थागत भूमिधारक नहीं है",
        operator=LogicalOperator.NOT,
        child=r2,
    )
    root = LogicalNode(
        rule_id="ROOT_PMKISAN_EXCLUSION_CHECK",
        description_en="Primary landholder qualification criteria",
        description_hi="प्राथमिक भूमिधारक अर्हता मानदंड",
        operator=LogicalOperator.AND,
        children=[r1, r2_not],
    )

    # Valid qualifying citizen
    ctx = EvaluationContext(
        data={
            "land": {"is_cultivable": True},
            "citizen": {"is_institutional_landholder": False},
        },
        evaluation_date=date(2026, 1, 1),
        policy_metadata={"scheme": "PM-KISAN", "version": "v2019"},
    )
    result = evaluator.evaluate(root, ctx)

    assert result.overall_result == EligibilityResult.ELIGIBLE
    assert result.root_truth_value == RuleTruthValue.TRUE
    assert "RULE_HAS_LAND" in result.satisfied_rules
    assert "RULE_NOT_INSTITUTIONAL" in result.satisfied_rules
    assert "RULE_INSTITUTIONAL" in result.failed_rules
    assert len(result.all_missing_fields) == 0

    # Serialization
    res_dict = result.to_dict()
    assert res_dict["overall_result"] == "ELIGIBLE"
    assert res_dict["metadata"]["scheme"] == "PM-KISAN"

    json_str = result.to_json()
    assert "PM-KISAN" in json_str
    parsed = json.loads(json_str)
    assert parsed["overall_result"] == "ELIGIBLE"


# ============================================================================
# 10. Determinism & Security Tests
# ============================================================================

def test_evaluator_determinism():
    """Ensure identical inputs produce identical outputs across repeated executions."""
    evaluator = DeterministicEvaluator()
    node = LogicalNode(
        operator=LogicalOperator.AND,
        children=[
            ComparisonNode(field_path="a", operator=ComparisonOperator.EQ, expected_value=10),
            ComparisonNode(field_path="b", operator=ComparisonOperator.GT, expected_value=5),
        ],
    )
    ctx = EvaluationContext(data={"a": 10, "b": 7}, evaluation_date=date(2026, 1, 1))

    first_result = evaluator.evaluate(node, ctx).to_json()
    for _ in range(10):
        next_result = evaluator.evaluate(node, ctx).to_json()
        assert next_result == first_result


def test_evaluator_security_against_code_injection():
    """Verify that malicious payload strings are never evaluated as Python code."""
    evaluator = DeterministicEvaluator()
    malicious_payload = "__import__('os').system('echo pwned')"

    node = ComparisonNode(
        field_path="input_field",
        operator=ComparisonOperator.EQ,
        expected_value=malicious_payload,
    )
    ctx = EvaluationContext(
        data={"input_field": malicious_payload},
        evaluation_date=date(2026, 1, 1),
    )

    # Evaluates literally as a string comparison, never executing the payload
    res = evaluator.evaluate(node, ctx)
    assert res.root_truth_value == RuleTruthValue.TRUE
    assert res.root_node_result.actual_value == malicious_payload


# ============================================================================
# 11. Final Semantic Audit Tests
# ============================================================================

def test_evaluate_family_member_all_seven_cases():
    """Verify exact semantics for all 7 EVALUATE_FAMILY_MEMBER cases (A through G)."""
    evaluator = DeterministicEvaluator()
    inner_rule = ComparisonNode(
        rule_id="CHECK_PENSION",
        field_path="father.monthly_pension",
        operator=ComparisonOperator.LTE,
        expected_value=10000,
    )
    scope_node = ContextScopeNode(
        rule_id="SCOPE_FATHER",
        operator=ContextOperator.EVALUATE_FAMILY_MEMBER,
        collection_path="family.members",
        selector_field="role",
        selector_value="FATHER",
        member_alias="father",
        rule=inner_rule,
    )

    # Case A: Collection itself is missing
    ctx_a = EvaluationContext(data={}, evaluation_date=date(2026, 1, 1))
    res_a = evaluator.evaluate(scope_node, ctx_a)
    assert res_a.root_truth_value == RuleTruthValue.UNKNOWN
    assert res_a.overall_result == EligibilityResult.INSUFFICIENT_INFORMATION
    assert "family.members" in res_a.all_missing_fields
    assert res_a.root_node_result.actual_value is None

    # Case B: Collection exists but is empty
    ctx_b = EvaluationContext(data={"family": {"members": []}}, evaluation_date=date(2026, 1, 1))
    res_b = evaluator.evaluate(scope_node, ctx_b)
    assert res_b.root_truth_value == RuleTruthValue.UNKNOWN
    assert "family.members[role=FATHER]" in res_b.all_missing_fields

    # Case C: Collection exists and contains no matching member
    ctx_c = EvaluationContext(
        data={"family": {"members": [{"role": "MOTHER", "monthly_pension": 5000}]}},
        evaluation_date=date(2026, 1, 1),
    )
    res_c = evaluator.evaluate(scope_node, ctx_c)
    assert res_c.root_truth_value == RuleTruthValue.UNKNOWN
    assert "family.members[role=FATHER]" in res_c.all_missing_fields

    # Case D: Matching member exists but requested field is missing
    ctx_d = EvaluationContext(
        data={"family": {"members": [{"role": "FATHER"}]}},
        evaluation_date=date(2026, 1, 1),
    )
    res_d = evaluator.evaluate(scope_node, ctx_d)
    assert res_d.root_truth_value == RuleTruthValue.UNKNOWN
    assert "father.monthly_pension" in res_d.all_missing_fields

    # Case E: Matching member exists and requested field is explicitly null
    ctx_e = EvaluationContext(
        data={"family": {"members": [{"role": "FATHER", "monthly_pension": None}]}},
        evaluation_date=date(2026, 1, 1),
    )
    res_e = evaluator.evaluate(scope_node, ctx_e)
    assert res_e.root_truth_value == RuleTruthValue.UNKNOWN
    assert "father.monthly_pension" in res_d.all_missing_fields

    # Case F: Matching member exists and predicate evaluates FALSE
    ctx_f = EvaluationContext(
        data={"family": {"members": [{"role": "FATHER", "monthly_pension": 15000}]}},
        evaluation_date=date(2026, 1, 1),
    )
    res_f = evaluator.evaluate(scope_node, ctx_f)
    assert res_f.root_truth_value == RuleTruthValue.FALSE
    assert res_f.overall_result == EligibilityResult.INELIGIBLE
    assert "SCOPE_FATHER" in res_f.failed_rules
    assert len(res_f.all_missing_fields) == 0

    # Case G: Matching member exists and predicate evaluates TRUE
    ctx_g = EvaluationContext(
        data={"family": {"members": [{"role": "FATHER", "monthly_pension": 8000}]}},
        evaluation_date=date(2026, 1, 1),
    )
    res_g = evaluator.evaluate(scope_node, ctx_g)
    assert res_g.root_truth_value == RuleTruthValue.TRUE
    assert res_g.overall_result == EligibilityResult.ELIGIBLE
    assert "SCOPE_FATHER" in res_g.satisfied_rules
    assert len(res_g.all_missing_fields) == 0


def test_collection_unknown_propagation_matrix():
    """Verify exact 10-point truth matrix for FOR_ALL and EXISTS_IN under Kleene logic."""
    evaluator = DeterministicEvaluator()
    pred = ComparisonNode(
        field_path="item.status",
        operator=ComparisonOperator.EQ,
        expected_value="QUALIFIED",
    )

    for_all_node = CollectionNode(
        operator=CollectionOperator.FOR_ALL,
        collection_path="items",
        item_alias="item",
        predicate=pred,
    )
    exists_in_node = CollectionNode(
        operator=CollectionOperator.EXISTS_IN,
        collection_path="items",
        item_alias="item",
        predicate=pred,
    )

    # Item sets:
    T = {"status": "QUALIFIED"}
    F = {"status": "DISQUALIFIED"}
    U = {}  # missing 'status' field -> UNKNOWN

    # FOR_ALL:
    # 1. [T, T] -> TRUE
    assert evaluator.evaluate(for_all_node, EvaluationContext(data={"items": [T, T]}, evaluation_date=date(2026, 1, 1))).root_truth_value == RuleTruthValue.TRUE
    # 2. [T, U] -> UNKNOWN
    assert evaluator.evaluate(for_all_node, EvaluationContext(data={"items": [T, U]}, evaluation_date=date(2026, 1, 1))).root_truth_value == RuleTruthValue.UNKNOWN
    # 3. [T, F] -> FALSE
    assert evaluator.evaluate(for_all_node, EvaluationContext(data={"items": [T, F]}, evaluation_date=date(2026, 1, 1))).root_truth_value == RuleTruthValue.FALSE
    # 4. [U, U] -> UNKNOWN
    assert evaluator.evaluate(for_all_node, EvaluationContext(data={"items": [U, U]}, evaluation_date=date(2026, 1, 1))).root_truth_value == RuleTruthValue.UNKNOWN
    # 5. [] -> TRUE (vacuous truth)
    assert evaluator.evaluate(for_all_node, EvaluationContext(data={"items": []}, evaluation_date=date(2026, 1, 1))).root_truth_value == RuleTruthValue.TRUE

    # EXISTS_IN:
    # 6. [T, F] -> TRUE
    assert evaluator.evaluate(exists_in_node, EvaluationContext(data={"items": [T, F]}, evaluation_date=date(2026, 1, 1))).root_truth_value == RuleTruthValue.TRUE
    # 7. [F, U] -> UNKNOWN
    assert evaluator.evaluate(exists_in_node, EvaluationContext(data={"items": [F, U]}, evaluation_date=date(2026, 1, 1))).root_truth_value == RuleTruthValue.UNKNOWN
    # 8. [F, F] -> FALSE
    assert evaluator.evaluate(exists_in_node, EvaluationContext(data={"items": [F, F]}, evaluation_date=date(2026, 1, 1))).root_truth_value == RuleTruthValue.FALSE
    # 9. [T, U] -> TRUE
    assert evaluator.evaluate(exists_in_node, EvaluationContext(data={"items": [T, U]}, evaluation_date=date(2026, 1, 1))).root_truth_value == RuleTruthValue.TRUE
    # 10. [] -> FALSE
    assert evaluator.evaluate(exists_in_node, EvaluationContext(data={"items": []}, evaluation_date=date(2026, 1, 1))).root_truth_value == RuleTruthValue.FALSE


def test_type_coercion_rules():
    """Verify strict controlled type conversions and rejections."""
    evaluator = DeterministicEvaluator()
    ref_date = date(2026, 1, 1)

    # 1. string vs integer
    node_str_int_eq = ComparisonNode(field_path="val", operator=ComparisonOperator.EQ, expected_value=25)
    ctx_str = EvaluationContext(data={"val": "25"}, evaluation_date=ref_date)
    assert evaluator.evaluate(node_str_int_eq, ctx_str).root_truth_value == RuleTruthValue.FALSE

    node_str_int_gt = ComparisonNode(field_path="val", operator=ComparisonOperator.GT, expected_value=20)
    with pytest.raises(TypeMismatchError):
        evaluator.evaluate(node_str_int_gt, ctx_str)

    # 2. integer vs decimal
    node_int_dec = ComparisonNode(field_path="val", operator=ComparisonOperator.EQ, expected_value=Decimal("100"))
    ctx_int = EvaluationContext(data={"val": 100}, evaluation_date=ref_date)
    assert evaluator.evaluate(node_int_dec, ctx_int).root_truth_value == RuleTruthValue.TRUE

    # 3. string numeric vs numeric
    node_str_num = ComparisonNode(field_path="val", operator=ComparisonOperator.EQ, expected_value=10.5)
    ctx_str_num = EvaluationContext(data={"val": "10.5"}, evaluation_date=ref_date)
    assert evaluator.evaluate(node_str_num, ctx_str_num).root_truth_value == RuleTruthValue.FALSE

    node_str_num_lt = ComparisonNode(field_path="val", operator=ComparisonOperator.LT, expected_value=15.0)
    with pytest.raises(TypeMismatchError):
        evaluator.evaluate(node_str_num_lt, ctx_str_num)

    # 4. string ISO date vs date
    node_date_str = ComparisonNode(field_path="val", operator=ComparisonOperator.EQ, expected_value="2026-01-01")
    ctx_date = EvaluationContext(data={"val": date(2026, 1, 1)}, evaluation_date=ref_date)
    assert evaluator.evaluate(node_date_str, ctx_date).root_truth_value == RuleTruthValue.TRUE

    # 5. date vs datetime
    node_datetime = ComparisonNode(field_path="val", operator=ComparisonOperator.EQ, expected_value=date(2026, 1, 1))
    ctx_dt = EvaluationContext(data={"val": datetime(2026, 1, 1, 15, 30)}, evaluation_date=ref_date)
    assert evaluator.evaluate(node_datetime, ctx_dt).root_truth_value == RuleTruthValue.TRUE

    # 6. boolean vs integer (prevent Python bool == int coercion)
    node_bool_int = ComparisonNode(field_path="val", operator=ComparisonOperator.EQ, expected_value=1)
    ctx_bool = EvaluationContext(data={"val": True}, evaluation_date=ref_date)
    assert evaluator.evaluate(node_bool_int, ctx_bool).root_truth_value == RuleTruthValue.FALSE

    node_bool_int_gt = ComparisonNode(field_path="val", operator=ComparisonOperator.GT, expected_value=0)
    with pytest.raises(TypeMismatchError):
        evaluator.evaluate(node_bool_int_gt, ctx_bool)


def test_deterministic_serialization_canonical_ordering():
    """Verify that serialization produces byte-for-byte identical output regardless of dict key insertion order."""
    evaluator = DeterministicEvaluator()
    node = ComparisonNode(field_path="age", operator=ComparisonOperator.GTE, expected_value=18)

    # Context 1: keys inserted in order X, Y, Z
    ctx1 = EvaluationContext(
        data={"age": 20},
        evaluation_date=date(2026, 1, 1),
        policy_metadata={"alpha": "first", "beta": "second", "gamma": "third"},
    )
    # Context 2: keys inserted in reverse order Z, Y, X
    ctx2 = EvaluationContext(
        data={"age": 20},
        evaluation_date=date(2026, 1, 1),
        policy_metadata={"gamma": "third", "beta": "second", "alpha": "first"},
    )

    json1 = evaluator.evaluate(node, ctx1).to_json(indent=2)
    json2 = evaluator.evaluate(node, ctx2).to_json(indent=2)

    # Must be byte-for-byte identical
    assert json1.encode("utf-8") == json2.encode("utf-8")
