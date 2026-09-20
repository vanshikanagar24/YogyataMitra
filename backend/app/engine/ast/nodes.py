"""Strongly-typed declarative Rule AST nodes."""

from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.engine.ast.operators import (
    AggregationOperator,
    CollectionOperator,
    ComparisonOperator,
    ContextOperator,
    ExistenceOperator,
    LogicalOperator,
    TemporalOperator,
)
from app.engine.errors import (
    InvalidOperandCountError,
    InvalidOperandTypeError,
)


class BaseRuleNode(BaseModel):
    """Base specification for all declarative AST rule nodes."""

    rule_id: Optional[str] = Field(None, description="Stable unique identifier for the rule")
    description_en: Optional[str] = Field(None, description="Human-readable description in English")
    description_hi: Optional[str] = Field(None, description="Human-readable description in Hindi")
    source_clause: Optional[str] = Field(None, description="Statutory reference clause e.g. 4.1(a)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary policy metadata")

    model_config = ConfigDict(extra="forbid", frozen=True)


class LogicalNode(BaseRuleNode):
    """Boolean composition node (AND, OR, NOT)."""

    node_type: Literal["logical"] = "logical"
    operator: LogicalOperator
    children: List["RuleASTNode"] = Field(default_factory=list)
    child: Optional["RuleASTNode"] = None

    @model_validator(mode="after")
    def validate_operands(self) -> "LogicalNode":
        if self.operator in (LogicalOperator.AND, LogicalOperator.OR):
            if not self.children or len(self.children) < 1:
                raise InvalidOperandCountError(
                    f"Logical operator {self.operator.value} requires at least 1 child node."
                )
            if self.child is not None:
                raise InvalidOperandTypeError(
                    f"Logical operator {self.operator.value} must use 'children', not 'child'."
                )
        elif self.operator == LogicalOperator.NOT:
            if self.child is None:
                raise InvalidOperandCountError(
                    "Logical operator NOT requires exactly 1 'child' node."
                )
            if self.children and len(self.children) > 0:
                raise InvalidOperandTypeError(
                    "Logical operator NOT must use 'child', not 'children'."
                )
        return self


class ComparisonNode(BaseRuleNode):
    """Relational comparison node evaluating field values against expected targets."""

    node_type: Literal["comparison"] = "comparison"
    operator: ComparisonOperator
    field_path: str = Field(..., min_length=1)
    expected_value: Any

    @model_validator(mode="after")
    def validate_operands(self) -> "ComparisonNode":
        if self.operator in (ComparisonOperator.IN, ComparisonOperator.NOT_IN):
            if not isinstance(self.expected_value, (list, tuple, set)):
                raise InvalidOperandTypeError(
                    f"Operator {self.operator.value} requires expected_value to be a list, tuple, or set."
                )
        return self


class ExistenceNode(BaseRuleNode):
    """Data presence verification node."""

    node_type: Literal["existence"] = "existence"
    operator: ExistenceOperator
    field_path: str = Field(..., min_length=1)


class TemporalNode(BaseRuleNode):
    """Calendar-aware temporal and age evaluation node."""

    node_type: Literal["temporal"] = "temporal"
    operator: TemporalOperator
    dob_field: str = Field(..., min_length=1, description="Path to date of birth field")
    as_of_field: str = Field("evaluation_date", min_length=1, description="Path to reference date field")
    age_limit: Optional[int] = Field(None, description="Age threshold in years for HAS_NOT_ATTAINED_AGE")
    comparison_operator: Optional[ComparisonOperator] = Field(
        None, description="Relational operator when evaluating AGE_AT"
    )
    expected_years: Optional[int] = Field(
        None, description="Expected years threshold when evaluating AGE_AT"
    )

    @model_validator(mode="after")
    def validate_temporal_params(self) -> "TemporalNode":
        if self.operator == TemporalOperator.HAS_NOT_ATTAINED_AGE:
            if self.age_limit is None or self.age_limit <= 0:
                raise InvalidOperandTypeError(
                    "HAS_NOT_ATTAINED_AGE requires a positive integer 'age_limit'."
                )
        elif self.operator == TemporalOperator.AGE_AT:
            if self.comparison_operator is None or self.expected_years is None:
                raise InvalidOperandTypeError(
                    "AGE_AT requires both 'comparison_operator' and 'expected_years'."
                )
            if self.expected_years < 0:
                raise InvalidOperandTypeError(
                    "AGE_AT requires 'expected_years' to be non-negative."
                )
        return self


class CollectionNode(BaseRuleNode):
    """Collection evaluation node for quantifiers and cardinality checks."""

    node_type: Literal["collection"] = "collection"
    operator: CollectionOperator
    collection_path: str = Field(..., min_length=1)
    item_alias: str = Field("item", min_length=1)
    predicate: Optional["RuleASTNode"] = None
    comparison_operator: Optional[ComparisonOperator] = None
    expected_count: Optional[int] = None

    @model_validator(mode="after")
    def validate_collection_params(self) -> "CollectionNode":
        if self.operator in (CollectionOperator.FOR_ALL, CollectionOperator.EXISTS_IN):
            if self.predicate is None:
                raise InvalidOperandCountError(
                    f"Collection operator {self.operator.value} requires a 'predicate' rule node."
                )
        elif self.operator == CollectionOperator.COUNT:
            if self.comparison_operator is None or self.expected_count is None:
                raise InvalidOperandTypeError(
                    "COUNT operator requires 'comparison_operator' and non-negative 'expected_count'."
                )
            if self.expected_count < 0:
                raise InvalidOperandTypeError("expected_count cannot be negative.")
        return self


class AggregationNode(BaseRuleNode):
    """Collection numeric aggregation node."""

    node_type: Literal["aggregation"] = "aggregation"
    operator: AggregationOperator
    collection_path: str = Field(..., min_length=1)
    value_field: str = Field(..., min_length=1)
    comparison_operator: ComparisonOperator
    expected_value: Union[int, float]


class ContextScopeNode(BaseRuleNode):
    """Evaluates an inner rule scoped to a specific selected entity (e.g. a family member)."""

    node_type: Literal["context"] = "context"
    operator: ContextOperator
    collection_path: str = Field("family.members", min_length=1)
    selector_field: str = Field(..., min_length=1)
    selector_value: Any
    member_alias: str = Field("member", min_length=1)
    rule: "RuleASTNode"


RuleASTNode = Annotated[
    Union[
        LogicalNode,
        ComparisonNode,
        ExistenceNode,
        TemporalNode,
        CollectionNode,
        AggregationNode,
        ContextScopeNode,
    ],
    Field(discriminator="node_type"),
]

# Update forward references
LogicalNode.model_rebuild()
CollectionNode.model_rebuild()
ContextScopeNode.model_rebuild()
