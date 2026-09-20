"""Comprehensive unit and integration tests for Phase 4 Explainability, Provenance, and Audit."""

from datetime import date, datetime, timezone
import json
import uuid
import pytest
from sqlalchemy import select

from app.engine import (
    ComparisonNode,
    ComparisonOperator,
    ContextOperator,
    ContextScopeNode,
    DeterministicEvaluator,
    EvaluationContext,
    LogicalNode,
    LogicalOperator,
    RuleTruthValue,
)
from app.engine.explainability import (
    AUDIT_SCHEMA_VERSION,
    AuditEvaluationRecord,
    BLOCKER_SCHEMA_VERSION,
    BlockerCategory,
    EVALUATOR_VERSION,
    EXPLANATION_SCHEMA_VERSION,
    ExplainabilityTrace,
    InformationGapBlocker,
    InputSnapshot,
    PolicyProvenance,
    PROVENANCE_SCHEMA_VERSION,
    TRACE_SCHEMA_VERSION,
    build_explainability_trace,
    compute_canonical_rule_hash,
    compute_input_snapshot_hash,
    create_audit_evaluation_record,
    generate_rule_explanation,
)
from app.models.citizen import Citizen
from app.models.enums import EligibilityResult, EvidenceStatus, SchemeStatus
from app.models.evaluation import EvaluationTrace
from app.models.scheme import PolicyVersion, RuleSet, Scheme


# ============================================================================
# Helpers for generic scheme-agnostic test fixtures
# ============================================================================

def make_sample_provenance(canonical_hash: str) -> PolicyProvenance:
    return PolicyProvenance(
        scheme_id=uuid.uuid4(),
        scheme_code="SCHEME_GENERIC_ALPHA",
        policy_version_id=uuid.uuid4(),
        policy_version_code="v2026.1",
        rule_set_id=uuid.uuid4(),
        rule_set_version="1.0.0",
        canonical_rule_hash=canonical_hash,
        evaluation_date=date(2026, 1, 1),
        effective_from=date(2025, 1, 1),
        effective_to=None,
        source_url="https://gov.in/schemes/alpha-gazette.pdf",
        source_title="Generic Scheme Statutory Notification 2025",
        source_clause="Section 3(2)",
    )


# ============================================================================
# 1. Canonical Rule Hashing Tests (Requirements I, J, K)
# ============================================================================

def test_canonical_rule_hashing_identical():
    """Identical rule definitions produce identical SHA-256 hashes regardless of dict key order."""
    rule_dict_1 = {
        "node_type": "comparison",
        "operator": "GTE",
        "field_path": "citizen.age",
        "expected_value": 18,
        "rule_id": "RULE_ADULT",
    }
    # Opposite key insertion order
    rule_dict_2 = {
        "rule_id": "RULE_ADULT",
        "expected_value": 18,
        "field_path": "citizen.age",
        "operator": "GTE",
        "node_type": "comparison",
    }

    hash1 = compute_canonical_rule_hash(rule_dict_1)
    hash2 = compute_canonical_rule_hash(rule_dict_2)

    assert len(hash1) == 64
    assert hash1 == hash2

    # Pydantic node matches dictionary
    node = ComparisonNode(
        rule_id="RULE_ADULT",
        field_path="citizen.age",
        operator=ComparisonOperator.GTE,
        expected_value=18,
    )
    hash_node = compute_canonical_rule_hash(node)
    assert hash_node == hash1


def test_canonical_rule_hashing_different():
    """Different rule definitions produce distinctly different hashes."""
    node1 = ComparisonNode(
        rule_id="RULE_INCOME",
        field_path="citizen.income",
        operator=ComparisonOperator.LTE,
        expected_value=100000,
    )
    # Different threshold
    node2 = ComparisonNode(
        rule_id="RULE_INCOME",
        field_path="citizen.income",
        operator=ComparisonOperator.LTE,
        expected_value=200000,
    )
    # Different operator
    node3 = ComparisonNode(
        rule_id="RULE_INCOME",
        field_path="citizen.income",
        operator=ComparisonOperator.LT,
        expected_value=100000,
    )

    h1 = compute_canonical_rule_hash(node1)
    h2 = compute_canonical_rule_hash(node2)
    h3 = compute_canonical_rule_hash(node3)

    assert h1 != h2
    assert h1 != h3
    assert h2 != h3


def test_canonical_rule_hashing_adversarial_collisions():
    """Adversarial test cases proving that structural distinctions are strictly preserved.
    
    Verifies that empty containers, empty strings, and None values do not collide
    with empty or absent structures.
    """
    # Adversarial Pair 1: {"x": {}} vs {}
    h_dict_empty_nested = compute_canonical_rule_hash({"x": {}})
    h_dict_empty = compute_canonical_rule_hash({})
    assert h_dict_empty_nested != h_dict_empty, "Collision: {'x': {}} must not collide with {}"

    # Adversarial Pair 2: {"x": []} vs {}
    h_list_empty_nested = compute_canonical_rule_hash({"x": []})
    assert h_list_empty_nested != h_dict_empty, "Collision: {'x': []} must not collide with {}"

    # Adversarial Pair 3: {"x": ""} vs {}
    h_str_empty_nested = compute_canonical_rule_hash({"x": ""})
    assert h_str_empty_nested != h_dict_empty, "Collision: {'x': ''} must not collide with {}"

    # Adversarial Pair 4: {"x": None} vs {}
    h_none_nested = compute_canonical_rule_hash({"x": None})
    assert h_none_nested != h_dict_empty, "Collision: {'x': None} must not collide with {}"

    # Cross-adversarial comparisons between distinct empty types
    assert h_dict_empty_nested != h_list_empty_nested, "{'x': {}} must not collide with {'x': []}"
    assert h_dict_empty_nested != h_str_empty_nested, "{'x': {}} must not collide with {'x': ''}"
    assert h_dict_empty_nested != h_none_nested, "{'x': {}} must not collide with {'x': None}"
    assert h_list_empty_nested != h_str_empty_nested, "{'x': []} must not collide with {'x': ''}"

    # Deep structural distinction: {"a": {"b": {}}} vs {"a": {}}
    h_deep1 = compute_canonical_rule_hash({"a": {"b": {}}})
    h_deep2 = compute_canonical_rule_hash({"a": {}})
    assert h_deep1 != h_deep2, "{'a': {'b': {}}} must not collide with {'a': {}}"


# ============================================================================
# 2. Rule Explanations: TRUE, FALSE, UNKNOWN (Requirements A, B, C, T, U, V)
# ============================================================================

def test_rule_explanation_outcomes_and_bilingual_fidelity():
    evaluator = DeterministicEvaluator()
    rule = ComparisonNode(
        rule_id="R_SCORE",
        description_en="Score threshold qualification",
        description_hi="स्कोर सीमा अर्हता",
        field_path="applicant.score",
        operator=ComparisonOperator.GTE,
        expected_value=75,
    )

    # A. TRUE rule
    ctx_true = EvaluationContext(data={"applicant": {"score": 80}}, evaluation_date=date(2026, 1, 1))
    res_true = evaluator.evaluate(rule, ctx_true)
    exp_true = generate_rule_explanation(res_true.root_node_result)

    assert exp_true.truth_value == RuleTruthValue.TRUE
    assert "satisfied" in exp_true.summary_en.lower()
    assert "पूरी हुई" in exp_true.summary_hi
    # Explanation does not change engine result
    assert res_true.root_truth_value == RuleTruthValue.TRUE
    assert res_true.overall_result == EligibilityResult.ELIGIBLE

    # B. FALSE rule
    ctx_false = EvaluationContext(data={"applicant": {"score": 60}}, evaluation_date=date(2026, 1, 1))
    res_false = evaluator.evaluate(rule, ctx_false)
    exp_false = generate_rule_explanation(res_false.root_node_result)

    assert exp_false.truth_value == RuleTruthValue.FALSE
    assert "not satisfied" in exp_false.summary_en.lower()
    assert "पूरी नहीं हुई" in exp_false.summary_hi
    assert res_false.root_truth_value == RuleTruthValue.FALSE

    # C. UNKNOWN rule
    ctx_unk = EvaluationContext(data={"applicant": {}}, evaluation_date=date(2026, 1, 1))
    res_unk = evaluator.evaluate(rule, ctx_unk)
    exp_unk = generate_rule_explanation(res_unk.root_node_result)

    assert exp_unk.truth_value == RuleTruthValue.UNKNOWN
    assert "unresolved" in exp_unk.summary_en.lower()
    assert "अनिर्धारित" in exp_unk.summary_hi
    assert "applicant.score" in exp_unk.detail_en
    assert res_unk.root_truth_value == RuleTruthValue.UNKNOWN


# ============================================================================
# 3. Blockers and Information Gaps (Requirement D, S)
# ============================================================================

def test_missing_field_blocker_generation():
    evaluator = DeterministicEvaluator()
    rule = LogicalNode(
        rule_id="ROOT_CHECK",
        operator=LogicalOperator.AND,
        children=[
            ComparisonNode(rule_id="R1", field_path="facts.required_a", operator=ComparisonOperator.EQ, expected_value="YES"),
            ComparisonNode(rule_id="R2", field_path="facts.required_b", operator=ComparisonOperator.EQ, expected_value="YES"),
        ],
    )
    # facts.required_b is missing
    ctx = EvaluationContext(data={"facts": {"required_a": "YES"}}, evaluation_date=date(2026, 1, 1))
    eval_res = evaluator.evaluate(rule, ctx)

    provenance = make_sample_provenance(compute_canonical_rule_hash(rule))
    trace = build_explainability_trace(eval_res, provenance)

    assert len(trace.blockers) == 1
    b = trace.blockers[0]
    assert b.category == BlockerCategory.MISSING_FIELD
    assert b.field_path == "facts.required_b"
    assert "facts.required_b" in b.message_en
    assert "facts.required_b" in b.message_hi
    assert b.code.startswith("BLOCKER_MISSING_")


def test_evidence_status_distinct_from_eligibility_status():
    """Verify evidence verification status is distinct from eligibility truth value."""
    node = ComparisonNode(
        rule_id="RULE_DOC",
        field_path="applicant.residence",
        operator=ComparisonOperator.EQ,
        expected_value="METRO",
    )
    evaluator = DeterministicEvaluator()
    ctx = EvaluationContext(data={"applicant": {"residence": "METRO"}}, evaluation_date=date(2026, 1, 1))
    res = evaluator.evaluate(node, ctx)

    provenance = make_sample_provenance(compute_canonical_rule_hash(node))
    trace = build_explainability_trace(res, provenance)

    # Attach evidence link without altering eligibility
    trace.root_node.evidence_reference = "ev-doc-987"
    trace.root_node.evidence_status = "PENDING"
    trace.root_node.verification_reference = "vrf-123"

    # Eligibility remains definitively ELIGIBLE (TRUE)
    assert trace.overall_result == EligibilityResult.ELIGIBLE
    assert trace.root_node.truth_value == RuleTruthValue.TRUE
    assert trace.root_node.evidence_status == "PENDING"


# ============================================================================
# 4. Trace Traversal Ordering & Nested Logic (Requirements E, F)
# ============================================================================

def test_deterministic_trace_traversal_ordering():
    """Verify depth-first pre-order traversal assigns consecutive 1-based order."""
    evaluator = DeterministicEvaluator()
    # Tree:
    # AND (order 1)
    #  ├── R_A (order 2)
    #  ├── R_B (order 3)
    #  └── OR  (order 4)
    #       ├── R_C (order 5)
    #       └── R_D (order 6)
    r_a = ComparisonNode(rule_id="R_A", field_path="a", operator=ComparisonOperator.EQ, expected_value=1)
    r_b = ComparisonNode(rule_id="R_B", field_path="b", operator=ComparisonOperator.EQ, expected_value=2)
    r_c = ComparisonNode(rule_id="R_C", field_path="c", operator=ComparisonOperator.EQ, expected_value=3)
    r_d = ComparisonNode(rule_id="R_D", field_path="d", operator=ComparisonOperator.EQ, expected_value=4)

    or_node = LogicalNode(rule_id="OR_NODE", operator=LogicalOperator.OR, children=[r_c, r_d])
    root_node = LogicalNode(rule_id="ROOT_AND", operator=LogicalOperator.AND, children=[r_a, r_b, or_node])

    ctx = EvaluationContext(data={"a": 1, "b": 2, "c": 3, "d": 0}, evaluation_date=date(2026, 1, 1))
    eval_res = evaluator.evaluate(root_node, ctx)

    provenance = make_sample_provenance(compute_canonical_rule_hash(root_node))
    trace = build_explainability_trace(eval_res, provenance)

    assert len(trace.ordered_nodes) == 6
    expected_orders = [
        ("ROOT_AND", 1, None),
        ("R_A", 2, "trc-0001"),
        ("R_B", 3, "trc-0001"),
        ("OR_NODE", 4, "trc-0001"),
        ("R_C", 5, "trc-0004"),
        ("R_D", 6, "trc-0004"),
    ]

    for node, (exp_rule_id, exp_order, exp_parent_trace) in zip(trace.ordered_nodes, expected_orders):
        assert node.rule_id == exp_rule_id
        assert node.evaluation_order == exp_order
        assert node.parent_trace_id == exp_parent_trace


# ============================================================================
# 5. Family Member Context Preservation (Requirement G, U)
# ============================================================================

def test_family_member_context_preserved_without_pii():
    evaluator = DeterministicEvaluator()
    inner = ComparisonNode(
        rule_id="CHECK_PENSION",
        field_path="member.pension",
        operator=ComparisonOperator.LT,
        expected_value=5000,
    )
    scope = ContextScopeNode(
        rule_id="FATHER_PENSION_CHECK",
        operator=ContextOperator.EVALUATE_FAMILY_MEMBER,
        collection_path="family.members",
        selector_field="role",
        selector_value="FATHER",
        member_alias="member",
        rule=inner,
    )

    ctx = EvaluationContext(
        data={"family": {"members": [{"role": "FATHER", "pension": 4000}]}},
        evaluation_date=date(2026, 1, 1),
    )
    eval_res = evaluator.evaluate(scope, ctx)

    provenance = make_sample_provenance(compute_canonical_rule_hash(scope))
    trace = build_explainability_trace(eval_res, provenance)

    assert len(trace.ordered_nodes) == 2
    root_trace = trace.ordered_nodes[0]
    inner_trace = trace.ordered_nodes[1]

    # Context preserved synthetically
    assert root_trace.family_member_context is not None
    assert root_trace.family_member_context["selector_value"] == "FATHER"
    assert inner_trace.family_member_context is not None
    assert inner_trace.family_member_context["selector_value"] == "FATHER"

    # No raw sensitive PII in explanation
    assert "Aadhaar" not in inner_trace.explanation_en
    assert "Aadhaar" not in inner_trace.explanation_hi


# ============================================================================
# 6. Audit Record & Historical Reproducibility (Req H, L, M, N, O, P, Q, R, X)
# ============================================================================

def test_audit_record_full_lifecycle_and_serialization():
    evaluator = DeterministicEvaluator()
    rule = ComparisonNode(
        rule_id="RULE_CREDIT",
        field_path="user.credit_score",
        operator=ComparisonOperator.GTE,
        expected_value=700,
    )
    facts = {"user": {"credit_score": 750}}
    eval_date = date(2026, 1, 1)
    ctx = EvaluationContext(data=facts, evaluation_date=eval_date)
    eval_res = evaluator.evaluate(rule, ctx)

    provenance = make_sample_provenance(compute_canonical_rule_hash(rule))
    trace = build_explainability_trace(eval_res, provenance)

    eval_uuid = uuid.uuid4()
    audit_record = create_audit_evaluation_record(
        citizen_ref="cit-synthetic-test-001",
        input_data=facts,
        provenance=provenance,
        explainability_trace=trace,
        evaluation_id=eval_uuid,
    )

    # Schema versions
    assert audit_record.schema_version == AUDIT_SCHEMA_VERSION
    assert audit_record.explainability_trace.trace_version == TRACE_SCHEMA_VERSION
    assert audit_record.explainability_trace.evaluator_version == EVALUATOR_VERSION

    # Preserves final result and root truth value
    assert audit_record.final_result == EligibilityResult.ELIGIBLE
    assert audit_record.root_truth_value == RuleTruthValue.TRUE

    # Preserves historical evaluation date, policy version, and input snapshot
    assert audit_record.evaluation_date == eval_date
    assert audit_record.policy_version_code == "v2026.1"
    assert audit_record.input_snapshot.data == facts
    assert len(audit_record.input_snapshot.snapshot_hash) == 64

    # Preserves provenance and rule trace
    assert audit_record.provenance.canonical_rule_hash == provenance.canonical_rule_hash
    assert len(audit_record.explainability_trace.ordered_nodes) == 1

    # Deterministic JSON serialization
    json1 = audit_record.to_json(indent=2)
    json2 = audit_record.to_json(indent=2)
    assert json1.encode("utf-8") == json2.encode("utf-8")

    parsed = json.loads(json1)
    assert parsed["citizen_ref"] == "cit-synthetic-test-001"
    assert parsed["final_result"] == "ELIGIBLE"


# ============================================================================
# 7. Database Persistence Integration (Phase 2 Model Bridge)
# ============================================================================

@pytest.mark.asyncio
async def test_audit_record_persists_to_database(db_session):
    """Verify that AuditEvaluationRecord maps cleanly to SQLAlchemy EvaluationTrace and commits."""
    # 1. Create prerequisites in database
    scheme_code_val = f"SCHEME_TEST_{uuid.uuid4().hex[:6]}"
    scheme = Scheme(
        scheme_code=scheme_code_val,
        name_en="Test Audit Scheme",
        name_hi="परीक्षण ऑडिट योजना",
        description_en="Test scheme for audit persistence",
        description_hi="ऑडिट स्थायित्व के लिए परीक्षण योजना",
        official_url="https://gov.in/schemes/test",
        status=SchemeStatus.ACTIVE,
    )
    db_session.add(scheme)
    await db_session.flush()

    pv = PolicyVersion(
        scheme_id=scheme.id,
        version_code="v1.0.0",
        effective_from=date(2025, 1, 1),
        source_url="https://gov.in/schemes/test-policy",
        source_title="Test Statutory Order 2025",
    )
    db_session.add(pv)
    await db_session.flush()

    citizen = Citizen(
        synthetic_reference=f"CIT-SYN-{uuid.uuid4().hex[:8]}",
        display_name="Test Synthetic Citizen",
    )
    db_session.add(citizen)
    await db_session.flush()

    # 2. Build deterministic evaluation and audit record
    rule = ComparisonNode(
        rule_id="RULE_MIN_EXP",
        field_path="profile.experience_years",
        operator=ComparisonOperator.GTE,
        expected_value=3,
    )
    rule_hash = compute_canonical_rule_hash(rule)
    evaluator = DeterministicEvaluator()
    facts = {"profile": {"experience_years": 5}}
    eval_date = date(2026, 1, 1)

    ctx = EvaluationContext(data=facts, evaluation_date=eval_date)
    eval_res = evaluator.evaluate(rule, ctx)

    provenance = PolicyProvenance(
        scheme_id=scheme.id,
        scheme_code=scheme.scheme_code,
        policy_version_id=pv.id,
        policy_version_code=pv.version_code,
        rule_set_version="1.0.0",
        canonical_rule_hash=rule_hash,
        evaluation_date=eval_date,
        effective_from=pv.effective_from,
        source_title="Statutory Circular 101",
        source_clause="Clause 4",
    )
    trace = build_explainability_trace(eval_res, provenance)
    audit_record = create_audit_evaluation_record(
        citizen_ref=f"cit-syn-{citizen.id.hex[:8]}",
        input_data=facts,
        provenance=provenance,
        explainability_trace=trace,
    )

    # 3. Bridge to SQLAlchemy EvaluationTrace model
    db_model = audit_record.to_db_model(
        citizen_id=citizen.id,
        scheme_id=scheme.id,
        policy_version_id=pv.id,
    )
    db_session.add(db_model)
    await db_session.commit()

    # 4. Query back and verify all fields preserved
    query = select(EvaluationTrace).where(EvaluationTrace.id == db_model.id)
    result = await db_session.execute(query)
    persisted = result.scalar_one()

    assert persisted.citizen_id == citizen.id
    assert persisted.scheme_id == scheme.id
    assert persisted.policy_version_id == pv.id
    assert persisted.evaluation_date == eval_date
    assert persisted.result_state == EligibilityResult.ELIGIBLE
    assert persisted.rule_definition_hash == rule_hash
    assert persisted.trace_schema_version == "1.0.0"
    assert persisted.input_snapshot_json["data"] == facts
    assert persisted.trace_json["root_node"]["truth_value"] == "TRUE"


# ============================================================================
# 8. Input Snapshot Immutability Audit (Section 2: Tests A, B, C, D)
# ============================================================================

def test_input_snapshot_immutability_full_suite():
    """Prove snapshot immutability across all four required test vectors (A, B, C, D)."""
    # Setup initial input data with nested structures
    initial_input = {
        "applicant": {
            "name": "Synthetic Applicant",
            "scores": [10, 20, 30],
            "details": {"tier": 1, "flags": {"active": True}},
        }
    }
    eval_date = date(2026, 1, 1)
    evaluator = DeterministicEvaluator()
    rule = ComparisonNode(
        rule_id="R_TIER",
        field_path="applicant.details.tier",
        operator=ComparisonOperator.EQ,
        expected_value=1,
    )
    eval_res = evaluator.evaluate(rule, EvaluationContext(data=initial_input, evaluation_date=eval_date))
    provenance = make_sample_provenance(compute_canonical_rule_hash(rule))
    trace = build_explainability_trace(eval_res, provenance)

    audit_record = create_audit_evaluation_record(
        citizen_ref="cit-immut-001",
        input_data=initial_input,
        provenance=provenance,
        explainability_trace=trace,
    )

    # TEST A: Mutate original top-level and nested input data
    initial_input["applicant"]["name"] = "MUTATED NAME"
    initial_input["applicant"]["details"]["tier"] = 999
    assert audit_record.input_snapshot.data["applicant"]["name"] == "Synthetic Applicant"
    assert audit_record.input_snapshot.data["applicant"]["details"]["tier"] == 1

    # TEST B: Attempt to mutate audit snapshot data directly
    with pytest.raises(TypeError, match="Cannot mutate immutable audit snapshot data"):
        audit_record.input_snapshot.data["new_key"] = "ILLEGAL"

    with pytest.raises(TypeError, match="Cannot mutate immutable audit snapshot data"):
        audit_record.input_snapshot.data["applicant"]["details"]["tier"] = 999

    # Verify Pydantic frozen model on AuditEvaluationRecord
    with pytest.raises(Exception):
        audit_record.final_result = EligibilityResult.INELIGIBLE  # Frozen instance prevents attribute assignment

    # TEST C: Mutate nested list/dict in the original input data
    initial_input["applicant"]["scores"].append(999)
    assert len(audit_record.input_snapshot.data["applicant"]["scores"]) == 3
    assert 999 not in audit_record.input_snapshot.data["applicant"]["scores"]

    # Attempt to mutate the frozen tuple inside snapshot
    with pytest.raises((AttributeError, TypeError)):
        audit_record.input_snapshot.data["applicant"]["scores"].append(999)

    # TEST D: Serialize the snapshot twice, verify byte-identical deterministic output
    json_bytes_1 = audit_record.input_snapshot.model_dump_json().encode("utf-8")
    json_bytes_2 = audit_record.input_snapshot.model_dump_json().encode("utf-8")
    assert json_bytes_1 == json_bytes_2

    rec_json_1 = audit_record.to_json(indent=2).encode("utf-8")
    rec_json_2 = audit_record.to_json(indent=2).encode("utf-8")
    assert rec_json_1 == rec_json_2


# ============================================================================
# 9. Engine Result Integrity (Section 6)
# ============================================================================

def test_engine_result_integrity_unaltered_by_trace_construction():
    """Verify engine EvaluationResult remains 100% byte-identical before and after trace building."""
    evaluator = DeterministicEvaluator()
    rule = LogicalNode(
        rule_id="RULE_COMPOSITE",
        operator=LogicalOperator.AND,
        children=[
            ComparisonNode(rule_id="R1", field_path="facts.score", operator=ComparisonOperator.GTE, expected_value=50),
            ComparisonNode(rule_id="R2", field_path="facts.active", operator=ComparisonOperator.EQ, expected_value=True),
        ],
    )
    ctx = EvaluationContext(data={"facts": {"score": 75, "active": True}}, evaluation_date=date(2026, 1, 1))
    eval_res = evaluator.evaluate(rule, ctx)

    # Serialize before trace construction
    json_before = eval_res.model_dump_json()

    provenance = make_sample_provenance(compute_canonical_rule_hash(rule))
    _trace = build_explainability_trace(eval_res, provenance)

    # Serialize after trace construction
    json_after = eval_res.model_dump_json()

    assert json_before == json_after
    assert json_before.encode("utf-8") == json_after.encode("utf-8")


# ============================================================================
# 10. Bilingual Fidelity (Section 7)
# ============================================================================

def test_bilingual_explanation_semantic_fidelity_detailed():
    """Verify Hindi explanation conveys identical factual meaning (values, fields, operator, outcome)."""
    evaluator = DeterministicEvaluator()
    rule = ComparisonNode(
        rule_id="R_EXPERIENCE",
        description_en="Minimum work experience in years",
        description_hi="वर्षों में न्यूनतम कार्य अनुभव",
        field_path="applicant.exp_years",
        operator=ComparisonOperator.GTE,
        expected_value=5,
    )

    # FALSE evaluation
    ctx_false = EvaluationContext(data={"applicant": {"exp_years": 3}}, evaluation_date=date(2026, 1, 1))
    res_false = evaluator.evaluate(rule, ctx_false)
    exp_false = generate_rule_explanation(res_false.root_node_result)

    # Both languages must convey the field, operator, actual value 3, and expected value 5
    assert "applicant.exp_years" in exp_false.detail_en
    assert "applicant.exp_years" in exp_false.detail_hi
    assert "GTE" in exp_false.detail_en
    assert "GTE" in exp_false.detail_hi
    assert "3" in exp_false.detail_en
    assert "3" in exp_false.detail_hi
    assert "5" in exp_false.detail_en
    assert "5" in exp_false.detail_hi
    assert "not satisfied" in exp_false.summary_en.lower()
    assert "पूरी नहीं हुई" in exp_false.summary_hi

    # UNKNOWN evaluation (missing field)
    ctx_unk = EvaluationContext(data={"applicant": {}}, evaluation_date=date(2026, 1, 1))
    res_unk = evaluator.evaluate(rule, ctx_unk)
    exp_unk = generate_rule_explanation(res_unk.root_node_result)

    assert "applicant.exp_years" in exp_unk.detail_en
    assert "applicant.exp_years" in exp_unk.detail_hi
    assert "unresolved" in exp_unk.summary_en.lower()
    assert "अनिर्धारित" in exp_unk.summary_hi


# ============================================================================
# 11. Trace Ordering / Multi-Run Determinism (Section 8)
# ============================================================================

def test_deterministic_trace_traversal_multi_run_byte_identical():
    """Verify exact stable pre-order traversal and 10 repeated runs produce byte-identical JSON."""
    evaluator = DeterministicEvaluator()
    r_a = ComparisonNode(rule_id="R_A", field_path="a", operator=ComparisonOperator.EQ, expected_value=1)
    r_b = ComparisonNode(rule_id="R_B", field_path="b", operator=ComparisonOperator.EQ, expected_value=2)
    r_c = ComparisonNode(rule_id="R_C", field_path="c", operator=ComparisonOperator.EQ, expected_value=3)
    r_d = ComparisonNode(rule_id="R_D", field_path="d", operator=ComparisonOperator.EQ, expected_value=4)

    or_node = LogicalNode(rule_id="OR_NODE", operator=LogicalOperator.OR, children=[r_c, r_d])
    root_node = LogicalNode(rule_id="ROOT_AND", operator=LogicalOperator.AND, children=[r_a, r_b, or_node])

    ctx = EvaluationContext(data={"a": 1, "b": 2, "c": 3, "d": 4}, evaluation_date=date(2026, 1, 1))
    provenance = make_sample_provenance(compute_canonical_rule_hash(root_node))

    # Evaluate once and check strict pre-order
    first_res = evaluator.evaluate(root_node, ctx)
    first_trace = build_explainability_trace(first_res, provenance)
    expected_order = ["ROOT_AND", "R_A", "R_B", "OR_NODE", "R_C", "R_D"]
    assert [n.rule_id for n in first_trace.ordered_nodes] == expected_order

    # Run 10 times in a loop and assert complete byte-identical JSON serialization
    reference_json = first_trace.to_json(indent=2)
    for _ in range(10):
        eval_run = evaluator.evaluate(root_node, ctx)
        trace_run = build_explainability_trace(eval_run, provenance)
        assert trace_run.to_json(indent=2) == reference_json
        assert trace_run.to_json(indent=2).encode("utf-8") == reference_json.encode("utf-8")


# ============================================================================
# 12. Family Member Privacy (Section 9)
# ============================================================================

def test_family_member_privacy_no_pii_leakage_detailed():
    """Verify that unreferenced raw sensitive identifiers never leak into trace or explanations."""
    evaluator = DeterministicEvaluator()
    inner = ComparisonNode(
        rule_id="RULE_MIN_AGE",
        field_path="member.age",
        operator=ComparisonOperator.GTE,
        expected_value=18,
    )
    scope = ContextScopeNode(
        rule_id="MEMBER_AGE_SCOPE",
        operator=ContextOperator.EVALUATE_FAMILY_MEMBER,
        collection_path="family.members",
        selector_field="role",
        selector_value="SPOUSE",
        member_alias="member",
        rule=inner,
    )

    sensitive_facts = {
        "family": {
            "members": [
                {
                    "role": "SPOUSE",
                    "age": 25,
                    "dummy_aadhaar_number": "1234-5678-9012",
                    "dummy_bank_account": "987654321098",
                    "dummy_phone": "+91-9988776655",
                    "dummy_full_name": "Sensitive Real Name",
                }
            ]
        }
    }
    eval_res = evaluator.evaluate(scope, EvaluationContext(data=sensitive_facts, evaluation_date=date(2026, 1, 1)))
    provenance = make_sample_provenance(compute_canonical_rule_hash(scope))
    trace = build_explainability_trace(eval_res, provenance)

    serialized_trace = trace.to_json()

    # None of the unreferenced sensitive PII strings must appear anywhere in the trace JSON
    assert "1234-5678-9012" not in serialized_trace
    assert "987654321098" not in serialized_trace
    assert "+91-9988776655" not in serialized_trace
    assert "Sensitive Real Name" not in serialized_trace

    # Explanations do not contain sensitive tokens
    for node in trace.ordered_nodes:
        assert "1234-5678-9012" not in node.explanation_en
        assert "1234-5678-9012" not in node.explanation_hi


# ============================================================================
# 13. Evidence / Eligibility Separation Matrix (Section 10)
# ============================================================================

def test_evidence_eligibility_separation_matrix():
    """Demonstrate that EligibilityResult and EvidenceStatus are completely independent dimensions."""
    # Proof of independence:
    # 1. Statutorily ELIGIBLE with PENDING verification
    # 2. Statutorily ELIGIBLE with VERIFIED verification
    # 3. Statutorily ELIGIBLE with REJECTED verification (procedurally blocked, but statutorily eligible)
    # 4. Statutorily INELIGIBLE with VERIFIED verification (proof verified that applicant does NOT qualify)
    # 5. INSUFFICIENT_INFORMATION with PENDING evidence

    evaluator = DeterministicEvaluator()
    rule = ComparisonNode(rule_id="R1", field_path="profile.score", operator=ComparisonOperator.GTE, expected_value=50)

    # Case A: Asserted score 80 (ELIGIBLE)
    res_eligible = evaluator.evaluate(rule, EvaluationContext(data={"profile": {"score": 80}}, evaluation_date=date(2026, 1, 1)))
    prov = make_sample_provenance(compute_canonical_rule_hash(rule))
    trace_a = build_explainability_trace(res_eligible, prov)

    trace_a.root_node.evidence_reference = "doc-cert-01"
    trace_a.root_node.evidence_status = EvidenceStatus.PENDING.value
    assert trace_a.overall_result == EligibilityResult.ELIGIBLE
    assert trace_a.root_node.evidence_status == "PENDING"

    trace_a.root_node.evidence_status = EvidenceStatus.REJECTED.value
    assert trace_a.overall_result == EligibilityResult.ELIGIBLE  # Eligibility logic does not mutate!
    assert trace_a.root_node.evidence_status == "REJECTED"

    # Case B: Asserted score 30 (INELIGIBLE) with VERIFIED evidence
    res_ineligible = evaluator.evaluate(rule, EvaluationContext(data={"profile": {"score": 30}}, evaluation_date=date(2026, 1, 1)))
    trace_b = build_explainability_trace(res_ineligible, prov)
    trace_b.root_node.evidence_reference = "doc-cert-02"
    trace_b.root_node.evidence_status = EvidenceStatus.VERIFIED.value

    assert trace_b.overall_result == EligibilityResult.INELIGIBLE  # Even though evidence is verified, candidate is ineligible!
    assert trace_b.root_node.evidence_status == "VERIFIED"

    # Type system distinctness: EligibilityResult and EvidenceStatus are different enums
    assert type(EligibilityResult.ELIGIBLE) is not type(EvidenceStatus.VERIFIED)


# ============================================================================
# 14. Audit Record Completeness & Historical Reproducibility (Section 4 & 5)
# ============================================================================

@pytest.mark.asyncio
async def test_persisted_audit_record_completeness(db_session):
    """Verify that every single required field from Section 4 is present in the persisted audit record."""
    scheme = Scheme(
        scheme_code=f"SCHEME_FULL_AUDIT_{uuid.uuid4().hex[:6]}",
        name_en="Complete Audit Test Scheme",
        name_hi="पूर्ण ऑडिट परीक्षण योजना",
        description_en="Verification of 23 required audit attributes",
        description_hi="23 आवश्यक ऑडिट विशेषताओं का सत्यापन",
        official_url="https://gov.in/schemes/audit-full",
        status=SchemeStatus.ACTIVE,
    )
    db_session.add(scheme)
    await db_session.flush()

    pv = PolicyVersion(
        scheme_id=scheme.id,
        version_code="v2025.1",
        effective_from=date(2025, 1, 1),
        effective_to=date(2025, 12, 31),
        source_url="https://gov.in/schemes/gazette-2025.pdf",
        source_title="Statutory Policy Guideline 2025",
        source_document_identifier="GAZ-2025-01",
    )
    db_session.add(pv)
    await db_session.flush()

    citizen = Citizen(
        synthetic_reference=f"CIT-SYN-FULL-{uuid.uuid4().hex[:8]}",
        display_name="Synthetic Audit Applicant",
    )
    db_session.add(citizen)
    await db_session.flush()

    rule = ComparisonNode(
        rule_id="RULE_QUALIFICATION",
        field_path="applicant.level",
        operator=ComparisonOperator.GTE,
        expected_value=2,
    )
    canonical_hash = compute_canonical_rule_hash(rule)
    eval_date = date(2025, 6, 1)
    facts = {"applicant": {"level": 3}}

    evaluator = DeterministicEvaluator()
    eval_res = evaluator.evaluate(rule, EvaluationContext(data=facts, evaluation_date=eval_date))

    provenance = PolicyProvenance(
        scheme_id=scheme.id,
        scheme_code=scheme.scheme_code,
        policy_version_id=pv.id,
        policy_version_code=pv.version_code,
        rule_set_id=uuid.uuid4(),
        rule_set_version="1.2.0",
        canonical_rule_hash=canonical_hash,
        evaluation_date=eval_date,
        effective_from=pv.effective_from,
        effective_to=pv.effective_to,
        source_url=pv.source_url,
        source_title=pv.source_title,
        source_clause="Section 5(b)",
    )
    trace = build_explainability_trace(eval_res, provenance)
    audit_record = create_audit_evaluation_record(
        citizen_ref=citizen.synthetic_reference,
        input_data=facts,
        provenance=provenance,
        explainability_trace=trace,
    )

    db_model = audit_record.to_db_model(
        citizen_id=citizen.id,
        scheme_id=scheme.id,
        policy_version_id=pv.id,
    )
    db_session.add(db_model)
    await db_session.commit()

    # Query back and check all 23 audit items
    query = select(EvaluationTrace).where(EvaluationTrace.id == db_model.id)
    persisted = (await db_session.execute(query)).scalar_one()

    # 1. evaluation identifier
    assert persisted.id == audit_record.evaluation_id
    # 2. citizen synthetic reference
    assert persisted.input_snapshot_json["citizen_ref"] == citizen.synthetic_reference
    # 3. scheme identifier
    assert persisted.scheme_id == scheme.id
    # 4. policy version identifier
    assert persisted.policy_version_id == pv.id
    # 5. policy version code
    assert persisted.trace_json["provenance"]["policy_version_code"] == "v2025.1"
    # 6. evaluation date
    assert persisted.evaluation_date == eval_date
    # 7. effective_from
    assert persisted.trace_json["provenance"]["effective_from"] == "2025-01-01"
    # 8. effective_to
    assert persisted.trace_json["provenance"]["effective_to"] == "2025-12-31"
    # 9. rule-set identifier/version
    assert persisted.trace_json["provenance"]["rule_set_version"] == "1.2.0"
    # 10. canonical rule hash
    assert persisted.rule_definition_hash == canonical_hash
    # 11. source URL
    assert persisted.trace_json["provenance"]["source_url"] == pv.source_url
    # 12. source title/reference
    assert persisted.trace_json["provenance"]["source_title"] == pv.source_title
    # 13. source clause where available
    assert persisted.trace_json["provenance"]["source_clause"] == "Section 5(b)"
    # 14. input snapshot/reference
    assert persisted.input_snapshot_json["snapshot_id"].startswith("snp-")
    # 15. input snapshot hash
    assert len(persisted.input_snapshot_json["snapshot_hash"]) == 64
    # 16. final eligibility result
    assert persisted.result_state == EligibilityResult.ELIGIBLE
    # 17. root truth value
    assert persisted.trace_json["root_truth_value"] == "TRUE"
    # 18. rule trace
    assert len(persisted.trace_json["ordered_nodes"]) >= 1
    # 19. blockers/information gaps
    assert "blockers" in persisted.trace_json
    # 20. trace schema version
    assert persisted.trace_schema_version == TRACE_SCHEMA_VERSION
    # 21. explanation schema version
    assert persisted.trace_json["explanation_schema_version"] == EXPLANATION_SCHEMA_VERSION
    # 22. audit schema version
    assert persisted.trace_json["audit_schema_version"] == AUDIT_SCHEMA_VERSION
    # 23. created timestamp
    assert persisted.created_at is not None


@pytest.mark.asyncio
async def test_historical_reproducibility_against_policy_evolution(db_session):
    """Prove that historical audit records remain strictly immutable when policy evolves."""
    # 1. Scheme under Policy V1
    scheme = Scheme(
        scheme_code=f"SCHEME_HIST_{uuid.uuid4().hex[:6]}",
        name_en="Historical Evolution Scheme",
        name_hi="ऐतिहासिक विकास योजना",
        description_en="Testing reproducibility under policy changes",
        description_hi="नीति परिवर्तनों के तहत पुनरुत्पादकता का परीक्षण",
        official_url="https://gov.in/schemes/historical",
        status=SchemeStatus.ACTIVE,
    )
    db_session.add(scheme)
    await db_session.flush()

    pv1 = PolicyVersion(
        scheme_id=scheme.id,
        version_code="v1.0.0",
        effective_from=date(2024, 1, 1),
        effective_to=date(2024, 12, 31),
        source_url="https://gov.in/schemes/policy-v1.pdf",
        source_title="Statutory Policy 2024 (Threshold 100)",
    )
    db_session.add(pv1)
    await db_session.flush()

    citizen = Citizen(synthetic_reference=f"CIT-HIST-{uuid.uuid4().hex[:8]}")
    db_session.add(citizen)
    await db_session.flush()

    # Rule V1: score >= 100
    rule_v1 = ComparisonNode(rule_id="RULE_SCORE", field_path="score", operator=ComparisonOperator.GTE, expected_value=100)
    hash_v1 = compute_canonical_rule_hash(rule_v1)
    facts_v1 = {"score": 150}
    eval_date_v1 = date(2024, 6, 1)

    evaluator = DeterministicEvaluator()
    res_v1 = evaluator.evaluate(rule_v1, EvaluationContext(data=facts_v1, evaluation_date=eval_date_v1))
    prov_v1 = PolicyProvenance(
        scheme_id=scheme.id,
        scheme_code=scheme.scheme_code,
        policy_version_id=pv1.id,
        policy_version_code=pv1.version_code,
        rule_set_version="1.0.0",
        canonical_rule_hash=hash_v1,
        evaluation_date=eval_date_v1,
        effective_from=pv1.effective_from,
        effective_to=pv1.effective_to,
        source_title=pv1.source_title,
    )
    audit_v1 = create_audit_evaluation_record(
        citizen_ref=citizen.synthetic_reference,
        input_data=facts_v1,
        provenance=prov_v1,
        explainability_trace=build_explainability_trace(res_v1, prov_v1),
    )
    db_trace_v1 = audit_v1.to_db_model(citizen_id=citizen.id, scheme_id=scheme.id, policy_version_id=pv1.id)
    db_session.add(db_trace_v1)
    await db_session.commit()

    saved_trace_id = db_trace_v1.id

    # 2. Scheme evolves: Policy V2 introduced (Threshold raised to 500)
    pv2 = PolicyVersion(
        scheme_id=scheme.id,
        version_code="v2.0.0",
        effective_from=date(2025, 1, 1),
        effective_to=None,
        source_url="https://gov.in/schemes/policy-v2.pdf",
        source_title="Statutory Policy 2025 (Threshold 500)",
    )
    db_session.add(pv2)
    await db_session.commit()

    # 3. Query back the historical V1 record and assert complete invariance
    query = select(EvaluationTrace).where(EvaluationTrace.id == saved_trace_id)
    persisted_historical = (await db_session.execute(query)).scalar_one()

    assert persisted_historical.policy_version_id == pv1.id
    assert persisted_historical.evaluation_date == eval_date_v1
    assert persisted_historical.result_state == EligibilityResult.ELIGIBLE
    assert persisted_historical.rule_definition_hash == hash_v1
    assert persisted_historical.input_snapshot_json["data"] == {"score": 150}
    assert persisted_historical.trace_json["provenance"]["policy_version_code"] == "v1.0.0"
    assert persisted_historical.trace_json["provenance"]["source_title"] == "Statutory Policy 2024 (Threshold 100)"


# ============================================================================
# 15. Schema Version Audit (Section 11)
# ============================================================================

@pytest.mark.asyncio
async def test_all_schema_versions_persisted(db_session):
    """Verify that all 6 required schema versions are stored and verifiable in persisted records."""
    scheme = Scheme(
        scheme_code=f"SCHEME_VERSIONS_{uuid.uuid4().hex[:6]}",
        name_en="Versions Test Scheme",
        name_hi="संस्करण परीक्षण योजना",
        description_en="Checking all schema versions",
        description_hi="सभी स्कीमा संस्करणों की जाँच",
        official_url="https://gov.in/schemes/versions",
        status=SchemeStatus.ACTIVE,
    )
    db_session.add(scheme)
    await db_session.flush()

    pv = PolicyVersion(
        scheme_id=scheme.id,
        version_code="v1.0.0",
        effective_from=date(2025, 1, 1),
        source_url="https://gov.in/schemes/versions-policy",
        source_title="Versions Guideline",
    )
    db_session.add(pv)
    await db_session.flush()

    citizen = Citizen(synthetic_reference=f"CIT-VER-{uuid.uuid4().hex[:8]}")
    db_session.add(citizen)
    await db_session.flush()

    # Rule with a missing field so blocker is emitted
    rule = ComparisonNode(rule_id="R_REQ", field_path="profile.mandatory_doc", operator=ComparisonOperator.EQ, expected_value="YES")
    evaluator = DeterministicEvaluator()
    eval_res = evaluator.evaluate(rule, EvaluationContext(data={"profile": {}}, evaluation_date=date(2026, 1, 1)))

    prov = PolicyProvenance(
        scheme_id=scheme.id,
        scheme_code=scheme.scheme_code,
        policy_version_id=pv.id,
        policy_version_code=pv.version_code,
        rule_set_version="1.0.0",
        canonical_rule_hash=compute_canonical_rule_hash(rule),
        evaluation_date=date(2026, 1, 1),
        effective_from=pv.effective_from,
        source_title="Versions Stat",
    )
    trace = build_explainability_trace(eval_res, prov)
    audit_record = create_audit_evaluation_record(
        citizen_ref=citizen.synthetic_reference,
        input_data={"profile": {}},
        provenance=prov,
        explainability_trace=trace,
    )
    db_trace = audit_record.to_db_model(citizen_id=citizen.id, scheme_id=scheme.id, policy_version_id=pv.id)
    db_session.add(db_trace)
    await db_session.commit()

    query = select(EvaluationTrace).where(EvaluationTrace.id == db_trace.id)
    persisted = (await db_session.execute(query)).scalar_one()

    # 1. TRACE_SCHEMA_VERSION
    assert persisted.trace_schema_version == TRACE_SCHEMA_VERSION
    assert persisted.trace_json["trace_version"] == TRACE_SCHEMA_VERSION

    # 2. EVALUATOR_VERSION
    assert persisted.trace_json["evaluator_version"] == EVALUATOR_VERSION

    # 3. AUDIT_SCHEMA_VERSION
    assert persisted.trace_json["audit_schema_version"] == AUDIT_SCHEMA_VERSION

    # 4. EXPLANATION_SCHEMA_VERSION
    assert persisted.trace_json["explanation_schema_version"] == EXPLANATION_SCHEMA_VERSION

    # 5. PROVENANCE_SCHEMA_VERSION
    assert persisted.trace_json["provenance"]["provenance_schema_version"] == PROVENANCE_SCHEMA_VERSION

    # 6. BLOCKER_SCHEMA_VERSION
    assert len(persisted.trace_json["blockers"]) > 0
    assert persisted.trace_json["blockers"][0]["blocker_schema_version"] == BLOCKER_SCHEMA_VERSION


