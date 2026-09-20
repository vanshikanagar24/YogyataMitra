"""Evaluation result data structures for deterministic Rule AST evaluation."""

from datetime import date
import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.engine.types import RuleTruthValue
from app.models.enums import EligibilityResult


class NodeEvaluationResult(BaseModel):
    """Detailed audit trace for the evaluation of a single AST rule node."""

    node_type: str = Field(..., description="AST node type e.g. logical, comparison, temporal")
    operator: str = Field(..., description="Operator evaluated e.g. AND, EQ, HAS_NOT_ATTAINED_AGE")
    truth_value: RuleTruthValue = Field(..., description="Tri-state evaluation outcome")
    rule_id: Optional[str] = Field(None, description="Identifier of the rule if present")
    description_en: Optional[str] = Field(None, description="English description")
    description_hi: Optional[str] = Field(None, description="Hindi description")
    source_clause: Optional[str] = Field(None, description="Statutory reference clause")
    field_path: Optional[str] = Field(None, description="Field path evaluated")
    actual_value: Any = Field(None, description="Resolved actual value from context")
    expected_value: Any = Field(None, description="Expected value specified in AST")
    missing_fields: List[str] = Field(default_factory=list, description="Fields required but missing")
    children: List["NodeEvaluationResult"] = Field(
        default_factory=list, description="Evaluation results for child nodes"
    )
    reason_en: Optional[str] = Field(None, description="English explanation of outcome")
    reason_hi: Optional[str] = Field(None, description="Hindi explanation of outcome")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional rule metadata")

    model_config = ConfigDict(extra="ignore")


class EvaluationResult(BaseModel):
    """Complete, immutable evaluation result and explanation trace for a ruleset."""

    overall_result: EligibilityResult = Field(
        ..., description="Final 5-state eligibility decision"
    )
    root_truth_value: RuleTruthValue = Field(
        ..., description="Root AST tri-state outcome"
    )
    evaluation_date: date = Field(
        ..., description="Reference date against which policy was evaluated"
    )
    root_node_result: NodeEvaluationResult = Field(
        ..., description="Root node execution trace"
    )
    all_missing_fields: List[str] = Field(
        default_factory=list,
        description="Deduplicated list of all missing data fields across rules",
    )
    failed_rules: List[str] = Field(
        default_factory=list,
        description="Rule IDs that definitively failed (evaluated to FALSE)",
    )
    satisfied_rules: List[str] = Field(
        default_factory=list,
        description="Rule IDs that definitively passed (evaluated to TRUE)",
    )
    unknown_rules: List[str] = Field(
        default_factory=list,
        description="Rule IDs that could not be determined due to missing data",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Evaluation context or policy metadata"
    )

    model_config = ConfigDict(extra="ignore")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize evaluation result to Python dictionary."""
        return self.model_dump(mode="python")

    def to_json(self, indent: Optional[int] = None) -> str:
        """Serialize evaluation result to canonical, formatted JSON string with sorted keys."""
        data = self.model_dump(mode="json")
        return json.dumps(data, indent=indent, sort_keys=True, ensure_ascii=False)


# Update forward references for recursive model
NodeEvaluationResult.model_rebuild()
