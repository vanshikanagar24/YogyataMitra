"""AST validation utilities for declarative policy rules."""

from typing import Any, Dict, Union

from pydantic import TypeAdapter, ValidationError

from app.engine.ast.nodes import BaseRuleNode, RuleASTNode
from app.engine.errors import (
    ASTValidationError,
    InvalidNodeTypeError,
    InvalidOperandCountError,
    InvalidOperandTypeError,
    UnknownOperatorError,
)

_adapter = TypeAdapter(RuleASTNode)


def validate_ast(ast_data: Union[Dict[str, Any], RuleASTNode]) -> RuleASTNode:
    """Validate and deserialize a raw dictionary or AST model into a verified RuleASTNode.
    
    Raises:
        ASTValidationError or specific subclasses upon syntactic or structural failure.
    """
    if isinstance(ast_data, BaseRuleNode):
        return ast_data  # type: ignore[return-value]

    if not isinstance(ast_data, dict):
        raise ASTValidationError(
            f"Expected dictionary representing AST node, received {type(ast_data).__name__}"
        )

    node_type = ast_data.get("node_type")
    if not node_type:
        raise InvalidNodeTypeError("AST node is missing required 'node_type' discriminator.")

    try:
        return _adapter.validate_python(ast_data)
    except ValidationError as err:
        # Check specific error types from validators
        first_err = err.errors()[0] if err.errors() else {}
        err_msg = first_err.get("msg", str(err))

        if "node_type" in str(first_err.get("loc", [])) or "discriminator" in err_msg or "Input tag" in err_msg:
            raise InvalidNodeTypeError(f"Unrecognized node_type: {node_type}") from err
        if "operator" in str(first_err.get("loc", [])) or "Input should be" in err_msg:
            operator_val = ast_data.get("operator", "<unknown>")
            raise UnknownOperatorError(f"Unrecognized operator: {operator_val}") from err
        if "requires at least" in err_msg or "requires exactly" in err_msg or "requires a 'predicate'" in err_msg:
            raise InvalidOperandCountError(err_msg) from err
        if "requires" in err_msg:
            raise InvalidOperandTypeError(err_msg) from err

        raise ASTValidationError(f"Invalid AST structure: {err_msg}", details={"raw_errors": err.errors()}) from err
