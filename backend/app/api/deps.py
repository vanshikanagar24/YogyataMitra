"""FastAPI dependency injection utilities for Officer Portal.

Enforces HTTP Bearer token extraction, RFC 7519 token decoding, and strict RBAC
(Role-Based Access Control) separating internal officers and supervisors from citizens.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_access_token

# HTTPBearer scheme without automatic error to enable customized 401 messages
http_bearer = HTTPBearer(auto_error=False)


async def get_current_officer(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
) -> Dict[str, Any]:
    """Validate Bearer JWT token and ensure caller is an authorized officer or supervisor.

    Raises:
        HTTPException(401): If token is missing, invalid, or expired.
        HTTPException(403): If caller holds a CITIZEN role or unknown non-officer role.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided or are invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired officer authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role = payload.get("role")
    if role == "CITIZEN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Citizen accounts cannot access internal verification portal",
        )

    if role not in ("OFFICER", "SUPERVISOR", "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Unrecognized or unauthorized officer role",
        )

    return {
        "email": payload.get("sub"),
        "role": role,
        "name": payload.get("name"),
        "designation": payload.get("designation"),
        "department": payload.get("department"),
    }


def require_role(allowed_roles: List[str]) -> Callable:
    """Dependency factory restricting route execution to specified officer roles."""

    async def role_checker(
        current_officer: Dict[str, Any] = Depends(get_current_officer),
    ) -> Dict[str, Any]:
        if current_officer["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires elevated role: {', '.join(allowed_roles)}. Current role is {current_officer['role']}.",
            )
        return current_officer

    return role_checker


async def get_current_citizen(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
) -> Dict[str, Any]:
    """Validate Bearer JWT token and ensure caller is an authenticated citizen."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided or are invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired citizen authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role = payload.get("role")
    if role != "CITIZEN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Officer accounts must use internal portal endpoints",
        )

    return {
        "email": payload.get("sub"),
        "role": role,
        "name": payload.get("name"),
        "citizen_ref": payload.get("citizen_ref"),
        "state": payload.get("state"),
        "district": payload.get("district"),
    }
