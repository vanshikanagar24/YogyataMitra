"""Pydantic schemas for Citizen, Claim, Evidence, and VerificationRecord entities."""

import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.enums import ClaimStatus, EvidenceStatus, VerificationStatus


# --- VerificationRecord Schemas ---

class VerificationRecordBase(BaseModel):
    verification_method: str = Field(..., max_length=128)
    status: VerificationStatus = Field(default=VerificationStatus.PENDING)
    verified_by: Optional[str] = Field(None, max_length=128)
    verified_at: Optional[datetime] = None
    details_json: Optional[Dict[str, Any]] = None


class VerificationRecordCreate(VerificationRecordBase):
    evidence_id: Optional[uuid.UUID] = None
    claim_id: Optional[uuid.UUID] = None


class VerificationRecordResponse(VerificationRecordBase):
    id: uuid.UUID
    evidence_id: Optional[uuid.UUID] = None
    claim_id: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Evidence Schemas ---

class EvidenceBase(BaseModel):
    evidence_type: str = Field(..., max_length=128)
    storage_reference: str = Field(..., max_length=512)
    metadata_json: Optional[Dict[str, Any]] = None
    status: EvidenceStatus = Field(default=EvidenceStatus.PENDING)
    rejection_reason: Optional[str] = None


class EvidenceCreate(EvidenceBase):
    claim_id: uuid.UUID


class EvidenceResponse(EvidenceBase):
    id: uuid.UUID
    claim_id: uuid.UUID
    submitted_at: datetime
    verified_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    verification_records: List[VerificationRecordResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# --- Claim Schemas ---

class ClaimBase(BaseModel):
    claim_type: str = Field(..., max_length=128, description="Attribute key e.g. cultivable_land_ownership")
    value_json: Dict[str, Any] = Field(..., description="Structured or scalar attribute value payload")
    source: str = Field("SELF_DECLARATION", max_length=64)
    status: ClaimStatus = Field(default=ClaimStatus.CLAIMED)


class ClaimCreate(ClaimBase):
    citizen_id: uuid.UUID


class ClaimResponse(ClaimBase):
    id: uuid.UUID
    citizen_id: uuid.UUID
    claimed_at: datetime
    updated_at: datetime
    evidence_items: List[EvidenceResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# --- Citizen Schemas ---

class CitizenBase(BaseModel):
    synthetic_reference: str = Field(..., max_length=64, description="Synthetic demo-safe identifier")
    display_name: Optional[str] = Field(None, max_length=128)
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(None, max_length=32)
    state: Optional[str] = Field(None, max_length=128)
    district: Optional[str] = Field(None, max_length=128)


class CitizenCreate(CitizenBase):
    pass


class CitizenResponse(CitizenBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    claims: List[ClaimResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
