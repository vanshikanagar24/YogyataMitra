"""Unit tests for Rule AST node creation, serialization, and structural validation."""

import pytest

from app.engine.ast import (
    AggregationNode,
    AggregationOperator,
    CollectionNode,
    CollectionOperator,
    ComparisonNode,
    ComparisonOperator,
    ContextOperator,
    ContextScopeNode,
    ExistenceNode,
    ExistenceOperator,
    LogicalNode,
    LogicalOperator,
    TemporalNode,
    TemporalOperator,
    validate_ast,
)
from app.engine.errors import (
    ASTValidationError,
    InvalidNodeTypeError,
    InvalidOperandCountError,
    InvalidOperandTypeError,
    UnknownOperatorError,
)


def test_valid_comparison_node_creation_and_serialization():
    node = ComparisonNode(
        rule_id="RULE_LAND_CUTOFF",
        description_en="Land acquisition date must be on or before 2019-02-01",
        description_hi="भूमि अधिग्रहण तिथि 01-02-2019 को या उससे पहले होनी चाहिए",
        source_clause="4.1(a)",
        field_path="land_records.acquisition_date",
        operator=ComparisonOperator.LTE,
        expected_value="2019-02-01",
    )
    data = node.model_dump()
    assert data["node_type"] == "comparison"
    assert data["operator"] == "LTE"
    assert data["field_path"] == "land_records.acquisition_date"
    assert data["expected_value"] == "2019-02-01"

    # Round trip validation
    validated = validate_ast(data)
    assert isinstance(validated, ComparisonNode)
    assert validated.rule_id == "RULE_LAND_CUTOFF"


def test_valid_logical_and_node():
    child1 = ComparisonNode(
        rule_id="R1",
        field_path="citizen.is_farmer",
        operator=ComparisonOperator.EQ,
        expected_value=True,
    )
    child2 = ExistenceNode(
        rule_id="R2",
        field_path="land_records.khata_number",
        operator=ExistenceOperator.EXISTS,
    )
    parent = LogicalNode(
        rule_id="R_PARENT",
        operator=LogicalOperator.AND,
        children=[child1, child2],
    )
    data = parent.model_dump()
    validated = validate_ast(data)
    assert isinstance(validated, LogicalNode)
    assert len(validated.children) == 2


def test_valid_logical_not_node():
    inner = ComparisonNode(
        rule_id="R_TAX",
        field_path="citizen.income_tax_payee",
        operator=ComparisonOperator.EQ,
        expected_value=True,
    )
    node = LogicalNode(
        rule_id="R_NOT_TAX",
        operator=LogicalOperator.NOT,
        child=inner,
    )
    data = node.model_dump()
    validated = validate_ast(data)
    assert isinstance(validated, LogicalNode)
    assert validated.child is not None
    assert validated.child.rule_id == "R_TAX"


def test_valid_temporal_node():
    node = TemporalNode(
        rule_id="R_SSY_AGE",
        operator=TemporalOperator.HAS_NOT_ATTAINED_AGE,
        dob_field="child.dob",
        as_of_field="evaluation_date",
        age_limit=10,
    )
    data = node.model_dump()
    validated = validate_ast(data)
    assert isinstance(validated, TemporalNode)
    assert validated.age_limit == 10


def test_valid_collection_and_aggregation_nodes():
    # Collection COUNT
    c_node = CollectionNode(
        rule_id="R_CHILD_COUNT",
        operator=CollectionOperator.COUNT,
        collection_path="family.children",
        comparison_operator=ComparisonOperator.LTE,
        expected_count=2,
    )
    validated_c = validate_ast(c_node.model_dump())
    assert isinstance(validated_c, CollectionNode)

    # Aggregation SUM
    a_node = AggregationNode(
        rule_id="R_LAND_SUM",
        operator=AggregationOperator.AGGREGATE_SUM,
        collection_path="land_parcels",
        value_field="area_hectares",
        comparison_operator=ComparisonOperator.LTE,
        expected_value=2.0,
    )
    validated_a = validate_ast(a_node.model_dump())
    assert isinstance(validated_a, AggregationNode)


def test_valid_context_scope_node():
    inner = ComparisonNode(
        rule_id="R_PENSION",
        field_path="member.monthly_pension",
        operator=ComparisonOperator.LT,
        expected_value=10000,
    )
    scope_node = ContextScopeNode(
        rule_id="R_FATHER_PENSION",
        operator=ContextOperator.EVALUATE_FAMILY_MEMBER,
        collection_path="family.members",
        selector_field="role",
        selector_value="FATHER",
        member_alias="member",
        rule=inner,
    )
    data = scope_node.model_dump()
    validated = validate_ast(data)
    assert isinstance(validated, ContextScopeNode)
    assert validated.selector_value == "FATHER"


def test_validation_error_missing_node_type():
    with pytest.raises(InvalidNodeTypeError):
        validate_ast({"operator": "EQ", "field_path": "citizen.age", "expected_value": 18})


def test_validation_error_unknown_node_type():
    with pytest.raises(InvalidNodeTypeError):
        validate_ast({"node_type": "quantum_node", "operator": "EQ"})


def test_validation_error_unknown_operator():
    with pytest.raises(UnknownOperatorError):
        validate_ast({
            "node_type": "comparison",
            "operator": "MAGIC_MATCH",
            "field_path": "citizen.age",
            "expected_value": 18,
        })


def test_validation_error_logical_and_empty_children():
    with pytest.raises(InvalidOperandCountError):
        validate_ast({
            "node_type": "logical",
            "operator": "AND",
            "children": [],
        })


def test_validation_error_logical_not_with_children_instead_of_child():
    child = {
        "node_type": "comparison",
        "operator": "EQ",
        "field_path": "test",
        "expected_value": True,
    }
    with pytest.raises((InvalidOperandCountError, InvalidOperandTypeError)):
        validate_ast({
            "node_type": "logical",
            "operator": "NOT",
            "children": [child],
        })


def test_validation_error_comparison_in_non_container():
    with pytest.raises(InvalidOperandTypeError):
        validate_ast({
            "node_type": "comparison",
            "operator": "IN",
            "field_path": "citizen.state",
            "expected_value": "NOT_A_LIST",
        })


def test_validation_error_temporal_invalid_age_limit():
    with pytest.raises(InvalidOperandTypeError):
        validate_ast({
            "node_type": "temporal",
            "operator": "HAS_NOT_ATTAINED_AGE",
            "dob_field": "child.dob",
            "age_limit": -5,
        })


def test_validation_error_collection_for_all_missing_predicate():
    with pytest.raises(InvalidOperandCountError):
        validate_ast({
            "node_type": "collection",
            "operator": "FOR_ALL",
            "collection_path": "parcels",
        })


def test_validation_error_extra_forbidden_field():
    with pytest.raises(ASTValidationError):
        validate_ast({
            "node_type": "comparison",
            "operator": "EQ",
            "field_path": "test",
            "expected_value": 1,
            "malicious_injected_field": "exploit",
        })
