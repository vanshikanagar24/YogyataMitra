"""Pydantic schemas for Scheme, PolicyVersion, and RuleSet domain entities."""

import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import SchemeStatus


# --- RuleSet Schemas ---

class RuleSetBase(BaseModel):
    definition_json: Dict[str, Any] = Field(..., description="Declarative Rule AST definition")
    schema_version: str = Field("1.0", description="AST schema specification version")
    rule_set_version: str = Field("1.0", description="Version of the rule set definition")


class RuleSetCreate(RuleSetBase):
    policy_version_id: uuid.UUID


class RuleSetResponse(RuleSetBase):
    id: uuid.UUID
    policy_version_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- PolicyVersion Schemas ---

class PolicyVersionBase(BaseModel):
    version_code: str = Field(..., max_length=64, description="Version code e.g. v1.0-2018")
    effective_from: date = Field(..., description="Start date of policy validity")
    effective_to: Optional[date] = Field(None, description="End date of policy validity, or null if open-ended")
    source_url: str = Field(..., max_length=512, description="Authoritative statutory source URL")
    source_title: str = Field(..., max_length=255, description="Title of official gazette/guidelines")
    source_document_identifier: Optional[str] = Field(None, max_length=128)
    rule_definition_hash: Optional[str] = Field(None, max_length=128)


class PolicyVersionCreate(PolicyVersionBase):
    scheme_id: uuid.UUID


class PolicyVersionResponse(PolicyVersionBase):
    id: uuid.UUID
    scheme_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    rule_set: Optional[RuleSetResponse] = None

    model_config = ConfigDict(from_attributes=True)


# --- Scheme Schemas ---

class SchemeBase(BaseModel):
    scheme_code: str = Field(..., max_length=64, description="Unique alphanumeric identifier e.g. pmkisan")
    name_en: str = Field(..., max_length=255, description="Official scheme name in English")
    name_hi: str = Field(..., max_length=255, description="Official scheme name in Hindi")
    description_en: str = Field(..., description="Detailed description in English")
    description_hi: str = Field(..., description="Detailed description in Hindi")
    ministry: Optional[str] = Field(None, max_length=255)
    official_url: str = Field(..., max_length=512)
    status: SchemeStatus = Field(default=SchemeStatus.ACTIVE)


class SchemeCreate(SchemeBase):
    pass


class SchemeResponse(SchemeBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    policy_versions: List[PolicyVersionResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
