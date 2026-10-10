"""Citizen Authentication Schemas.

Pydantic v2 schemas for citizen self-registration, credential login,
and authenticated profile inspection.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class CitizenLoginRequest(BaseModel):
    """Payload for citizen login via email or synthetic reference."""

    identifier: str = Field(
        ...,
        min_length=3,
        max_length=128,
        description="Citizen email or synthetic reference (e.g. SYN-CIT-...)",
    )
    password: str = Field(
        ...,
        min_length=6,
        max_length=128,
        description="Citizen account password",
    )

    model_config = ConfigDict(extra="forbid")


class CitizenSignupRequest(BaseModel):
    """Payload for citizen account registration."""

    name: str = Field(
        ...,
        min_length=2,
        max_length=128,
        description="Full name of citizen applicant",
    )
    email: str = Field(
        ...,
        min_length=5,
        max_length=128,
        description="Email address for notifications and account recovery",
    )
    password: str = Field(
        ...,
        min_length=6,
        max_length=128,
        description="Account password (minimum 6 characters)",
    )
    state: Optional[str] = Field(
        None,
        max_length=128,
        description="State of residence",
    )
    district: Optional[str] = Field(
        None,
        max_length=128,
        description="District of residence",
    )

    model_config = ConfigDict(extra="forbid")


class CitizenAuthResponse(BaseModel):
    """Authentication response returning signed JWT access token and citizen profile."""

    access_token: str
    token_type: str = "bearer"
    citizen_name: str
    citizen_ref: str
    email: str
    role: str = "CITIZEN"
    state: Optional[str] = None
    district: Optional[str] = None


class CitizenProfileResponse(BaseModel):
    """Authenticated citizen profile details."""

    citizen_name: str
    citizen_ref: str
    email: str
    role: str = "CITIZEN"
    state: Optional[str] = None
    district: Optional[str] = None
