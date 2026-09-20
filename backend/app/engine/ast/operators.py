"""Operator definitions for declarative Rule AST nodes."""

from enum import Enum


class LogicalOperator(str, Enum):
    """Boolean composition operators."""
    AND = "AND"
    OR = "OR"
    NOT = "NOT"


class ComparisonOperator(str, Enum):
    """Relational and set membership comparison operators."""
    EQ = "EQ"
    NEQ = "NEQ"
    GT = "GT"
    GTE = "GTE"
    LT = "LT"
    LTE = "LTE"
    IN = "IN"
    NOT_IN = "NOT_IN"


class ExistenceOperator(str, Enum):
    """Data presence and absence operators."""
    EXISTS = "EXISTS"
    IS_MISSING = "IS_MISSING"


class CollectionOperator(str, Enum):
    """Quantifier and collection-level operators."""
    COUNT = "COUNT"
    FOR_ALL = "FOR_ALL"
    EXISTS_IN = "EXISTS_IN"


class TemporalOperator(str, Enum):
    """Calendar-aware temporal and age boundary operators."""
    AGE_AT = "AGE_AT"
    HAS_NOT_ATTAINED_AGE = "HAS_NOT_ATTAINED_AGE"


class AggregationOperator(str, Enum):
    """Numeric aggregation operators over collections."""
    AGGREGATE_SUM = "AGGREGATE_SUM"


class ContextOperator(str, Enum):
    """Sub-context and scoped entity evaluation operators."""
    EVALUATE_FAMILY_MEMBER = "EVALUATE_FAMILY_MEMBER"


class ASTNodeType(str, Enum):
    """Structural node types in the Rule AST."""
    LOGICAL = "logical"
    COMPARISON = "comparison"
    EXISTENCE = "existence"
    COLLECTION = "collection"
    TEMPORAL = "temporal"
    AGGREGATION = "aggregation"
    CONTEXT = "context"
