"""Citizen Authentication API Router.

Provides dedicated endpoints for:
- Citizen registration / Sign Up (creates citizen record and returns signed JWT)
- Citizen login via email or synthetic reference
- Authenticated citizen profile inspection
"""

from __future__ import annotations

import secrets
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_citizen
from app.core.database import get_db
from app.core.security import (
    authenticate_citizen,
    create_access_token,
    register_citizen_user,
)
from app.models.citizen import Citizen
from app.schemas.citizen_auth import (
    CitizenAuthResponse,
    CitizenLoginRequest,
    CitizenProfileResponse,
    CitizenSignupRequest,
)

router = APIRouter(prefix="/citizen/auth", tags=["Citizen Authentication"])


@router.post(
    "/signup",
    response_model=CitizenAuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Citizen Account Registration",
    description="Registers a new citizen profile, assigns synthetic reference, and returns JWT access token.",
)
async def citizen_signup(
    payload: CitizenSignupRequest,
    db: AsyncSession = Depends(get_db),
) -> CitizenAuthResponse:
    # 1. Generate synthetic reference
    synthetic_ref = f"SYN-CIT-{secrets.token_hex(4).upper()}"

    # 2. Register user in credential store
    try:
        user = register_citizen_user(
            email=str(payload.email),
            password=payload.password,
            name=payload.name,
            state=payload.state,
            district=payload.district,
            citizen_ref=synthetic_ref,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    # 3. Create database citizen record if not already exists
    stmt = select(Citizen).where(Citizen.synthetic_reference == synthetic_ref)
    result = await db.execute(stmt)
    db_citizen = result.scalar_one_or_none()
    if not db_citizen:
        db_citizen = Citizen(
            synthetic_reference=synthetic_ref,
            display_name=payload.name,
            state=payload.state,
            district=payload.district,
        )
        db.add(db_citizen)
        await db.commit()
        await db.refresh(db_citizen)

    # 4. Issue standard signed HS256 JWT
    token_data = {
        "sub": user["email"],
        "role": "CITIZEN",
        "name": user["name"],
        "citizen_ref": user["citizen_ref"],
        "state": user.get("state"),
        "district": user.get("district"),
    }
    access_token = create_access_token(data=token_data)

    return CitizenAuthResponse(
        access_token=access_token,
        token_type="bearer",
        citizen_name=user["name"],
        citizen_ref=user["citizen_ref"],
        email=user["email"],
        role="CITIZEN",
        state=user.get("state"),
        district=user.get("district"),
    )


@router.post(
    "/login",
    response_model=CitizenAuthResponse,
    summary="Citizen Login",
    description="Authenticates citizen via email or synthetic reference and returns JWT access token.",
)
async def citizen_login(payload: CitizenLoginRequest) -> CitizenAuthResponse:
    user = authenticate_citizen(payload.identifier, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid citizen credentials. Please check your email/reference or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = {
        "sub": user["email"],
        "role": "CITIZEN",
        "name": user["name"],
        "citizen_ref": user["citizen_ref"],
        "state": user.get("state"),
        "district": user.get("district"),
    }
    access_token = create_access_token(data=token_data)

    return CitizenAuthResponse(
        access_token=access_token,
        token_type="bearer",
        citizen_name=user["name"],
        citizen_ref=user["citizen_ref"],
        email=user["email"],
        role="CITIZEN",
        state=user.get("state"),
        district=user.get("district"),
    )


@router.get(
    "/me",
    response_model=CitizenProfileResponse,
    summary="Current Citizen Profile",
    description="Returns authenticated citizen profile from Bearer JWT token.",
)
async def get_my_citizen_profile(
    current_citizen: Dict[str, Any] = Depends(get_current_citizen),
) -> CitizenProfileResponse:
    return CitizenProfileResponse(
        citizen_name=current_citizen["name"],
        citizen_ref=current_citizen["citizen_ref"],
        email=current_citizen["email"],
        role="CITIZEN",
        state=current_citizen.get("state"),
        district=current_citizen.get("district"),
    )
