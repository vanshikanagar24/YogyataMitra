"""Pydantic v2 API Schemas for YogyataMitra Phase 6 API Layer.

Strict contract-first schemas enforcing extra="forbid" on requests,
well-defined response envelopes, and comprehensive error structures.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EligibilityResult, SchemeStatus


# ==============================================================================
# Error Schemas
# ==============================================================================

class ErrorDetail(BaseModel):
    """Structured error payload details."""
    code: str = Field(..., description="Stable machine-readable error code")
    message: str = Field(..., description="Human-readable error explanation")
    details: Optional[Dict[str, Any]] = Field(None, description="Detailed context or parameter errors")

    model_config = ConfigDict(extra="forbid")


class ErrorResponse(BaseModel):
    """Standardized API error envelope."""
    error: ErrorDetail

    model_config = ConfigDict(extra="forbid")


# ==============================================================================
# Scheme & Policy Version Schemas
# ==============================================================================

class PolicyVersionSummaryResponse(BaseModel):
    """Summary of a policy version associated with a scheme."""
    version_code: str = Field(..., description="Unique policy version code e.g. v2.0-2019")
    effective_from: date = Field(..., description="Statutory effective start date")
    effective_to: Optional[date] = Field(None, description="Statutory effective end date, or null if current")
    rule_definition_hash: Optional[str] = Field(None, description="Canonical SHA-256 hash of rule AST")

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class SchemeSummaryResponse(BaseModel):
    """Summary response for scheme discovery."""
    id: uuid.UUID = Field(..., description="Scheme unique identifier")
    scheme_code: str = Field(..., description="Machine-readable scheme code e.g. PM_KISAN")
    name_en: str = Field(..., description="Official scheme name in English")
    name_hi: str = Field(..., description="Official scheme name in Hindi")
    description_en: str = Field(..., description="Scheme description in English")
    description_hi: str = Field(..., description="Scheme description in Hindi")
    ministry: Optional[str] = Field(None, description="Sponsoring government ministry")
    official_url: str = Field(..., description="Official government portal URL")
    status: SchemeStatus = Field(..., description="Current operational status")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class SchemeDetailResponse(SchemeSummaryResponse):
    """Detailed scheme metadata including associated policy versions."""
    updated_at: datetime = Field(..., description="Last update timestamp")
    policy_versions: List[PolicyVersionSummaryResponse] = Field(
        default_factory=list, description="Historical and active policy versions"
    )

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class PolicyVersionDetailResponse(BaseModel):
    """Detailed policy version representation with statutory provenance."""
    id: uuid.UUID = Field(..., description="Policy version unique identifier")
    scheme_code: str = Field(..., description="Parent scheme code")
    version_code: str = Field(..., description="Policy version code")
    effective_from: date = Field(..., description="Start date of statutory validity")
    effective_to: Optional[date] = Field(None, description="End date of statutory validity, or null")
    source_url: str = Field(..., description="Authoritative statutory source URL")
    source_title: str = Field(..., description="Official title of the gazette notification or order")
    source_document_identifier: Optional[str] = Field(None, description="Statutory document reference identifier")
    rule_definition_hash: Optional[str] = Field(None, description="Cryptographic SHA-256 hash of rule AST")
    ruleset_schema_version: Optional[str] = Field(None, description="AST schema specification version")
    ruleset_version: Optional[str] = Field(None, description="Ruleset revision version")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True, extra="forbid")


# ==============================================================================
# Evaluation Request Schemas
# ==============================================================================

class FamilyFacts(BaseModel):
    """Family-level facts evaluated by scheme rulesets."""
    owns_cultivable_land: Optional[bool] = Field(None, description="Whether family owns cultivable land")
    total_land_area_hectares: Optional[float] = Field(None, ge=0.0, description="Total cultivable landholding in hectares")
    is_institutional_landholder: Optional[bool] = Field(None, description="Whether land is held institutionally")
    has_constitutional_post_holder: Optional[bool] = Field(None, description="Exclusion: former/present constitutional post")
    has_public_representative: Optional[bool] = Field(None, description="Exclusion: former/present MP/MLA/Mayor/Chairperson")
    has_disqualified_government_employee: Optional[bool] = Field(None, description="Exclusion: serving/retired govt employee")
    has_pensioner_above_ten_thousand: Optional[bool] = Field(None, description="Exclusion: pensioner >= Rs. 10,000/mo")
    has_income_tax_payer: Optional[bool] = Field(None, description="Exclusion: paid income tax in last assessment year")
    has_registered_practicing_professional: Optional[bool] = Field(None, description="Exclusion: Doctor, Engineer, Lawyer, CA, Architect")
    is_nri: Optional[bool] = Field(None, description="Exclusion: Non-Resident Indian farmer family under Income Tax Act")
    has_nri_relative: Optional[bool] = Field(None, description="Secondary flag: whether family has an NRI relative")
    active_ssy_accounts_count: Optional[int] = Field(None, ge=0, description="Number of active SSY accounts in family")
    has_multiple_birth_exception: Optional[bool] = Field(None, description="Multiple birth exception for third girl child")
    medical_twin_triplet_certificate_available: Optional[bool] = Field(None, description="Medical proof for multiple birth")

    model_config = ConfigDict(extra="forbid")


class LandFacts(BaseModel):
    """Land-parcel and transfer facts."""
    transferred_after_cutoff: Optional[bool] = Field(None, description="Whether land was transferred after cut-off date (2019-02-01)")
    acquired_via_succession: Optional[bool] = Field(None, description="Whether land was acquired via succession")
    previous_owner_deceased: Optional[bool] = Field(None, description="Whether previous landowner is deceased")

    model_config = ConfigDict(extra="forbid")


class BeneficiaryFacts(BaseModel):
    """Individual beneficiary facts (e.g. girl child)."""
    gender: Optional[str] = Field(None, max_length=32, description="Gender (e.g. FEMALE)")
    is_indian_resident: Optional[bool] = Field(None, description="Whether beneficiary is an Indian resident")
    date_of_birth: Optional[date] = Field(None, description="Date of birth of the beneficiary")

    model_config = ConfigDict(extra="forbid")


class GuardianFacts(BaseModel):
    """Guardian facts for minor beneficiary accounts."""
    is_natural_guardian: Optional[bool] = Field(None, description="Whether applicant is natural father or mother")
    is_court_appointed_legal_guardian: Optional[bool] = Field(None, description="Whether applicant is court-appointed guardian")

    model_config = ConfigDict(extra="forbid")


class AccountFacts(BaseModel):
    """Account opening facts."""
    opening_date: Optional[date] = Field(None, description="Proposed or actual account opening date")
    is_first_account_for_child: Optional[bool] = Field(None, description="Whether this is the first account for the child")

    model_config = ConfigDict(extra="forbid")


class EvaluationFacts(BaseModel):
    """Composite structured facts evaluated by the engine.
    
    Strictly forbids arbitrary unknown top-level sections.
    """
    family: Optional[FamilyFacts] = Field(None, description="Family-level attributes and exclusions")
    land: Optional[LandFacts] = Field(None, description="Land ownership, cut-off, and succession facts")
    beneficiary: Optional[BeneficiaryFacts] = Field(None, description="Primary beneficiary facts")
    guardian: Optional[GuardianFacts] = Field(None, description="Guardian facts for minor accounts")
    account: Optional[AccountFacts] = Field(None, description="Account-specific facts")

    model_config = ConfigDict(extra="forbid")

    def to_engine_dict(self) -> Dict[str, Any]:
        """Convert facts into a nested dictionary suitable for EvaluationContext.
        
        Only includes fields that were explicitly set (preserving the distinction
        between truly missing fields and explicit nulls/booleans).
        """
        raw = self.model_dump(exclude_unset=True)
        return raw


class EvaluationRequest(BaseModel):
    """Statutory eligibility evaluation request.
    
    Requires explicit scheme and evaluation_date to ensure deterministic
    and historically reproducible policy selection.
    """
    scheme_code: str = Field(..., min_length=1, max_length=64, description="Statutory scheme code e.g. PM_KISAN or SSY")
    evaluation_date: date = Field(..., description="As-of reference date for policy selection and temporal rules")
    facts: EvaluationFacts = Field(..., description="Citizen, family, and asset facts to evaluate")
    policy_version_code: Optional[str] = Field(None, max_length=64, description="Optional explicit policy version for audit verification")
    citizen_id: Optional[uuid.UUID] = Field(None, description="Optional existing synthetic citizen UUID")
    citizen_ref: Optional[str] = Field(None, max_length=64, description="Optional synthetic reference identifier")

    model_config = ConfigDict(extra="forbid")


# ==============================================================================
# Evaluation Response Schemas
# ==============================================================================

class BlockerResponse(BaseModel):
    """Structured blocker preventing immediate welfare entitlement."""
    code: str = Field(..., description="Machine-readable blocker identifier")
    category: str = Field(..., description="Category: INSUFFICIENT_INFORMATION, DISQUALIFYING_CONDITION, etc.")
    field_path: Optional[str] = Field(None, description="Specific missing field path")
    rule_id: Optional[str] = Field(None, description="Rule ID that produced the blocker")
    message_en: str = Field(..., description="Explanation in English")
    message_hi: str = Field(..., description="Explanation in Hindi")

    model_config = ConfigDict(extra="forbid")


class EvaluationResponse(BaseModel):
    """Comprehensive, explainable eligibility evaluation decision."""
    evaluation_id: uuid.UUID = Field(..., description="Unique evaluation identifier")
    scheme_code: str = Field(..., description="Statutory scheme evaluated")
    policy_version_code: str = Field(..., description="Policy version effective as of evaluation_date")
    rule_definition_hash: str = Field(..., description="Cryptographic SHA-256 hash of canonical ruleset AST")
    evaluation_date: date = Field(..., description="Reference date of evaluation")
    effective_from: date = Field(..., description="Policy version effective start date")
    effective_to: Optional[date] = Field(None, description="Policy version effective end date, or null if open-ended")
    overall_result: EligibilityResult = Field(..., description="Canonical 5-state eligibility decision")
    root_truth_value: str = Field(..., description="Root AST truth value (TRUE, FALSE, UNKNOWN)")
    reasons_en: List[str] = Field(default_factory=list, description="English reasons explaining the decision")
    reasons_hi: List[str] = Field(default_factory=list, description="Hindi reasons explaining the decision")
    missing_fields: List[str] = Field(default_factory=list, description="Facts required by policy but missing in request")
    satisfied_rules: List[str] = Field(default_factory=list, description="IDs of rules satisfied")
    failed_rules: List[str] = Field(default_factory=list, description="IDs of rules that failed")
    unknown_rules: List[str] = Field(default_factory=list, description="IDs of rules that evaluated to UNKNOWN")
    blockers: List[BlockerResponse] = Field(default_factory=list, description="Actionable blockers preventing entitlement")
    audit_persisted: bool = Field(True, description="Indicates whether audit trace was successfully persisted")
    created_at: datetime = Field(..., description="Timestamp when evaluation was executed")
    trace: Optional[Dict[str, Any]] = Field(None, description="Detailed AST evaluation trace graph")

    model_config = ConfigDict(extra="forbid")


class PersistedEvaluationResponse(BaseModel):
    """Persisted historical evaluation record retrieved from database."""
    id: uuid.UUID = Field(..., description="Evaluation unique identifier")
    citizen_id: uuid.UUID = Field(..., description="Associated synthetic citizen identifier")
    scheme_id: uuid.UUID = Field(..., description="Scheme unique identifier")
    scheme_code: str = Field(..., description="Scheme code")
    policy_version_id: uuid.UUID = Field(..., description="Policy version unique identifier")
    policy_version_code: str = Field(..., description="Policy version code")
    evaluation_date: date = Field(..., description="Reference date of evaluation")
    result_state: EligibilityResult = Field(..., description="Final eligibility result state")
    rule_definition_hash: Optional[str] = Field(None, description="SHA-256 rule definition hash")
    trace_schema_version: str = Field(..., description="Version of trace schema")
    input_snapshot_json: Dict[str, Any] = Field(..., description="Frozen input snapshot facts")
    trace_json: Dict[str, Any] = Field(..., description="Persisted explainability trace")
    created_at: datetime = Field(..., description="Timestamp when evaluation was persisted")

    model_config = ConfigDict(from_attributes=True, extra="forbid")
