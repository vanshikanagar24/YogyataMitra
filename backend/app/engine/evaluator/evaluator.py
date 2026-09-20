"""Deterministic, provider-neutral Rule AST Evaluator implementing Kleene tri-state logic."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from app.engine.ast.nodes import (
    AggregationNode,
    BaseRuleNode,
    CollectionNode,
    ComparisonNode,
    ContextScopeNode,
    ExistenceNode,
    LogicalNode,
    RuleASTNode,
    TemporalNode,
)
from app.engine.ast.operators import (
    AggregationOperator,
    CollectionOperator,
    ComparisonOperator,
    ExistenceOperator,
    LogicalOperator,
    TemporalOperator,
)
from app.engine.ast.validation import validate_ast
from app.engine.errors import (
    EvaluationError,
    InvalidCollectionOperationError,
    InvalidTemporalArgumentError,
    TypeMismatchError,
)
from app.engine.evaluator.context import EvaluationContext
from app.engine.evaluator.result import EvaluationResult, NodeEvaluationResult
from app.engine.types import (
    RuleTruthValue,
    kleene_and,
    kleene_not,
    kleene_or,
)
from app.models.enums import EligibilityResult


def _parse_date(val: Any, field_name: str) -> date:
    """Safely parse a date value from date, datetime, or ISO-8601 string."""
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        try:
            return date.fromisoformat(val.strip())
        except ValueError as err:
            raise InvalidTemporalArgumentError(
                f"Field '{field_name}' value '{val}' is not a valid ISO date (YYYY-MM-DD)."
            ) from err
    raise InvalidTemporalArgumentError(
        f"Field '{field_name}' must be a date or ISO date string, got {type(val).__name__}."
    )


def _calculate_age(dob: date, as_of: date) -> int:
    """Calculate exact calendar age in whole years.
    
    Correctly accounts for leap years and anniversary dates.
    """
    if as_of < dob:
        raise InvalidTemporalArgumentError(
            f"Reference date ({as_of}) cannot precede birth date ({dob})."
        )
    years = as_of.year - dob.year
    if (as_of.month, as_of.day) < (dob.month, dob.day):
        years -= 1
    return years


def _compare_values(actual: Any, expected: Any, operator: ComparisonOperator, field_path: str) -> bool:
    """Perform strongly-typed comparison with controlled coercions for dates and decimals."""
    # Strict boolean check: prevent Python's bool-is-subclass-of-int coercion
    if isinstance(actual, bool) != isinstance(expected, bool):
        if operator == ComparisonOperator.EQ:
            return False
        elif operator == ComparisonOperator.NEQ:
            return True
        else:
            raise TypeMismatchError(
                f"Cannot compare boolean with non-boolean {type(expected).__name__} for field '{field_path}'."
            )

    # Datetime to date normalization
    if isinstance(actual, datetime):
        actual = actual.date()
    if isinstance(expected, datetime):
        expected = expected.date()

    # Date coercion from ISO string
    if isinstance(actual, date) and isinstance(expected, str):
        try:
            expected = date.fromisoformat(expected.strip())
        except ValueError:
            pass
    elif isinstance(actual, str) and isinstance(expected, date):
        try:
            actual = date.fromisoformat(actual.strip())
        except ValueError:
            pass

    # Numeric coercion between Decimal and int/float
    if isinstance(actual, Decimal) and isinstance(expected, (int, float)):
        expected = Decimal(str(expected))
    elif isinstance(expected, Decimal) and isinstance(actual, (int, float)):
        actual = Decimal(str(actual))

    try:
        if operator == ComparisonOperator.EQ:
            return bool(actual == expected)
        elif operator == ComparisonOperator.NEQ:
            return bool(actual != expected)
        elif operator == ComparisonOperator.GT:
            return bool(actual > expected)
        elif operator == ComparisonOperator.GTE:
            return bool(actual >= expected)
        elif operator == ComparisonOperator.LT:
            return bool(actual < expected)
        elif operator == ComparisonOperator.LTE:
            return bool(actual <= expected)
        elif operator == ComparisonOperator.IN:
            # Check container
            if isinstance(actual, (date, datetime)) and isinstance(expected, (list, tuple, set)):
                # Match against dates in expected list
                normalized = []
                for item in expected:
                    if isinstance(item, str):
                        try:
                            item = date.fromisoformat(item.strip())
                        except ValueError:
                            pass
                    normalized.append(item)
                return actual in normalized
            return actual in expected
        elif operator == ComparisonOperator.NOT_IN:
            if isinstance(actual, (date, datetime)) and isinstance(expected, (list, tuple, set)):
                normalized = []
                for item in expected:
                    if isinstance(item, str):
                        try:
                            item = date.fromisoformat(item.strip())
                        except ValueError:
                            pass
                    normalized.append(item)
                return actual not in normalized
            return actual not in expected
        else:
            raise EvaluationError(f"Unsupported comparison operator: {operator}")
    except TypeError as err:
        raise TypeMismatchError(
            f"Cannot compare field '{field_path}' value '{actual}' ({type(actual).__name__}) "
            f"against expected '{expected}' ({type(expected).__name__}) with operator {operator.value}."
        ) from err


class DeterministicEvaluator:
    """Stateless, deterministic, provider-neutral Rule AST Evaluator.
    
    Implements Kleene strong tri-state logic (TRUE, FALSE, UNKNOWN) across
    all AST node types. Missing or null facts evaluate to UNKNOWN and are
    tracked explicitly for explainability.
    """

    def evaluate(
        self,
        ast_data: Union[Dict[str, Any], RuleASTNode],
        context: EvaluationContext,
    ) -> EvaluationResult:
        """Evaluate a validated or raw Rule AST against an EvaluationContext."""
        root_node = validate_ast(ast_data)
        root_result = self._evaluate_node(root_node, context)

        # Collect missing fields preserving order
        all_missing: List[str] = []
        seen_missing: Set[str] = set()

        failed_rules: List[str] = []
        satisfied_rules: List[str] = []
        unknown_rules: List[str] = []

        def _traverse(res: NodeEvaluationResult) -> None:
            for field in res.missing_fields:
                if field not in seen_missing:
                    seen_missing.add(field)
                    all_missing.append(field)

            if res.rule_id:
                if res.truth_value == RuleTruthValue.FALSE:
                    if res.rule_id not in failed_rules:
                        failed_rules.append(res.rule_id)
                elif res.truth_value == RuleTruthValue.TRUE:
                    if res.rule_id not in satisfied_rules:
                        satisfied_rules.append(res.rule_id)
                elif res.truth_value == RuleTruthValue.UNKNOWN:
                    if res.rule_id not in unknown_rules:
                        unknown_rules.append(res.rule_id)

            for child in res.children:
                _traverse(child)

        _traverse(root_result)

        # Map root truth value to 5-state EligibilityResult
        if root_result.truth_value == RuleTruthValue.TRUE:
            overall = EligibilityResult.ELIGIBLE
        elif root_result.truth_value == RuleTruthValue.FALSE:
            overall = EligibilityResult.INELIGIBLE
        else:
            overall = EligibilityResult.INSUFFICIENT_INFORMATION

        return EvaluationResult(
            overall_result=overall,
            root_truth_value=root_result.truth_value,
            evaluation_date=context.evaluation_date,
            root_node_result=root_result,
            all_missing_fields=all_missing,
            failed_rules=failed_rules,
            satisfied_rules=satisfied_rules,
            unknown_rules=unknown_rules,
            metadata=dict(context.policy_metadata),
        )

    def _evaluate_node(self, node: RuleASTNode, context: EvaluationContext) -> NodeEvaluationResult:
        """Route node evaluation to specialized visitor methods based on node_type."""
        if isinstance(node, LogicalNode):
            return self._eval_logical(node, context)
        elif isinstance(node, ComparisonNode):
            return self._eval_comparison(node, context)
        elif isinstance(node, ExistenceNode):
            return self._eval_existence(node, context)
        elif isinstance(node, TemporalNode):
            return self._eval_temporal(node, context)
        elif isinstance(node, CollectionNode):
            return self._eval_collection(node, context)
        elif isinstance(node, AggregationNode):
            return self._eval_aggregation(node, context)
        elif isinstance(node, ContextScopeNode):
            return self._eval_context_scope(node, context)
        else:
            raise EvaluationError(f"Unsupported AST node type: {type(node).__name__}")

    def _eval_logical(self, node: LogicalNode, context: EvaluationContext) -> NodeEvaluationResult:
        """Evaluate logical conjunction (AND), disjunction (OR), or negation (NOT)."""
        if node.operator == LogicalOperator.NOT:
            assert node.child is not None
            child_result = self._evaluate_node(node.child, context)
            truth_val = kleene_not(child_result.truth_value)
            missing = list(child_result.missing_fields)

            if truth_val == RuleTruthValue.TRUE:
                reason_en = "Condition satisfied (negated condition is false)"
                reason_hi = "शर्त पूरी हुई (उल्टी शर्त असत्य है)"
            elif truth_val == RuleTruthValue.FALSE:
                reason_en = "Condition failed (negated condition is true)"
                reason_hi = "शर्त पूरी नहीं हुई (उल्टी शर्त सत्य है)"
            else:
                reason_en = "Condition unknown due to insufficient information in negated condition"
                reason_hi = "अपर्याप्त जानकारी के कारण शर्त का निर्धारण नहीं हो सका"

            return NodeEvaluationResult(
                node_type=node.node_type,
                operator=node.operator.value,
                truth_value=truth_val,
                rule_id=node.rule_id,
                description_en=node.description_en,
                description_hi=node.description_hi,
                source_clause=node.source_clause,
                missing_fields=missing,
                children=[child_result],
                reason_en=reason_en,
                reason_hi=reason_hi,
                metadata=dict(node.metadata),
            )

        # AND / OR evaluation
        child_results: List[NodeEvaluationResult] = [
            self._evaluate_node(child, context) for child in node.children
        ]

        # Deduplicate missing fields from children
        missing_fields: List[str] = []
        for c in child_results:
            for f in c.missing_fields:
                if f not in missing_fields:
                    missing_fields.append(f)

        if node.operator == LogicalOperator.AND:
            truth_val = kleene_and(c.truth_value for c in child_results)
            if truth_val == RuleTruthValue.TRUE:
                reason_en = "All required conditions are satisfied"
                reason_hi = "सभी आवश्यक शर्तें पूरी हो गई हैं"
            elif truth_val == RuleTruthValue.FALSE:
                failed_count = sum(1 for c in child_results if c.truth_value == RuleTruthValue.FALSE)
                reason_en = f"Conjunction failed: {failed_count} condition(s) failed"
                reason_hi = f"शर्त संयोजन विफल: {failed_count} शर्त(एं) पूरी नहीं हुईं"
            else:
                reason_en = "Cannot confirm conjunction: required information is missing"
                reason_hi = "संयोजन की पुष्टि नहीं हो सकती: आवश्यक जानकारी अनुपलब्ध है"

        elif node.operator == LogicalOperator.OR:
            truth_val = kleene_or(c.truth_value for c in child_results)
            if truth_val == RuleTruthValue.TRUE:
                reason_en = "At least one qualifying alternative condition is satisfied"
                reason_hi = "कम से कम एक अर्हक वैकल्पिक शर्त पूरी हुई"
            elif truth_val == RuleTruthValue.FALSE:
                reason_en = "None of the qualifying alternative conditions are met"
                reason_hi = "कोई भी अर्हक वैकल्पिक शर्त पूरी नहीं हुई"
            else:
                reason_en = "Insufficient information to confirm any alternative condition"
                reason_hi = "किसी भी वैकल्पिक शर्त की पुष्टि के लिए अपर्याप्त जानकारी"
        else:
            raise EvaluationError(f"Unexpected logical operator: {node.operator}")

        return NodeEvaluationResult(
            node_type=node.node_type,
            operator=node.operator.value,
            truth_value=truth_val,
            rule_id=node.rule_id,
            description_en=node.description_en,
            description_hi=node.description_hi,
            source_clause=node.source_clause,
            missing_fields=missing_fields,
            children=child_results,
            reason_en=reason_en,
            reason_hi=reason_hi,
            metadata=dict(node.metadata),
        )

    def _eval_comparison(self, node: ComparisonNode, context: EvaluationContext) -> NodeEvaluationResult:
        """Evaluate comparison operator against resolved context field."""
        actual_val, exists = context.resolve_path(node.field_path)

        if not exists or actual_val is None:
            return NodeEvaluationResult(
                node_type=node.node_type,
                operator=node.operator.value,
                truth_value=RuleTruthValue.UNKNOWN,
                rule_id=node.rule_id,
                description_en=node.description_en,
                description_hi=node.description_hi,
                source_clause=node.source_clause,
                field_path=node.field_path,
                actual_value=None,
                expected_value=node.expected_value,
                missing_fields=[node.field_path],
                reason_en=f"Field '{node.field_path}' is missing or not provided",
                reason_hi=f"फ़ील्ड '{node.field_path}' अनुपलब्ध है या प्रदान नहीं किया गया है",
                metadata=dict(node.metadata),
            )

        cmp_ok = _compare_values(actual_val, node.expected_value, node.operator, node.field_path)
        truth_val = RuleTruthValue.TRUE if cmp_ok else RuleTruthValue.FALSE

        if truth_val == RuleTruthValue.TRUE:
            reason_en = f"Field '{node.field_path}' ({actual_val}) satisfies {node.operator.value} {node.expected_value}"
            reason_hi = f"फ़ील्ड '{node.field_path}' ({actual_val}) शर्त {node.operator.value} {node.expected_value} को पूरा करता है"
        else:
            reason_en = f"Field '{node.field_path}' ({actual_val}) does not satisfy {node.operator.value} {node.expected_value}"
            reason_hi = f"फ़ील्ड '{node.field_path}' ({actual_val}) शर्त {node.operator.value} {node.expected_value} को पूरा नहीं करता"

        return NodeEvaluationResult(
            node_type=node.node_type,
            operator=node.operator.value,
            truth_value=truth_val,
            rule_id=node.rule_id,
            description_en=node.description_en,
            description_hi=node.description_hi,
            source_clause=node.source_clause,
            field_path=node.field_path,
            actual_value=actual_val,
            expected_value=node.expected_value,
            missing_fields=[],
            reason_en=reason_en,
            reason_hi=reason_hi,
            metadata=dict(node.metadata),
        )

    def _eval_existence(self, node: ExistenceNode, context: EvaluationContext) -> NodeEvaluationResult:
        """Evaluate structural presence or absence of a data field in context facts."""
        actual_val, exists = context.resolve_path(node.field_path)

        if node.operator == ExistenceOperator.EXISTS:
            truth_val = RuleTruthValue.TRUE if exists else RuleTruthValue.FALSE
            missing = [] if exists else [node.field_path]
            if exists:
                reason_en = f"Field '{node.field_path}' exists in context facts"
                reason_hi = f"फ़ील्ड '{node.field_path}' संदर्भ तथ्यों में मौजूद है"
            else:
                reason_en = f"Field '{node.field_path}' is missing from context facts"
                reason_hi = f"फ़ील्ड '{node.field_path}' संदर्भ तथ्यों में अनुपलब्ध है"
        elif node.operator == ExistenceOperator.IS_MISSING:
            truth_val = RuleTruthValue.TRUE if not exists else RuleTruthValue.FALSE
            missing = []
            if not exists:
                reason_en = f"Field '{node.field_path}' is absent as required"
                reason_hi = f"फ़ील्ड '{node.field_path}' आवश्यकतानुसार अनुपस्थित है"
            else:
                reason_en = f"Field '{node.field_path}' is present in context facts"
                reason_hi = f"फ़ील्ड '{node.field_path}' संदर्भ तथ्यों में उपस्थित है"
        else:
            raise EvaluationError(f"Unexpected existence operator: {node.operator}")

        return NodeEvaluationResult(
            node_type=node.node_type,
            operator=node.operator.value,
            truth_value=truth_val,
            rule_id=node.rule_id,
            description_en=node.description_en,
            description_hi=node.description_hi,
            source_clause=node.source_clause,
            field_path=node.field_path,
            actual_value=actual_val if exists else None,
            missing_fields=missing,
            reason_en=reason_en,
            reason_hi=reason_hi,
            metadata=dict(node.metadata),
        )

    def _eval_temporal(self, node: TemporalNode, context: EvaluationContext) -> NodeEvaluationResult:
        """Evaluate temporal age boundaries with exact calendar arithmetic."""
        dob_val, dob_exists = context.resolve_path(node.dob_field)
        as_of_val, as_of_exists = context.resolve_path(node.as_of_field)

        if not dob_exists or dob_val is None:
            return NodeEvaluationResult(
                node_type=node.node_type,
                operator=node.operator.value,
                truth_value=RuleTruthValue.UNKNOWN,
                rule_id=node.rule_id,
                description_en=node.description_en,
                description_hi=node.description_hi,
                source_clause=node.source_clause,
                field_path=node.dob_field,
                missing_fields=[node.dob_field],
                reason_en=f"Date of birth field '{node.dob_field}' is missing",
                reason_hi=f"जन्म तिथि फ़ील्ड '{node.dob_field}' अनुपलब्ध है",
                metadata=dict(node.metadata),
            )

        if node.as_of_field and node.as_of_field != "evaluation_date":
            if not as_of_exists or as_of_val is None:
                return NodeEvaluationResult(
                    node_type=node.node_type,
                    operator=node.operator.value,
                    truth_value=RuleTruthValue.UNKNOWN,
                    rule_id=node.rule_id,
                    description_en=node.description_en,
                    description_hi=node.description_hi,
                    source_clause=node.source_clause,
                    field_path=node.as_of_field,
                    missing_fields=[node.as_of_field],
                    reason_en=f"As-of date field '{node.as_of_field}' is missing",
                    reason_hi=f"संदर्भ तिथि फ़ील्ड '{node.as_of_field}' अनुपलब्ध है",
                    metadata=dict(node.metadata),
                )
            as_of = _parse_date(as_of_val, node.as_of_field)
        else:
            as_of = context.evaluation_date

        dob = _parse_date(dob_val, node.dob_field)

        age = _calculate_age(dob, as_of)

        if node.operator == TemporalOperator.HAS_NOT_ATTAINED_AGE:
            assert node.age_limit is not None
            # On 10th birthday, age == 10, so child HAS attained age 10.
            # "HAS NOT ATTAINED 10" is True iff age < 10.
            has_not_attained = (age < node.age_limit)
            truth_val = RuleTruthValue.TRUE if has_not_attained else RuleTruthValue.FALSE
            expected_desc = f"< {node.age_limit} years"

            if truth_val == RuleTruthValue.TRUE:
                reason_en = f"Age as of {as_of.isoformat()} is {age} years, which has not attained {node.age_limit} years"
                reason_hi = f"{as_of.isoformat()} को आयु {age} वर्ष है, जो {node.age_limit} वर्ष की सीमा तक नहीं पहुँची है"
            else:
                reason_en = f"Age as of {as_of.isoformat()} is {age} years, which has reached or exceeded {node.age_limit} years"
                reason_hi = f"{as_of.isoformat()} को आयु {age} वर्ष है, जो {node.age_limit} वर्ष या उससे अधिक हो चुकी है"

        elif node.operator == TemporalOperator.AGE_AT:
            assert node.comparison_operator is not None
            assert node.expected_years is not None
            cmp_ok = _compare_values(age, node.expected_years, node.comparison_operator, "age")
            truth_val = RuleTruthValue.TRUE if cmp_ok else RuleTruthValue.FALSE
            expected_desc = f"{node.comparison_operator.value} {node.expected_years} years"

            if truth_val == RuleTruthValue.TRUE:
                reason_en = f"Age as of {as_of.isoformat()} is {age} years, satisfying {expected_desc}"
                reason_hi = f"{as_of.isoformat()} को आयु {age} वर्ष है, जो {expected_desc} की शर्त पूरी करती है"
            else:
                reason_en = f"Age as of {as_of.isoformat()} is {age} years, failing {expected_desc}"
                reason_hi = f"{as_of.isoformat()} को आयु {age} वर्ष है, जो {expected_desc} की शर्त पूरी नहीं करती"
        else:
            raise EvaluationError(f"Unexpected temporal operator: {node.operator}")

        return NodeEvaluationResult(
            node_type=node.node_type,
            operator=node.operator.value,
            truth_value=truth_val,
            rule_id=node.rule_id,
            description_en=node.description_en,
            description_hi=node.description_hi,
            source_clause=node.source_clause,
            field_path=node.dob_field,
            actual_value={"dob": dob.isoformat(), "as_of": as_of.isoformat(), "age_years": age},
            expected_value=expected_desc,
            missing_fields=[],
            reason_en=reason_en,
            reason_hi=reason_hi,
            metadata=dict(node.metadata),
        )

    def _eval_collection(self, node: CollectionNode, context: EvaluationContext) -> NodeEvaluationResult:
        """Evaluate collection quantifier or cardinality constraint."""
        items, exists = context.resolve_path(node.collection_path)

        if not exists or items is None:
            return NodeEvaluationResult(
                node_type=node.node_type,
                operator=node.operator.value,
                truth_value=RuleTruthValue.UNKNOWN,
                rule_id=node.rule_id,
                description_en=node.description_en,
                description_hi=node.description_hi,
                source_clause=node.source_clause,
                field_path=node.collection_path,
                missing_fields=[node.collection_path],
                reason_en=f"Collection at '{node.collection_path}' is missing or not provided",
                reason_hi=f"'{node.collection_path}' पर संग्रह अनुपलब्ध है या प्रदान नहीं किया गया है",
                metadata=dict(node.metadata),
            )

        if not isinstance(items, (list, tuple)):
            raise InvalidCollectionOperationError(
                f"Field at '{node.collection_path}' must be a list, got {type(items).__name__}."
            )

        if node.operator == CollectionOperator.COUNT:
            assert node.comparison_operator is not None
            assert node.expected_count is not None

            if node.predicate is not None:
                item_results: List[NodeEvaluationResult] = []
                matching_count = 0
                for item in items:
                    scoped_ctx = context.with_scope({node.item_alias: item})
                    res = self._evaluate_node(node.predicate, scoped_ctx)
                    item_results.append(res)
                    if res.truth_value == RuleTruthValue.TRUE:
                        matching_count += 1
                actual_count = matching_count
                children = item_results
            else:
                actual_count = len(items)
                children = []

            cmp_ok = _compare_values(
                actual_count, node.expected_count, node.comparison_operator, "collection_count"
            )
            truth_val = RuleTruthValue.TRUE if cmp_ok else RuleTruthValue.FALSE

            if truth_val == RuleTruthValue.TRUE:
                reason_en = f"Collection count ({actual_count}) satisfies {node.comparison_operator.value} {node.expected_count}"
                reason_hi = f"संग्रह संख्या ({actual_count}) शर्त {node.comparison_operator.value} {node.expected_count} को पूरा करती है"
            else:
                reason_en = f"Collection count ({actual_count}) does not satisfy {node.comparison_operator.value} {node.expected_count}"
                reason_hi = f"संग्रह संख्या ({actual_count}) शर्त {node.comparison_operator.value} {node.expected_count} को पूरा नहीं करती"

            return NodeEvaluationResult(
                node_type=node.node_type,
                operator=node.operator.value,
                truth_value=truth_val,
                rule_id=node.rule_id,
                description_en=node.description_en,
                description_hi=node.description_hi,
                source_clause=node.source_clause,
                field_path=node.collection_path,
                actual_value=actual_count,
                expected_value=f"{node.comparison_operator.value} {node.expected_count}",
                missing_fields=[],
                children=children,
                reason_en=reason_en,
                reason_hi=reason_hi,
                metadata=dict(node.metadata),
            )

        # FOR_ALL / EXISTS_IN
        assert node.predicate is not None

        if len(items) == 0:
            if node.operator == CollectionOperator.FOR_ALL:
                truth_val = RuleTruthValue.TRUE
                reason_en = "Empty collection vacuously satisfies universal condition (FOR_ALL)"
                reason_hi = "खाली संग्रह सर्वव्यापी शर्त (FOR_ALL) को स्वतः पूरा करता है"
            else:
                truth_val = RuleTruthValue.FALSE
                reason_en = "Empty collection cannot satisfy existential condition (EXISTS_IN)"
                reason_hi = "खाली संग्रह अस्तित्व शर्त (EXISTS_IN) को पूरा नहीं कर सकता"
            return NodeEvaluationResult(
                node_type=node.node_type,
                operator=node.operator.value,
                truth_value=truth_val,
                rule_id=node.rule_id,
                description_en=node.description_en,
                description_hi=node.description_hi,
                source_clause=node.source_clause,
                field_path=node.collection_path,
                actual_value=0,
                children=[],
                reason_en=reason_en,
                reason_hi=reason_hi,
                metadata=dict(node.metadata),
            )

        item_results = []
        for item in items:
            scoped_ctx = context.with_scope({node.item_alias: item})
            item_results.append(self._evaluate_node(node.predicate, scoped_ctx))

        missing_fields = []
        for r in item_results:
            for f in r.missing_fields:
                if f not in missing_fields:
                    missing_fields.append(f)

        if node.operator == CollectionOperator.FOR_ALL:
            truth_val = kleene_and(r.truth_value for r in item_results)
            if truth_val == RuleTruthValue.TRUE:
                reason_en = "All items in collection satisfy predicate condition"
                reason_hi = "संग्रह के सभी मद शर्त को पूरा करते हैं"
            elif truth_val == RuleTruthValue.FALSE:
                reason_en = "One or more items in collection failed predicate condition"
                reason_hi = "संग्रह के एक या अधिक मद शर्त को पूरा नहीं करते"
            else:
                reason_en = "Cannot verify all items due to missing information"
                reason_hi = "अपर्याप्त जानकारी के कारण सभी मदों का सत्यापन नहीं हो सका"
        else:  # EXISTS_IN
            truth_val = kleene_or(r.truth_value for r in item_results)
            if truth_val == RuleTruthValue.TRUE:
                reason_en = "At least one item in collection satisfies predicate condition"
                reason_hi = "संग्रह का कम से कम एक मद शर्त को पूरा करता है"
            elif truth_val == RuleTruthValue.FALSE:
                reason_en = "No item in collection satisfies predicate condition"
                reason_hi = "संग्रह का कोई भी मद शर्त को पूरा नहीं करता"
            else:
                reason_en = "Cannot verify existence due to missing information"
                reason_hi = "अपर्याप्त जानकारी के कारण अस्तित्व का सत्यापन नहीं हो सका"

        return NodeEvaluationResult(
            node_type=node.node_type,
            operator=node.operator.value,
            truth_value=truth_val,
            rule_id=node.rule_id,
            description_en=node.description_en,
            description_hi=node.description_hi,
            source_clause=node.source_clause,
            field_path=node.collection_path,
            actual_value=len(items),
            missing_fields=missing_fields,
            children=item_results,
            reason_en=reason_en,
            reason_hi=reason_hi,
            metadata=dict(node.metadata),
        )

    def _eval_aggregation(self, node: AggregationNode, context: EvaluationContext) -> NodeEvaluationResult:
        """Evaluate numeric aggregation over collection items."""
        items, exists = context.resolve_path(node.collection_path)

        if not exists or items is None:
            return NodeEvaluationResult(
                node_type=node.node_type,
                operator=node.operator.value,
                truth_value=RuleTruthValue.UNKNOWN,
                rule_id=node.rule_id,
                description_en=node.description_en,
                description_hi=node.description_hi,
                source_clause=node.source_clause,
                field_path=node.collection_path,
                missing_fields=[node.collection_path],
                reason_en=f"Collection at '{node.collection_path}' is missing",
                reason_hi=f"'{node.collection_path}' पर संग्रह अनुपलब्ध है",
                metadata=dict(node.metadata),
            )

        if not isinstance(items, (list, tuple)):
            raise InvalidCollectionOperationError(
                f"Field at '{node.collection_path}' must be a list, got {type(items).__name__}."
            )

        # Aggregate sum
        total = Decimal("0")
        missing_fields: List[str] = []

        for idx, item in enumerate(items):
            item_val = None
            if isinstance(item, dict):
                item_val = item.get(node.value_field)
            elif hasattr(item, node.value_field):
                item_val = getattr(item, node.value_field)

            if item_val is None:
                missing_fields.append(f"{node.collection_path}[{idx}].{node.value_field}")
            else:
                try:
                    total += Decimal(str(item_val))
                except Exception as err:
                    raise EvaluationError(
                        f"Item value '{item_val}' at index {idx} cannot be converted to Decimal."
                    ) from err

        if missing_fields:
            return NodeEvaluationResult(
                node_type=node.node_type,
                operator=node.operator.value,
                truth_value=RuleTruthValue.UNKNOWN,
                rule_id=node.rule_id,
                description_en=node.description_en,
                description_hi=node.description_hi,
                source_clause=node.source_clause,
                field_path=node.collection_path,
                missing_fields=missing_fields,
                reason_en=f"Aggregation incomplete due to missing field(s): {', '.join(missing_fields)}",
                reason_hi=f"अनुपलब्ध फ़ील्ड के कारण संचयी गणना अधूरी है: {', '.join(missing_fields)}",
                metadata=dict(node.metadata),
            )

        cmp_ok = _compare_values(
            float(total), float(node.expected_value), node.comparison_operator, node.value_field
        )
        truth_val = RuleTruthValue.TRUE if cmp_ok else RuleTruthValue.FALSE

        if truth_val == RuleTruthValue.TRUE:
            reason_en = f"Aggregated sum ({total}) satisfies {node.comparison_operator.value} {node.expected_value}"
            reason_hi = f"कुल योग ({total}) शर्त {node.comparison_operator.value} {node.expected_value} को पूरा करता है"
        else:
            reason_en = f"Aggregated sum ({total}) does not satisfy {node.comparison_operator.value} {node.expected_value}"
            reason_hi = f"कुल योग ({total}) शर्त {node.comparison_operator.value} {node.expected_value} को पूरा नहीं करता"

        return NodeEvaluationResult(
            node_type=node.node_type,
            operator=node.operator.value,
            truth_value=truth_val,
            rule_id=node.rule_id,
            description_en=node.description_en,
            description_hi=node.description_hi,
            source_clause=node.source_clause,
            field_path=f"{node.collection_path}.{node.value_field}",
            actual_value=float(total),
            expected_value=f"{node.comparison_operator.value} {node.expected_value}",
            missing_fields=[],
            reason_en=reason_en,
            reason_hi=reason_hi,
            metadata=dict(node.metadata),
        )

    def _eval_context_scope(self, node: ContextScopeNode, context: EvaluationContext) -> NodeEvaluationResult:
        """Evaluate inner rule scoped to a specific entity within a collection."""
        items, exists = context.resolve_path(node.collection_path)

        if not exists or items is None:
            return NodeEvaluationResult(
                node_type=node.node_type,
                operator=node.operator.value,
                truth_value=RuleTruthValue.UNKNOWN,
                rule_id=node.rule_id,
                description_en=node.description_en,
                description_hi=node.description_hi,
                source_clause=node.source_clause,
                field_path=node.collection_path,
                missing_fields=[node.collection_path],
                reason_en=f"Collection '{node.collection_path}' is missing or not provided",
                reason_hi=f"संग्रह '{node.collection_path}' अनुपलब्ध है या प्रदान नहीं किया गया है",
                metadata=dict(node.metadata),
            )

        if not isinstance(items, (list, tuple)):
            raise InvalidCollectionOperationError(
                f"Field '{node.collection_path}' must be a collection, got {type(items).__name__}."
            )

        # Locate matching member/item
        matched_item = None
        for item in items:
            val = item.get(node.selector_field) if isinstance(item, dict) else getattr(item, node.selector_field, None)
            if val == node.selector_value:
                matched_item = item
                break

        if matched_item is None:
            missing_tag = f"{node.collection_path}[{node.selector_field}={node.selector_value}]"
            return NodeEvaluationResult(
                node_type=node.node_type,
                operator=node.operator.value,
                truth_value=RuleTruthValue.UNKNOWN,
                rule_id=node.rule_id,
                description_en=node.description_en,
                description_hi=node.description_hi,
                source_clause=node.source_clause,
                field_path=missing_tag,
                missing_fields=[missing_tag],
                reason_en=f"Entity with {node.selector_field}='{node.selector_value}' not found in '{node.collection_path}'",
                reason_hi=f"'{node.collection_path}' में {node.selector_field}='{node.selector_value}' वाला सदस्य नहीं मिला",
                metadata=dict(node.metadata),
            )

        scoped_ctx = context.with_scope({node.member_alias: matched_item})
        inner_result = self._evaluate_node(node.rule, scoped_ctx)

        return NodeEvaluationResult(
            node_type=node.node_type,
            operator=node.operator.value,
            truth_value=inner_result.truth_value,
            rule_id=node.rule_id or inner_result.rule_id,
            description_en=node.description_en or inner_result.description_en,
            description_hi=node.description_hi or inner_result.description_hi,
            source_clause=node.source_clause or inner_result.source_clause,
            field_path=node.collection_path,
            actual_value=node.selector_value,
            missing_fields=list(inner_result.missing_fields),
            children=[inner_result],
            reason_en=inner_result.reason_en,
            reason_hi=inner_result.reason_hi,
            metadata=dict(node.metadata),
        )
