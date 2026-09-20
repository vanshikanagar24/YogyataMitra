"""Explainable rule execution trace models."""

from datetime import date
import json
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.engine.explainability.blockers import InformationGapBlocker
from app.engine.explainability.constants import (
    AUDIT_SCHEMA_VERSION,
    EVALUATOR_VERSION,
    EXPLANATION_SCHEMA_VERSION,
    TRACE_SCHEMA_VERSION,
)
from app.engine.explainability.provenance import PolicyProvenance
from app.engine.types import RuleTruthValue
from app.models.enums import EligibilityResult


class ExplainableTraceNode(BaseModel):
    """Detailed, explainable trace record for a single evaluated AST rule node."""

    trace_id: str = Field(..., description="Unique deterministic trace identifier e.g. trc-001")
    evaluation_id: Optional[uuid.UUID] = Field(None, description="Parent evaluation run UUID")
    rule_id: Optional[str] = Field(None, description="Statutory rule identifier if assigned")
    node_type: str = Field(..., description="AST node type e.g. logical, comparison, temporal")
    operator: str = Field(..., description="Operator evaluated e.g. AND, EQ, HAS_NOT_ATTAINED_AGE")
    truth_value: RuleTruthValue = Field(..., description="Tri-state truth value (TRUE, FALSE, UNKNOWN)")
    result_state: EligibilityResult = Field(..., description="Equivalent eligibility outcome state")
    actual_value: Any = Field(None, description="Factual resolved value from evaluation context")
    expected_value: Any = Field(None, description="Expected statutory threshold or pattern")
    missing_fields: List[str] = Field(default_factory=list, description="Fields required by this node but absent")
    source_clause: Optional[str] = Field(None, description="Statutory section or guideline clause reference")
    policy_version: Optional[str] = Field(None, description="Policy version code associated with rule")
    family_member_context: Optional[Dict[str, Any]] = Field(
        None, description="Synthetic context identifier for evaluated member (no sensitive PII)"
    )
    explanation_en: str = Field(..., description="English plain-language explanation")
    explanation_hi: str = Field(..., description="Hindi plain-language explanation")
    parent_trace_id: Optional[str] = Field(None, description="Trace ID of parent node in execution tree")
    parent_rule_id: Optional[str] = Field(None, description="Rule ID of parent node")
    evaluation_order: int = Field(..., ge=1, description="Deterministic 1-based traversal order")
    children: List["ExplainableTraceNode"] = Field(
        default_factory=list, description="Child nodes evaluated under this operator"
    )
    evidence_reference: Optional[str] = Field(None, description="Associated evidence document reference if any")
    evidence_status: Optional[str] = Field(None, description="Current status of evidence verification")
    verification_reference: Optional[str] = Field(None, description="Associated verification record reference if any")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional rule or evaluation metadata")

    model_config = ConfigDict(extra="ignore")


class ExplainabilityTrace(BaseModel):
    """Complete, ordered explainability graph and audit trace for an evaluation."""

    trace_version: str = Field(default=TRACE_SCHEMA_VERSION, description="Schema version of trace model")
    evaluator_version: str = Field(default=EVALUATOR_VERSION, description="Version of deterministic engine")
    explanation_schema_version: str = Field(
        default=EXPLANATION_SCHEMA_VERSION, description="Schema version of explanation model"
    )
    audit_schema_version: str = Field(
        default=AUDIT_SCHEMA_VERSION, description="Schema version of audit record"
    )
    evaluation_id: Optional[uuid.UUID] = Field(None, description="Unique evaluation identifier")
    overall_result: EligibilityResult = Field(..., description="Top-level eligibility decision")
    root_truth_value: RuleTruthValue = Field(..., description="Root AST truth value")
    evaluation_date: date = Field(..., description="As-of evaluation reference date")
    provenance: PolicyProvenance = Field(..., description="Policy version and source provenance")
    root_node: ExplainableTraceNode = Field(..., description="Hierarchical root of execution trace tree")
    ordered_nodes: List[ExplainableTraceNode] = Field(
        default_factory=list, description="Flattened nodes in strict deterministic pre-order traversal"
    )
    blockers: List[InformationGapBlocker] = Field(
        default_factory=list, description="Structured blockers and information gaps preventing entitlement"
    )
    satisfied_rules: List[str] = Field(default_factory=list, description="Rule IDs that definitively satisfied (TRUE)")
    failed_rules: List[str] = Field(default_factory=list, description="Rule IDs that definitively failed (FALSE)")
    unknown_rules: List[str] = Field(default_factory=list, description="Rule IDs unresolved due to missing data")
    all_missing_fields: List[str] = Field(
        default_factory=list, description="Deduplicated list of all missing data fields in encounter order"
    )

    model_config = ConfigDict(extra="ignore")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize trace to Python dictionary."""
        return self.model_dump(mode="python")

    def to_json(self, indent: Optional[int] = None) -> str:
        """Serialize trace to canonical, formatted JSON with sorted keys."""
        data = self.model_dump(mode="json")
        return json.dumps(data, indent=indent, sort_keys=True, ensure_ascii=False)


# Rebuild forward references
ExplainableTraceNode.model_rebuild()
