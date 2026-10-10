"""Pydantic v2 schemas for Citizen Portal Application management (Phase B).

Provides strongly typed schemas for:
- Citizen application summaries (dashboard and listing)
- Detailed application dossier with claims, transitions, and evaluation outcomes
- Dashboard statistical aggregates
- IDOR-safe serialization
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EligibilityResult, JourneyState
from app.schemas.journey import (
    JourneyClaimResponse,
    JourneyTransitionRecordResponse,
)


class CitizenApplicationSummary(BaseModel):
    """Compact summary of a citizen welfare application for dashboard and list views."""

    id: uuid.UUID = Field(..., description="Unique journey identifier")
    application_ref: str = Field(..., description="Human-readable application reference e.g. APP-2026-A1B2C3D4")
    scheme_id: uuid.UUID = Field(..., description="Welfare scheme ID")
    scheme_code: str = Field(..., description="Canonical scheme code e.g. PM_KISAN or SSY")
    scheme_name: str = Field(..., description="Bilingual or primary scheme name")
    scheme_name_hi: Optional[str] = Field(None, description="Hindi scheme name")
    ministry: Optional[str] = Field(None, description="Nodal Ministry")
    state: JourneyState = Field(..., description="Current lifecycle state")
    status_label_en: str = Field(..., description="Plain-language English status label")
    status_label_hi: str = Field(..., description="Plain-language Hindi status label")
    created_at: datetime = Field(..., description="Submission or draft creation timestamp")
    updated_at: datetime = Field(..., description="Last modification timestamp")
    submitted_at: Optional[datetime] = Field(None, description="Formal submission timestamp")
    policy_version_id: Optional[uuid.UUID] = Field(None, description="Bound policy version ID")
    policy_version_code: Optional[str] = Field(None, description="Applied statutory policy version code")
    rule_definition_hash: Optional[str] = Field(None, description="Cryptographic SHA-256 rule AST hash")
    evaluation_outcome: Optional[EligibilityResult] = Field(None, description="Final or latest eligibility determination")
    claims_count: int = Field(0, description="Total number of asserted factual claims")
    evidence_count: int = Field(0, description="Total submitted documentary evidence attachments")

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class EvaluationSummary(BaseModel):
    """Evaluation trace summary attached to a citizen application."""

    evaluation_id: uuid.UUID
    result_state: EligibilityResult
    evaluation_date: str
    policy_version_code: Optional[str] = None
    rule_definition_hash: Optional[str] = None
    reasons_en: List[str] = Field(default_factory=list)
    reasons_hi: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class CitizenApplicationDetail(CitizenApplicationSummary):
    """Comprehensive application dossier view for an authenticated citizen."""

    citizen_ref: str = Field(..., description="Synthetic citizen beneficiary reference")
    citizen_name: Optional[str] = Field(None, description="Citizen display name")
    official_url: Optional[str] = Field(None, description="Official government scheme portal URL")
    claims: List[JourneyClaimResponse] = Field(default_factory=list, description="All asserted factual claims with evidence")
    transitions: List[JourneyTransitionRecordResponse] = Field(
        default_factory=list, description="Chronological audit records of state progression"
    )
    latest_evaluation: Optional[EvaluationSummary] = Field(
        None, description="Structured evaluation outcome summary if evaluated"
    )
    allowed_actions: List[str] = Field(
        default_factory=list, description="Permitted citizen actions on this application"
    )
    verification_status: Optional[str] = Field(
        None, description="Backend-authoritative verification readiness status"
    )
    clarifications: List[Dict[str, Any]] = Field(
        default_factory=list, description="Sanitized clarification requests requiring citizen attention or historical records"
    )

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class CitizenDashboardStats(BaseModel):
    """High-level summary metrics for the authenticated citizen's dashboard."""

    total_applications: int = Field(..., description="Total applications across all schemes")
    in_progress_count: int = Field(..., description="Applications currently undergoing review or verification")
    evaluated_count: int = Field(..., description="Applications with completed evaluations")
    action_required_count: int = Field(..., description="Applications requiring citizen action or clarification")
    recent_applications: List[CitizenApplicationSummary] = Field(
        default_factory=list, description="Most recent applications (up to 5)"
    )

    model_config = ConfigDict(extra="forbid")


class CitizenApplicationCreateRequest(BaseModel):
    """Payload to initiate a new application for a scheme from the citizen workspace."""

    scheme_code: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Statutory scheme code to apply for (e.g. PM_KISAN, SSY)",
    )
    initial_facts: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional initial factual assertions",
    )

    model_config = ConfigDict(extra="forbid")


class CitizenEvidenceSubmission(BaseModel):
    """Single evidence item submitted or attached by a citizen applicant."""

    evidence_type: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Statutory evidence category (e.g. LAND_RECORD, AADHAAR, BIRTH_CERTIFICATE)",
    )
    storage_reference: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="Document storage identifier or reference URI",
    )
    document_name: Optional[str] = Field(
        None,
        max_length=255,
        description="User-friendly name of the attached document",
    )
    metadata_json: Optional[Dict[str, Any]] = Field(
        None,
        description="Supplementary metadata (issuing authority, date, document number)",
    )

    model_config = ConfigDict(extra="forbid")


class CitizenApplicationDraftUpdateRequest(BaseModel):
    """Payload to update an in-progress draft application prior to final submission."""

    facts: Optional[Dict[str, Any]] = Field(
        None,
        description="Updated fact assertions (flat key-value or structured)",
    )
    evidence_items: Optional[List[CitizenEvidenceSubmission]] = Field(
        None,
        description="Updated documentary evidence attachments",
    )

    model_config = ConfigDict(extra="forbid")


class CitizenApplicationSubmitRequest(BaseModel):
    """Payload to formally commit and submit an application for statutory processing."""

    facts: Dict[str, Any] = Field(
        ...,
        description="Complete citizen factual declarations for scheme evaluation",
    )
    evidence_items: Optional[List[CitizenEvidenceSubmission]] = Field(
        None,
        description="All corroborating documentary evidence attachments",
    )
    declaration_confirmed: bool = Field(
        True,
        description="Statutory acknowledgement that submitted facts are authentic and accurate",
    )

    model_config = ConfigDict(extra="forbid")


from app.schemas.form_metadata import (
    CrossFieldRule,
    FieldCondition,
    FormSectionDefinition,
)


class SchemeRequirementField(BaseModel):
    """Single input field requirement for a statutory scheme application (Phase C & G)."""

    field_key: str = Field(..., description="Canonical dot-notated fact key e.g. 'family.owns_cultivable_land'")
    field_type: str = Field(..., description="'boolean', 'number', 'integer', 'decimal', 'date', 'text', 'select', 'radio', 'multi_select', 'address', etc.")
    label_en: str = Field(..., description="English field label")
    label_hi: str = Field(..., description="Hindi field label")
    help_text_en: Optional[str] = Field(None, description="English guidance / explanatory text")
    help_text_hi: Optional[str] = Field(None, description="Hindi guidance / explanatory text")
    required: bool = Field(True, description="Whether this field is mandatory for submission")
    options: Optional[List[Dict[str, Any]]] = Field(None, description="Options for select/radio fields")
    default_value: Optional[Any] = Field(None, description="Pre-filled default or placeholder value")
    claim_type: Optional[str] = Field(None, description="Target claim type if different from field_key")
    section_key: str = Field("general", description="Associated form section key")
    display_order: int = Field(0, description="Display order within form section")
    min_value: Optional[float] = Field(None, description="Minimum numeric value constraint")
    max_value: Optional[float] = Field(None, description="Maximum numeric value constraint")
    min_date: Optional[str] = Field(None, description="Minimum date string (YYYY-MM-DD)")
    max_date: Optional[str] = Field(None, description="Maximum date string (YYYY-MM-DD)")
    step: Optional[float] = Field(None, description="Numeric step interval (e.g. 0.01)")
    validation_message_en: Optional[str] = Field(None, description="Custom English validation error message")
    validation_message_hi: Optional[str] = Field(None, description="Custom Hindi validation error message")
    associated_evidence_type: Optional[str] = Field(None, description="Associated evidence category")
    condition: Optional[Dict[str, Any]] = Field(None, description="Declarative visibility/applicability condition")
    is_active: bool = Field(True, description="Whether field is active")

    model_config = ConfigDict(extra="forbid")


class SchemeRequirementEvidence(BaseModel):
    """Documentary evidence requirement specification for a scheme (Phase C & G)."""

    evidence_type: str = Field(..., description="Statutory evidence code e.g. 'LAND_RECORD'")
    label_en: str = Field(..., description="English document name")
    label_hi: str = Field(..., description="Hindi document name")
    description_en: str = Field(..., description="English purpose and accepted formats")
    description_hi: str = Field(..., description="Hindi purpose and accepted formats")
    mandatory: bool = Field(True, description="Whether this document is strictly required")
    allowed_extensions: Optional[List[str]] = Field(
        default_factory=lambda: [".pdf", ".jpg", ".jpeg", ".png"],
        description="Permitted file MIME extensions",
    )
    max_size_mb: int = Field(5, description="Maximum upload size in MB")
    associated_field_keys: Optional[List[str]] = Field(
        default_factory=list, description="Field keys corroborated by this evidence"
    )

    model_config = ConfigDict(extra="forbid")


class SchemeRequirementsResponse(BaseModel):
    """Generic scheme requirements specification for application entry forms (Phase C & G)."""

    scheme_code: str = Field(..., description="Canonical scheme code")
    scheme_name_en: str = Field(..., description="Official scheme name in English")
    scheme_name_hi: str = Field(..., description="Official scheme name in Hindi")
    ministry: Optional[str] = Field(None, description="Nodal Ministry")
    official_url: str = Field(..., description="Authoritative scheme portal URL")
    policy_version_id: uuid.UUID = Field(..., description="Active statutory policy version ID")
    policy_version_code: str = Field(..., description="Active policy version code e.g. 'v3.0-2023'")
    effective_from: str = Field(..., description="Statutory validity start date")
    rule_definition_hash: Optional[str] = Field(None, description="Canonical SHA-256 rule AST hash")
    sections: List[FormSectionDefinition] = Field(
        default_factory=list, description="Ordered list of form sections for grouping"
    )
    fields: List[SchemeRequirementField] = Field(..., description="Ordered list of required fact input fields")
    evidence_types: List[SchemeRequirementEvidence] = Field(..., description="Supported evidence document types")
    cross_field_rules: List[CrossFieldRule] = Field(
        default_factory=list, description="Declarative cross-field validation rules"
    )

    model_config = ConfigDict(extra="forbid")


class CitizenDecisionResponse(BaseModel):
    """Citizen-facing statutory eligibility decision and plain-language explanation."""

    application_id: uuid.UUID = Field(..., description="Unique journey / application identifier")
    application_ref: str = Field(..., description="Human-readable application reference code")
    scheme_code: str = Field(..., description="Canonical scheme code")
    scheme_name_en: str = Field(..., description="Scheme name in English")
    scheme_name_hi: str = Field(..., description="Scheme name in Hindi")
    is_evaluated: bool = Field(..., description="Whether statutory evaluation has been executed")
    outcome: str = Field(..., description="Statutory decision outcome (ELIGIBLE, INELIGIBLE, INSUFFICIENT_INFORMATION, VERIFICATION_REQUIRED, PENDING_EVALUATION)")
    policy_version_code: Optional[str] = Field(None, description="Statutory policy version code applied")
    evaluated_at: Optional[datetime] = Field(None, description="Timestamp of evaluation execution")
    reasons_en: List[str] = Field(default_factory=list, description="Plain-language statutory reasons in English")
    reasons_hi: List[str] = Field(default_factory=list, description="Plain-language statutory reasons in Hindi")
    passed_conditions: List[str] = Field(default_factory=list, description="Statutory conditions that passed")
    failed_conditions: List[str] = Field(default_factory=list, description="Statutory conditions that failed")
    missing_information: List[str] = Field(default_factory=list, description="Missing factual information fields")
    unverified_requirements: List[str] = Field(default_factory=list, description="Unverified documentary requirements")
    statutory_disclaimer_en: str = Field(
        default="This eligibility evaluation is generated deterministically based on verified statutory criteria and documentary evidence. It does not constitute a final official government disbursement order.",
        description="Legal disclaimer in English",
    )
    statutory_disclaimer_hi: str = Field(
        default="यह पात्रता मूल्यांकन सत्यापित वैधानिक मानदंडों और दस्तावेजी साक्ष्यों के आधार पर निर्धारणात्मक रूप से उत्पन्न किया गया है। यह अंतिम आधिकारिक सरकारी संवितरण आदेश नहीं है।",
        description="Legal disclaimer in Hindi",
    )

    model_config = ConfigDict(from_attributes=True, extra="forbid")
