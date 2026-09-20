"""Explicit, structured domain exceptions for Rule AST and Evaluation Engine."""

from typing import Any, Optional


class EngineError(Exception):
    """Base exception for all Rule Engine errors."""
    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


# --- AST Validation Errors ---

class ASTValidationError(EngineError):
    """Raised when an AST node fails syntactic or structural validation."""
    pass


class InvalidNodeTypeError(ASTValidationError):
    """Raised when an AST node specifies an unrecognized node_type."""
    pass


class UnknownOperatorError(ASTValidationError):
    """Raised when an AST node specifies an unrecognized operator."""
    pass


class InvalidOperandCountError(ASTValidationError):
    """Raised when an operator receives fewer or more operands than required."""
    pass


class InvalidOperandTypeError(ASTValidationError):
    """Raised when an operand violates type or schema requirements."""
    pass


# --- Runtime Evaluation Errors ---

class EvaluationError(EngineError):
    """Raised when a runtime error occurs during rule evaluation."""
    pass


class FieldPathResolutionError(EvaluationError):
    """Raised when an illegal or malformed path traversal is attempted."""
    pass


class TypeMismatchError(EvaluationError):
    """Raised when a comparison is attempted on incompatible or un-coercible types."""
    pass


class InvalidTemporalArgumentError(EvaluationError):
    """Raised when date or age calculation receives invalid or unparseable inputs."""
    pass


class InvalidCollectionOperationError(EvaluationError):
    """Raised when a collection operator is applied to a non-collection target."""
    pass
