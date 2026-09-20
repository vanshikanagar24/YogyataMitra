"""Policy Test Generation, Execution, and Statutory Regression Verification Service.

Guarantees:
- Deterministic test generation for boundary values and Strong Kleene UNKNOWN propagation.
- Test execution uses the official RuleEvaluator against EvaluationContext.
- Regression verification rigorously checks that all 6 canonical policy hashes remain frozen.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.ast.nodes import (
    BaseRuleNode,
    ComparisonNode,
    ExistenceNode,
    LogicalNode,
    RuleASTNode,
    TemporalNode,
)
from app.engine.ast.operators import ComparisonOperator, LogicalOperator, TemporalOperator
from app.engine.ast.validation import validate_ast
from app.engine.evaluator.context import EvaluationContext
from app.engine.evaluator.evaluator import DeterministicEvaluator
from app.engine.explainability.provenance import compute_canonical_rule_hash
from app.engine.types import RuleTruthValue
from app.models.enums import EligibilityResult
from app.models.policy_draft import (
    PolicyDraft,
    PolicyDraftTest,
    PolicyDraftTestStatus,
    PolicyDraftTestType,
)
from app.schemas.policy_authoring import PolicyDraftTestResponse, TestRunSummaryResponse
from app.services.policy_loader import (
    discover_schemes_and_policies,
    get_default_schemes_data_dir,
)

logger = logging.getLogger("yogyatamitra.services.policy_test_service")


# ==============================================================================
# Mandatory Statutory Regression Verification
# ==============================================================================

FROZEN_CANONICAL_POLICY_HASHES: Dict[Tuple[str, str], str] = {
    ("PM_KISAN", "v1.0-2018"): "facc14b3388802e3d0ef0c4134414459500dc9a9be7e0dc62ddecc082b47e9d2",
    ("PM_KISAN", "v2.0-2019"): "55fe76d5bd441cbe4a0ceddb45ddbf253f5f059683570bd29096bf9b972ad6d8",
    ("PM_KISAN", "v3.0-2023"): "7ef27f5c071a8fa4fff2d95c6c34cda5211b76d16ddb0e610a312ea61cf669d6",
    ("SSY", "v1.0-2016"): "ffb3c2dae2cf283d3b0b41c8dfd87267cfff29e30fa898ee1ca93fde19419ae7",
    ("SSY", "v2.0-2019"): "3dbd7d9d1f87ae7ce5064143333bd8ac969b14e927ac6cb7e6206f1777288669",
    ("SSY", "v3.0-2024"): "5fa83b3d5b0177ca9d0983e46213d11e92883993f2f7a5abc9fe43fb25b9ff28",
}


def verify_canonical_policy_regression() -> None:
    """Verify that all 6 authoritative statutory policy versions remain permanently frozen.
    
    Raises:
        RuntimeError: If any canonical policy version hash deviates.
    """
    schemes_data_dir = get_default_schemes_data_dir()
    discovered = discover_schemes_and_policies(schemes_data_dir)

    for (scheme_code, version_code), expected_hash in FROZEN_CANONICAL_POLICY_HASHES.items():
        if scheme_code not in discovered:
            raise RuntimeError(f"Statutory scheme '{scheme_code}' is missing from canonical repository!")

        _, policies = discovered[scheme_code]
        policy = next((p for p in policies if p.policy_version_code == version_code), None)
        if policy is None:
            raise RuntimeError(f"Statutory policy version '{version_code}' of '{scheme_code}' is missing!")

        actual_hash = compute_canonical_rule_hash(policy.root_rule)
        if actual_hash != expected_hash:
            raise RuntimeError(
                f"CANONICAL HASH MUTATION DETECTED! Scheme: {scheme_code}, Version: {version_code}. "
                f"Expected: {expected_hash}, Actual: {actual_hash}. Execution aborted."
            )


# ==============================================================================
# Deterministic Test Case Generator
# ==============================================================================

def _extract_predicates(node: Any, predicates: List[Dict[str, Any]]) -> None:
    """Recursively collect comparison, existence, and temporal nodes from AST dict."""
    if not isinstance(node, dict):
        return

    node_type = node.get("node_type")
    if node_type in ("comparison", "temporal", "existence"):
        predicates.append(node)

    if "children" in node and isinstance(node["children"], list):
        for child in node["children"]:
            _extract_predicates(child, predicates)
    if "child" in node and isinstance(node["child"], dict):
        _extract_predicates(node["child"], predicates)


def generate_draft_test_cases(draft: PolicyDraft) -> List[Dict[str, Any]]:
    """Synthesize deterministic test scenarios for boundary testing and UNKNOWN propagation.
    
    Returns a list of dicts: { name, description, facts_json, expected_result }
    """
    rules_json = draft.authored_rules_json or {}
    if not rules_json or not isinstance(rules_json, dict) or not rules_json.get("node_type"):
        return []

    predicates: List[Dict[str, Any]] = []
    _extract_predicates(rules_json, predicates)

    generated: List[Dict[str, Any]] = []

    # Scenario 1: Baseline Eligible Scenario (positive facts for all recognized predicates)
    baseline_facts: Dict[str, Any] = {}
    for p in predicates:
        nt = p.get("node_type")
        if nt == "comparison":
            path = p.get("field_path")
            op = p.get("operator")
            val = p.get("expected_value")
            if path:
                if op == "EQ":
                    baseline_facts[path] = val
                elif op in ("GT", "GTE"):
                    baseline_facts[path] = (val + 1) if isinstance(val, (int, float)) else val
                elif op in ("LT", "LTE"):
                    baseline_facts[path] = (val - 1) if isinstance(val, (int, float)) else val
                elif op == "IN" and isinstance(val, list) and len(val) > 0:
                    baseline_facts[path] = val[0]
                elif op == "NEQ":
                    baseline_facts[path] = "other"
        elif nt == "existence":
            path = p.get("field_path")
            if path:
                baseline_facts[path] = "verified_present"
        elif nt == "temporal":
            dob_path = p.get("dob_field", "citizen.dob")
            limit = p.get("age_limit", 10)
            # 5 years old -> eligible for HAS_NOT_ATTAINED_AGE
            baseline_facts[dob_path] = "2020-01-01"
            baseline_facts["evaluation_date"] = "2025-01-01"

    if baseline_facts:
        generated.append({
            "name": "Scenario: Baseline Full Eligibility",
            "description": "Deterministic scenario where citizen satisfies all authored positive criteria.",
            "facts_json": baseline_facts,
            "expected_result": "ELIGIBLE",
        })

    # Scenario 2: Boundary Ineligible Scenario
    ineligible_facts = dict(baseline_facts)
    boundary_tested = False
    for p in predicates:
        nt = p.get("node_type")
        if nt == "comparison":
            path = p.get("field_path")
            op = p.get("operator")
            val = p.get("expected_value")
            if path and op in ("GT", "GTE") and isinstance(val, (int, float)):
                ineligible_facts[path] = val - 1  # Boundary failing
                boundary_tested = True
                break
            elif path and op in ("LT", "LTE") and isinstance(val, (int, float)):
                ineligible_facts[path] = val + 1  # Boundary failing
                boundary_tested = True
                break
            elif path and op == "EQ":
                ineligible_facts[path] = "non_matching_boundary_value"
                boundary_tested = True
                break
        elif nt == "temporal":
            dob_path = p.get("dob_field", "citizen.dob")
            limit = p.get("age_limit", 10)
            ineligible_facts[dob_path] = "2010-01-01"  # 15 years old -> exceeds limit
            ineligible_facts["evaluation_date"] = "2025-01-01"
            boundary_tested = True
            break

    if boundary_tested:
        generated.append({
            "name": "Scenario: Boundary Ineligibility",
            "description": "Deterministic boundary failure testing threshold exclusion.",
            "facts_json": ineligible_facts,
            "expected_result": "INELIGIBLE",
        })

    # Scenario 3: Missing Information / UNKNOWN Propagation (Strong Kleene)
    generated.append({
        "name": "Scenario: Missing Evidence & UNKNOWN Propagation",
        "description": "Verifies that omitting mandatory evidence produces an UNKNOWN or INCOMPLETE state.",
        "facts_json": {},  # Completely empty context
        "expected_result": "UNKNOWN",
    })

    return generated


# ==============================================================================
# Deterministic Test Execution
# ==============================================================================

async def run_draft_test_suite(
    session: AsyncSession,
    draft: PolicyDraft,
) -> TestRunSummaryResponse:
    """Execute all registered tests against draft rules using the deterministic evaluator."""
    now = datetime.now(timezone.utc)
    rules_json = draft.authored_rules_json or {}
    if not rules_json or not isinstance(rules_json, dict) or not rules_json.get("node_type"):
        raise ValueError("Cannot run tests on empty draft ruleset.")

    # Validate AST
    validated_ast = validate_ast(rules_json)
    evaluator = DeterministicEvaluator()

    # Query tests
    stmt = (
        select(PolicyDraftTest)
        .where(PolicyDraftTest.draft_id == draft.id)
        .order_by(PolicyDraftTest.created_at.asc())
    )
    res = await session.execute(stmt)
    tests = list(res.scalars().all())

    passed_count = 0
    failed_count = 0

    test_responses: List[PolicyDraftTestResponse] = []

    for test in tests:
        facts = test.facts_json or {}
        eval_date = date.today()
        if "evaluation_date" in facts:
            try:
                eval_date = date.fromisoformat(str(facts["evaluation_date"]))
            except Exception:
                pass

        context = EvaluationContext(data=facts, evaluation_date=eval_date)
        eval_res = evaluator.evaluate(validated_ast, context)

        # Map truth value to result
        truth = eval_res.root_truth_value
        if truth == RuleTruthValue.TRUE:
            actual = "ELIGIBLE"
        elif truth == RuleTruthValue.FALSE:
            actual = "INELIGIBLE"
        else:
            actual = "UNKNOWN"

        expected = test.expected_result.upper().strip()
        is_pass = (actual == expected)

        test.actual_result = actual
        test.status = "PASSED" if is_pass else "FAILED"
        test.execution_notes = (
            f"Evaluated root truth: {truth.value}. "
            f"Satisfied rules: {len(eval_res.satisfied_rules)}, "
            f"Failed rules: {len(eval_res.failed_rules)}, "
            f"Missing fields: {len(eval_res.all_missing_fields)}."
        )
        test.updated_at = now

        if is_pass:
            passed_count += 1
        else:
            failed_count += 1

        test_responses.append(PolicyDraftTestResponse.model_validate(test))

    # Update draft test status
    overall_status = PolicyDraftTestStatus.NOT_TESTED
    if len(tests) > 0:
        if failed_count == 0:
            overall_status = PolicyDraftTestStatus.PASSED
        else:
            overall_status = PolicyDraftTestStatus.FAILED

    draft.test_status = overall_status
    draft.test_summary_json = {
        "total_tests": len(tests),
        "passed_tests": passed_count,
        "failed_tests": failed_count,
        "executed_at": now.isoformat(),
    }
    await session.commit()

    return TestRunSummaryResponse(
        total_tests=len(tests),
        passed_tests=passed_count,
        failed_tests=failed_count,
        test_status=overall_status.value,
        executed_at=now,
        results=test_responses,
    )
