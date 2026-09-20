"""Builder for transforming deterministic EvaluationResult into an explainable, ordered trace."""

from typing import Any, Dict, List, Optional
import uuid

from app.engine.evaluator.result import EvaluationResult, NodeEvaluationResult
from app.engine.explainability.blockers import BlockerCategory, InformationGapBlocker
from app.engine.explainability.constants import EVALUATOR_VERSION, TRACE_SCHEMA_VERSION
from app.engine.explainability.explanation import generate_rule_explanation
from app.engine.explainability.provenance import PolicyProvenance
from app.engine.explainability.trace import ExplainabilityTrace, ExplainableTraceNode
from app.engine.types import RuleTruthValue
from app.models.enums import EligibilityResult


def _truth_to_result_state(tv: RuleTruthValue) -> EligibilityResult:
    """Map tri-state rule truth value to canonical EligibilityResult."""
    if tv == RuleTruthValue.TRUE:
        return EligibilityResult.ELIGIBLE
    elif tv == RuleTruthValue.FALSE:
        return EligibilityResult.INELIGIBLE
    else:
        return EligibilityResult.INSUFFICIENT_INFORMATION


class TraceBuilder:
    """Transforms raw engine results into an explainable, ordered, audit-ready trace."""

    def __init__(self) -> None:
        self._current_order = 0
        self._ordered_nodes: List[ExplainableTraceNode] = []
        self._blockers: List[InformationGapBlocker] = []
        self._seen_blocker_codes: set[str] = set()

    def build(
        self,
        eval_result: EvaluationResult,
        provenance: PolicyProvenance,
        evaluation_id: Optional[uuid.UUID] = None,
    ) -> ExplainabilityTrace:
        """Construct a complete ExplainabilityTrace with strict deterministic pre-order traversal."""
        self._current_order = 0
        self._ordered_nodes = []
        self._blockers = []
        self._seen_blocker_codes = set()

        root_trace_node = self._transform_node(
            node_res=eval_result.root_node_result,
            provenance=provenance,
            evaluation_id=evaluation_id,
            parent_trace_id=None,
            parent_rule_id=None,
            inherited_context=None,
        )

        # Fallback blocker if evaluation is unresolved but no field-specific blocker was created
        if eval_result.overall_result == EligibilityResult.INSUFFICIENT_INFORMATION and not self._blockers:
            generic_code = "BLOCKER_INSUFFICIENT_INFORMATION"
            self._blockers.append(
                InformationGapBlocker(
                    code=generic_code,
                    category=BlockerCategory.INSUFFICIENT_INFORMATION,
                    field_path=None,
                    rule_id=eval_result.root_node_result.rule_id,
                    message_en="Evaluation could not reach a definitive entitlement decision due to missing data.",
                    message_hi="अनुपलब्ध डेटा के कारण पात्रता का अंतिम निर्णय नहीं लिया जा सका।",
                )
            )

        return ExplainabilityTrace(
            trace_version=TRACE_SCHEMA_VERSION,
            evaluator_version=EVALUATOR_VERSION,
            evaluation_id=evaluation_id,
            overall_result=eval_result.overall_result,
            root_truth_value=eval_result.root_truth_value,
            evaluation_date=eval_result.evaluation_date,
            provenance=provenance,
            root_node=root_trace_node,
            ordered_nodes=list(self._ordered_nodes),
            blockers=list(self._blockers),
            satisfied_rules=list(eval_result.satisfied_rules),
            failed_rules=list(eval_result.failed_rules),
            unknown_rules=list(eval_result.unknown_rules),
            all_missing_fields=list(eval_result.all_missing_fields),
        )

    def _transform_node(
        self,
        node_res: NodeEvaluationResult,
        provenance: PolicyProvenance,
        evaluation_id: Optional[uuid.UUID],
        parent_trace_id: Optional[str],
        parent_rule_id: Optional[str],
        inherited_context: Optional[Dict[str, Any]],
    ) -> ExplainableTraceNode:
        """Process a single node and its children recursively in pre-order depth-first traversal."""
        self._current_order += 1
        order = self._current_order
        trace_id = f"trc-{order:04d}"

        # Context scope handling (preserving family-member context without sensitive PII)
        node_context = dict(inherited_context or {})
        if node_res.node_type == "context":
            node_context["scope_type"] = "entity_context"
            node_context["field_path"] = node_res.field_path
            node_context["selector_value"] = str(node_res.actual_value)

        # Generate faithful bilingual explanation
        explanation = generate_rule_explanation(node_res)

        # Track structured blockers for missing information
        for missing_field in node_res.missing_fields:
            clean_code = f"BLOCKER_MISSING_{missing_field.upper().replace('.', '_').replace('[', '_').replace(']', '').replace('=', '_')}"
            if clean_code not in self._seen_blocker_codes:
                self._seen_blocker_codes.add(clean_code)
                self._blockers.append(
                    InformationGapBlocker(
                        code=clean_code,
                        category=BlockerCategory.MISSING_FIELD,
                        field_path=missing_field,
                        rule_id=node_res.rule_id,
                        message_en=f"Required information '{missing_field}' is missing.",
                        message_hi=f"आवश्यक जानकारी '{missing_field}' अनुपलब्ध है।",
                    )
                )

        trace_node = ExplainableTraceNode(
            trace_id=trace_id,
            evaluation_id=evaluation_id,
            rule_id=node_res.rule_id,
            node_type=node_res.node_type,
            operator=node_res.operator,
            truth_value=node_res.truth_value,
            result_state=_truth_to_result_state(node_res.truth_value),
            actual_value=node_res.actual_value,
            expected_value=node_res.expected_value,
            missing_fields=list(node_res.missing_fields),
            source_clause=node_res.source_clause or provenance.source_clause,
            policy_version=provenance.policy_version_code,
            family_member_context=node_context if node_context else None,
            explanation_en=explanation.detail_en,
            explanation_hi=explanation.detail_hi,
            parent_trace_id=parent_trace_id,
            parent_rule_id=parent_rule_id,
            evaluation_order=order,
            children=[],
            metadata={
                **dict(node_res.metadata),
                **({"field_path": node_res.field_path} if node_res.field_path else {}),
            },
        )

        # Add to flat ordered list immediately (pre-order depth-first)
        self._ordered_nodes.append(trace_node)

        # Recursively process children
        for child in node_res.children:
            child_trace = self._transform_node(
                node_res=child,
                provenance=provenance,
                evaluation_id=evaluation_id,
                parent_trace_id=trace_id,
                parent_rule_id=node_res.rule_id,
                inherited_context=node_context if node_context else None,
            )
            trace_node.children.append(child_trace)

        return trace_node


def build_explainability_trace(
    eval_result: EvaluationResult,
    provenance: PolicyProvenance,
    evaluation_id: Optional[uuid.UUID] = None,
) -> ExplainabilityTrace:
    """Convenience functional factory for generating an ExplainabilityTrace."""
    return TraceBuilder().build(
        eval_result=eval_result,
        provenance=provenance,
        evaluation_id=evaluation_id,
    )
