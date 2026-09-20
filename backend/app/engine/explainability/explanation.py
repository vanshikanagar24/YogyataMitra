"""Bilingual rule explanation generator and representation."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.engine.evaluator.result import NodeEvaluationResult
from app.engine.explainability.constants import EXPLANATION_SCHEMA_VERSION
from app.engine.types import RuleTruthValue


class RuleExplanation(BaseModel):
    """Structured bilingual plain-language explanation of a single rule evaluation outcome."""

    explanation_schema_version: str = Field(
        default=EXPLANATION_SCHEMA_VERSION, description="Schema version of rule explanation"
    )
    rule_id: Optional[str] = Field(None, description="Identifier of the rule evaluated")
    truth_value: RuleTruthValue = Field(..., description="Tri-state truth value (TRUE, FALSE, UNKNOWN)")
    summary_en: str = Field(..., description="Concise English outcome summary")
    summary_hi: str = Field(..., description="Concise Hindi outcome summary")
    detail_en: str = Field(..., description="Detailed English explanation including factual values")
    detail_hi: str = Field(..., description="Detailed Hindi explanation including factual values")
    source_clause: Optional[str] = Field(None, description="Statutory reference clause")

    model_config = ConfigDict(extra="ignore", frozen=True)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize explanation to Python dictionary."""
        return self.model_dump(mode="python")


def generate_rule_explanation(node_res: NodeEvaluationResult) -> RuleExplanation:
    """Generate structured bilingual explanations from a NodeEvaluationResult.
    
    Invariants:
    - Never modifies the node truth value or actual/expected values.
    - Never invents facts or citizen attributes.
    - Accurately renders outcomes for TRUE, FALSE, and UNKNOWN.
    """
    tv = node_res.truth_value
    node_type = node_res.node_type
    op = node_res.operator
    rule_desc_en = node_res.description_en or node_res.rule_id or f"{node_type} rule"
    rule_desc_hi = node_res.description_hi or node_res.rule_id or f"{node_type} नियम"

    if tv == RuleTruthValue.TRUE:
        summary_en = f"Condition satisfied: {rule_desc_en}."
        summary_hi = f"शर्त पूरी हुई: {rule_desc_hi}।"
    elif tv == RuleTruthValue.FALSE:
        summary_en = f"Condition not satisfied: {rule_desc_en}."
        summary_hi = f"शर्त पूरी नहीं हुई: {rule_desc_hi}।"
    else:  # UNKNOWN
        summary_en = f"Condition unresolved: {rule_desc_en}."
        summary_hi = f"शर्त अनिर्धारित: {rule_desc_hi}।"

    # Use node-generated reasons if present, otherwise construct standardized detail
    if node_res.reason_en and node_res.reason_hi:
        detail_en = node_res.reason_en
        detail_hi = node_res.reason_hi
    else:
        if tv == RuleTruthValue.TRUE:
            detail_en = f"Evaluated operator '{op}' successfully on '{node_res.field_path or 'composite'}'. Found: {node_res.actual_value}."
            detail_hi = f"फ़ील्ड '{node_res.field_path or 'संयोजित'}' पर ऑपरेटर '{op}' सफलतापूर्वक पूरा हुआ। प्राप्त मान: {node_res.actual_value}।"
        elif tv == RuleTruthValue.FALSE:
            detail_en = f"Failed condition for '{node_res.field_path or 'composite'}' using operator '{op}'. Found: {node_res.actual_value}, Expected: {node_res.expected_value}."
            detail_hi = f"फ़ील्ड '{node_res.field_path or 'संयोजित'}' पर ऑपरेटर '{op}' की शर्त पूरी नहीं हुई। प्राप्त मान: {node_res.actual_value}, अपेक्षित: {node_res.expected_value}।"
        else:
            missing_str = ", ".join(node_res.missing_fields) if node_res.missing_fields else "unresolved context"
            detail_en = f"Cannot determine condition because required information is missing or unresolved: {missing_str}."
            detail_hi = f"शर्त का निर्धारण नहीं हो सका क्योंकि आवश्यक जानकारी अनुपलब्ध या अनिर्धारित है: {missing_str}।"

    return RuleExplanation(
        rule_id=node_res.rule_id,
        truth_value=tv,
        summary_en=summary_en,
        summary_hi=summary_hi,
        detail_en=detail_en,
        detail_hi=detail_hi,
        source_clause=node_res.source_clause,
    )
