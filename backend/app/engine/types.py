"""Core type definitions and multi-valued logic semantics for the Rule Engine."""

from enum import Enum
from typing import Iterable

from app.models.enums import EligibilityResult


class RuleTruthValue(str, Enum):
    """Tri-state truth values under Kleene strong logic of indeterminacy.
    
    Distinguishes definitively true conditions, definitively false conditions,
    and unknown/insufficient information conditions.
    """
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"

    @property
    def is_true(self) -> bool:
        return self == RuleTruthValue.TRUE

    @property
    def is_false(self) -> bool:
        return self == RuleTruthValue.FALSE

    @property
    def is_unknown(self) -> bool:
        return self == RuleTruthValue.UNKNOWN


def kleene_and(operands: Iterable[RuleTruthValue]) -> RuleTruthValue:
    """Evaluate logical conjunction under Kleene strong tri-state logic.
    
    Truth Table:
      - If ANY operand is FALSE -> FALSE (short-circuit / definitive failure)
      - If ALL operands are TRUE -> TRUE
      - Otherwise (mix of TRUE and UNKNOWN, or all UNKNOWN) -> UNKNOWN
    """
    has_unknown = False
    for val in operands:
        if val == RuleTruthValue.FALSE:
            return RuleTruthValue.FALSE
        if val == RuleTruthValue.UNKNOWN:
            has_unknown = True
    return RuleTruthValue.UNKNOWN if has_unknown else RuleTruthValue.TRUE


def kleene_or(operands: Iterable[RuleTruthValue]) -> RuleTruthValue:
    """Evaluate logical disjunction under Kleene strong tri-state logic.
    
    Truth Table:
      - If ANY operand is TRUE -> TRUE (short-circuit / definitive satisfaction)
      - If ALL operands are FALSE -> FALSE
      - Otherwise (mix of FALSE and UNKNOWN, or all UNKNOWN) -> UNKNOWN
    """
    has_unknown = False
    for val in operands:
        if val == RuleTruthValue.TRUE:
            return RuleTruthValue.TRUE
        if val == RuleTruthValue.UNKNOWN:
            has_unknown = True
    return RuleTruthValue.UNKNOWN if has_unknown else RuleTruthValue.FALSE


def kleene_not(operand: RuleTruthValue) -> RuleTruthValue:
    """Evaluate logical negation under Kleene strong tri-state logic.
    
    Truth Table:
      - TRUE -> FALSE
      - FALSE -> TRUE
      - UNKNOWN -> UNKNOWN
    """
    if operand == RuleTruthValue.TRUE:
        return RuleTruthValue.FALSE
    if operand == RuleTruthValue.FALSE:
        return RuleTruthValue.TRUE
    return RuleTruthValue.UNKNOWN
