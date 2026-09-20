"""Pydantic schemas for EvaluationTrace domain entity."""

import uuid
from datetime import date, datetime
from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import EligibilityResult


class EvaluationTraceBase(BaseModel):
    evaluation_date: date = Field(..., description="As-of evaluation date for temporal policy binding")
    input_snapshot_json: Dict[str, Any] = Field(..., description="Complete frozen citizen/claim input state")
    result_state: EligibilityResult = Field(..., description="Five-state eligibility decision")
    trace_json: Dict[str, Any] = Field(..., description="Detailed AST rule-by-rule evaluation graph/trace")
    rule_definition_hash: str | None = Field(None, description="SHA-256 hash of canonical rule definition")
    trace_schema_version: str = Field("1.0.0", description="Version of trace schema")


class EvaluationTraceCreate(EvaluationTraceBase):
    citizen_id: uuid.UUID
    scheme_id: uuid.UUID
    policy_version_id: uuid.UUID


class EvaluationTraceResponse(EvaluationTraceBase):
    id: uuid.UUID
    citizen_id: uuid.UUID
    scheme_id: uuid.UUID
    policy_version_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
