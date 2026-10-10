"""Generic Policy-Driven Form Architecture Schemas (Phase G).

Defines strongly-typed, schema-agnostic metadata representations for:
- Generic form fields and data types (TEXT, NUMBER, INTEGER, DECIMAL, DATE, BOOLEAN, SELECT, RADIO, MULTI_SELECT, ADDRESS, EVIDENCE_REFERENCE)
- Bilingual prompts, guidance, and validation error messages (English + Hindi)
- Policy-driven form sections and display grouping
- Declarative field conditions (conditional visibility without code execution)
- Declarative cross-field validation rules
- Documentary evidence associations and constraints
- Version-bound policy form metadata
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Union
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FormFieldType(str, Enum):
    """Supported generic input field types for policy-driven forms."""

    TEXT = "text"
    NUMBER = "number"
    INTEGER = "integer"
    DECIMAL = "decimal"
    DATE = "date"
    BOOLEAN = "boolean"
    SELECT = "select"
    RADIO = "radio"
    MULTI_SELECT = "multi_select"
    ADDRESS = "address"
    FILE_REFERENCE = "file_reference"
    EVIDENCE_REFERENCE = "evidence_reference"

    @classmethod
    def _missing_(cls, value: object) -> Optional["FormFieldType"]:
        """Support case-insensitive lookup."""
        if isinstance(value, str):
            for member in cls:
                if member.value.lower() == value.lower():
                    return member
        return None


class ConditionOperator(str, Enum):
    """Declarative conditional operators for field visibility evaluation."""

    EQUALS = "EQUALS"
    NOT_EQUALS = "NOT_EQUALS"
    IN = "IN"
    NOT_IN = "NOT_IN"
    GREATER_THAN = "GREATER_THAN"
    LESS_THAN = "LESS_THAN"
    GREATER_THAN_OR_EQUAL = "GREATER_THAN_OR_EQUAL"
    LESS_THAN_OR_EQUAL = "LESS_THAN_OR_EQUAL"
    IS_EMPTY = "IS_EMPTY"
    IS_NOT_EMPTY = "IS_NOT_EMPTY"


class FieldCondition(BaseModel):
    """Declarative condition for displaying or requiring a form field.
    
    Safe evaluation: evaluates purely against currently entered fact declarations.
    Zero eval(), zero exec(), zero arbitrary code execution.
    """

    field_key: str = Field(..., description="Controlling field key e.g. 'land.transferred_after_cutoff'")
    operator: ConditionOperator = Field(..., description="Comparison operator")
    value: Optional[Any] = Field(None, description="Expected value or list of values to match")

    model_config = ConfigDict(extra="forbid")

    def evaluate(self, facts: Dict[str, Any]) -> bool:
        """Deterministically evaluate this condition against a dictionary of facts."""
        actual_val = facts.get(self.field_key)

        # Handle nested or flat fact lookup
        if actual_val is None and "." in self.field_key:
            parts = self.field_key.split(".", 1)
            if parts[0] in facts and isinstance(facts[parts[0]], dict):
                actual_val = facts[parts[0]].get(parts[1])

        op = self.operator
        if op == ConditionOperator.EQUALS:
            return actual_val == self.value
        elif op == ConditionOperator.NOT_EQUALS:
            return actual_val != self.value
        elif op == ConditionOperator.IN:
            if isinstance(self.value, (list, set, tuple)):
                return actual_val in self.value
            return False
        elif op == ConditionOperator.NOT_IN:
            if isinstance(self.value, (list, set, tuple)):
                return actual_val not in self.value
            return True
        elif op == ConditionOperator.IS_EMPTY:
            return actual_val is None or actual_val == "" or actual_val == []
        elif op == ConditionOperator.IS_NOT_EMPTY:
            return actual_val is not None and actual_val != "" and actual_val != []
        elif actual_val is None or self.value is None:
            return False
        elif op == ConditionOperator.GREATER_THAN:
            try:
                return float(actual_val) > float(self.value)
            except (ValueError, TypeError):
                return False
        elif op == ConditionOperator.LESS_THAN:
            try:
                return float(actual_val) < float(self.value)
            except (ValueError, TypeError):
                return False
        elif op == ConditionOperator.GREATER_THAN_OR_EQUAL:
            try:
                return float(actual_val) >= float(self.value)
            except (ValueError, TypeError):
                return False
        elif op == ConditionOperator.LESS_THAN_OR_EQUAL:
            try:
                return float(actual_val) <= float(self.value)
            except (ValueError, TypeError):
                return False
        return False


class FieldOption(BaseModel):
    """Option for select, radio, or multi_select fields with full bilingual support."""

    value: str = Field(..., description="Canonical stored value")
    label_en: str = Field(..., description="English option label")
    label_hi: str = Field(..., description="Hindi option label")
    label: Optional[str] = Field(None, description="Combined or fallback label for backward-compatibility")

    model_config = ConfigDict(extra="forbid")

    @field_validator("label", mode="before")
    @classmethod
    def populate_default_label(cls, v: Any, info: Any) -> Optional[str]:
        if v:
            return v
        data = info.data
        if "label_en" in data and "label_hi" in data:
            return f"{data['label_en']} / {data['label_hi']}"
        return None


class FormSectionDefinition(BaseModel):
    """Logical grouping section for policy-driven application fields."""

    section_key: str = Field(..., min_length=1, max_length=64, description="Unique section key e.g. 'land_details'")
    title_en: str = Field(..., min_length=1, max_length=255, description="English section title")
    title_hi: str = Field(..., min_length=1, max_length=255, description="Hindi section title")
    description_en: Optional[str] = Field(None, description="English explanatory guidance for section")
    description_hi: Optional[str] = Field(None, description="Hindi explanatory guidance for section")
    display_order: int = Field(0, description="Sort order of the section in the form")

    model_config = ConfigDict(extra="forbid")


class FormFieldDefinition(BaseModel):
    """Reusable, generic metadata representation for a policy-driven form field."""

    field_key: str = Field(..., description="Canonical dot-notated fact key e.g. 'land.total_land_area_hectares'")
    claim_type: str = Field(..., description="Target claim type admitted into citizen claims")
    field_type: str = Field(..., description="Generic field type string (e.g. 'boolean', 'number', 'date', 'select')")
    required: bool = Field(True, description="Whether this field is mandatory when applicable")
    label_en: str = Field(..., min_length=1, description="English field label")
    label_hi: str = Field(..., min_length=1, description="Hindi field label")
    help_text_en: Optional[str] = Field(None, description="English help text")
    help_text_hi: Optional[str] = Field(None, description="Hindi help text")
    validation_message_en: Optional[str] = Field(None, description="Custom English validation error message")
    validation_message_hi: Optional[str] = Field(None, description="Custom Hindi validation error message")
    section_key: str = Field("general", description="Associated FormSectionDefinition key")
    display_order: int = Field(0, description="Ordering within section")
    options: Optional[List[Dict[str, Any]]] = Field(None, description="Allowed choices for select/radio fields")
    default_value: Optional[Any] = Field(None, description="Default or placeholder value")
    min_value: Optional[float] = Field(None, description="Minimum numeric constraint")
    max_value: Optional[float] = Field(None, description="Maximum numeric constraint")
    min_date: Optional[str] = Field(None, description="Earliest allowable date (ISO format YYYY-MM-DD)")
    max_date: Optional[str] = Field(None, description="Latest allowable date (ISO format YYYY-MM-DD)")
    step: Optional[float] = Field(None, description="Numeric step interval (e.g. 0.01 for decimals)")
    associated_evidence_type: Optional[str] = Field(
        None, description="Statutory evidence category corroborating this field"
    )
    condition: Optional[FieldCondition] = Field(
        None, description="Declarative condition governing visibility/applicability"
    )
    is_active: bool = Field(True, description="Whether this field is active in current policy version")

    model_config = ConfigDict(extra="forbid")


class FormEvidenceDefinition(BaseModel):
    """Documentary evidence requirement specification for a policy-driven form."""

    evidence_type: str = Field(..., min_length=1, max_length=64, description="Statutory evidence code e.g. 'LAND_RECORD'")
    label_en: str = Field(..., min_length=1, description="English document name")
    label_hi: str = Field(..., min_length=1, description="Hindi document name")
    description_en: str = Field(..., min_length=1, description="English purpose and accepted documentation")
    description_hi: str = Field(..., min_length=1, description="Hindi purpose and accepted documentation")
    mandatory: bool = Field(True, description="Whether this evidence is strictly required for evaluation")
    allowed_extensions: List[str] = Field(
        default_factory=lambda: [".pdf", ".jpg", ".jpeg", ".png"],
        description="Allowed file MIME extensions",
    )
    max_size_mb: int = Field(5, description="Maximum file upload size in MB")
    associated_field_keys: List[str] = Field(
        default_factory=list, description="Field keys corroborated by this evidence"
    )

    model_config = ConfigDict(extra="forbid")


class CrossFieldRule(BaseModel):
    """Declarative cross-field validation rule."""

    rule_id: str = Field(..., min_length=1, description="Unique identifier for the cross-field constraint")
    rule_type: str = Field(
        ...,
        description="Rule type e.g. 'AGE_AT_DATE', 'MUTUALLY_EXCLUSIVE', 'VALUE_COMPARISON', 'CONDITIONAL_MANDATORY'",
    )
    primary_field: str = Field(..., description="First field involved in validation")
    secondary_field: Optional[str] = Field(None, description="Second field involved in validation")
    operator: Optional[str] = Field(None, description="Comparison operator if applicable")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Specific parameters (e.g. max_age_years)")
    message_en: str = Field(..., description="English error message if constraint is violated")
    message_hi: str = Field(..., description="Hindi error message if constraint is violated")

    model_config = ConfigDict(extra="forbid")


class PolicyFormMetadata(BaseModel):
    """Complete version-bound statutory form metadata specification for a scheme."""

    scheme_code: str = Field(..., min_length=1, max_length=64, description="Canonical scheme code")
    policy_version_id: Optional[uuid.UUID] = Field(None, description="Bound policy version UUID")
    policy_version_code: str = Field(..., min_length=1, max_length=64, description="Statutory version code e.g. 'v3.0-2023'")
    effective_from: str = Field(..., description="Statutory validity start date (ISO format YYYY-MM-DD)")
    rule_definition_hash: Optional[str] = Field(None, description="Canonical SHA-256 rule AST hash")
    sections: List[FormSectionDefinition] = Field(
        default_factory=list, description="Ordered list of form grouping sections"
    )
    fields: List[FormFieldDefinition] = Field(
        default_factory=list, description="Ordered list of generic field definitions"
    )
    evidence_types: List[FormEvidenceDefinition] = Field(
        default_factory=list, description="Required documentary evidence definitions"
    )
    cross_field_rules: List[CrossFieldRule] = Field(
        default_factory=list, description="Declarative cross-field validation rules"
    )

    model_config = ConfigDict(extra="forbid")
