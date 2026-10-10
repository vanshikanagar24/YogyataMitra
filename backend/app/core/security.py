"""Authentication and cryptographic security utilities for Officer Portal.

Implements standard RFC 7519 HMAC-SHA256 (HS256) JSON Web Tokens and PBKDF2-SHA256
password hashing using Python standard library primitives (hmac, hashlib, base64, json, secrets).
Includes conditional development officer and supervisor demo accounts (strictly disabled in production).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from app.core.config import settings


def _b64url_encode(data: bytes) -> str:
    """Encode bytes to base64url string without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    """Decode base64url string with flexible padding."""
    padding = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode((s + padding).encode("ascii"))


def hash_password(password: str, iterations: int = 100_000) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with a unique cryptographically random per-password salt.

    Returns standard format: pbkdf2_sha256$<iterations>$<salt_b64>$<hash_b64>
    """
    salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    salt_b64 = base64.b64encode(salt).decode("ascii")
    key_b64 = base64.b64encode(key).decode("ascii")
    return f"pbkdf2_sha256${iterations}${salt_b64}${key_b64}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against hashed password in constant time."""
    try:
        parts = hashed_password.split("$")
        if len(parts) == 4 and parts[0] == "pbkdf2_sha256":
            _, iterations_str, salt_b64, key_b64 = parts
            iterations = int(iterations_str)
            salt = base64.b64decode(salt_b64.encode("ascii"))
            expected_key = base64.b64decode(key_b64.encode("ascii"))
            computed_key = hashlib.pbkdf2_hmac(
                "sha256", plain_password.encode("utf-8"), salt, iterations
            )
            return hmac.compare_digest(computed_key, expected_key)
        return False
    except Exception:
        return False


# ------------------------------------------------------------------------------
# Demo Accounts Storage (Development & Demo Only)
# ------------------------------------------------------------------------------

def _build_demo_users() -> Dict[str, Dict[str, Any]]:
    """Build development demo users with fresh per-account salted hashes."""
    return {
        "officer@yogyatamitra.local": {
            "email": "officer@yogyatamitra.local",
            "password_hash": hash_password("Officer@123"),
            "name": "Senior Verification Officer (Demo)",
            "role": "OFFICER",
            "designation": "Verification Officer Grade II",
            "department": "Welfare Verification Cell",
        },
        "officer.varanasi@yogyatamitra.local": {
            "email": "officer.varanasi@yogyatamitra.local",
            "password_hash": hash_password("Officer@123"),
            "name": "Varanasi Verification Officer (Demo)",
            "role": "OFFICER",
            "designation": "Verification Officer Grade I",
            "department": "District Verification Cell, Varanasi",
        },
        "officer.lucknow@yogyatamitra.local": {
            "email": "officer.lucknow@yogyatamitra.local",
            "password_hash": hash_password("Officer@123"),
            "name": "Lucknow Verification Officer (Demo)",
            "role": "OFFICER",
            "designation": "Verification Officer Grade I",
            "department": "District Verification Cell, Lucknow",
        },

        "supervisor@yogyatamitra.local": {
            "email": "supervisor@yogyatamitra.local",
            "password_hash": hash_password("Supervisor@123"),
            "name": "Welfare Review Supervisor (Demo)",
            "role": "SUPERVISOR",
            "designation": "Assistant Commissioner (Review & Appeals)",
            "department": "Supervisory Review Division",
        },
        "citizen.test@yogyatamitra.local": {
            "email": "citizen.test@yogyatamitra.local",
            "password_hash": hash_password("Citizen@123"),
            "name": "Test Citizen (Demo)",
            "role": "CITIZEN",
            "citizen_ref": "SYN-CIT-DEMO0001",
            "designation": "Citizen Applicant",
            "department": "Public",
            "state": "Maharashtra",
            "district": "Pune",
        },
    }


_CACHED_DEMO_USERS: Optional[Dict[str, Dict[str, Any]]] = None


def get_demo_users() -> Dict[str, Dict[str, Any]]:
    """Return demo users only when running in development/demo/test environment.

    Strictly disabled and returns empty dict in production.
    """
    global _CACHED_DEMO_USERS
    env = (settings.ENVIRONMENT or "development").lower().strip()
    if env == "production" or not getattr(settings, "ENABLE_DEMO_ACCOUNTS", False):
        return {}
    if _CACHED_DEMO_USERS is None:
        _CACHED_DEMO_USERS = _build_demo_users()
    return _CACHED_DEMO_USERS


class _DemoUsersProxy(dict):
    """Dynamic proxy ensuring DEMO_USERS reflects current environment settings."""

    def get(self, key: str, default: Any = None) -> Any:
        return get_demo_users().get(key, default)

    def __getitem__(self, key: str) -> Any:
        return get_demo_users()[key]

    def __contains__(self, key: object) -> bool:
        return key in get_demo_users()

    def __len__(self) -> int:
        return len(get_demo_users())

    def __iter__(self):
        return iter(get_demo_users())

    def keys(self):
        return get_demo_users().keys()

    def values(self):
        return get_demo_users().values()

    def items(self):
        return get_demo_users().items()


DEMO_USERS: Dict[str, Dict[str, Any]] = _DemoUsersProxy()


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """Create a signed HS256 JWT access token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
    })

    header = {"alg": "HS256", "typ": "JWT"}
    header_json = json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_json = json.dumps(to_encode, separators=(",", ":"), sort_keys=True).encode("utf-8")

    header_b64 = _b64url_encode(header_json)
    payload_b64 = _b64url_encode(payload_json)
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")

    signature = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    signature_b64 = _b64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode a signed HS256 JWT access token.

    Returns the payload dict if valid, or None if signature fails or token is expired.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None

        header_b64, payload_b64, signature_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")

        expected_sig = hmac.new(
            settings.SECRET_KEY.encode("utf-8"),
            signing_input,
            hashlib.sha256,
        ).digest()
        expected_sig_b64 = _b64url_encode(expected_sig)

        if not hmac.compare_digest(signature_b64, expected_sig_b64):
            return None

        payload_bytes = _b64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))

        # Check expiration
        exp = payload.get("exp")
        if exp is not None and time.time() > exp:
            return None

        return payload
    except Exception:
        return None


def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate user against demo users store.

    In production or if demo accounts are disabled, fails closed (returns None).
    """
    env = (settings.ENVIRONMENT or "development").lower().strip()
    if env == "production" or not getattr(settings, "ENABLE_DEMO_ACCOUNTS", False):
        return None

    user = DEMO_USERS.get(email.lower().strip())
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return {
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "designation": user["designation"],
        "department": user["department"],
    }


REGISTERED_CITIZENS: Dict[str, Dict[str, Any]] = {}


def register_citizen_user(
    email: str,
    password: str,
    name: str,
    state: Optional[str] = None,
    district: Optional[str] = None,
    citizen_ref: Optional[str] = None,
) -> Dict[str, Any]:
    """Register a new citizen with a synthetic reference and salted PBKDF2 hash."""
    clean_email = email.lower().strip()
    if clean_email in DEMO_USERS or clean_email in REGISTERED_CITIZENS:
        raise ValueError("An account with this email address is already registered.")

    ref = citizen_ref or f"SYN-CIT-{secrets.token_hex(4).upper()}"
    user_record = {
        "email": clean_email,
        "password_hash": hash_password(password),
        "name": name.strip(),
        "role": "CITIZEN",
        "citizen_ref": ref,
        "designation": "Citizen Beneficiary",
        "department": "Public",
        "state": state.strip() if state else None,
        "district": district.strip() if district else None,
    }
    REGISTERED_CITIZENS[clean_email] = user_record
    return user_record


def authenticate_citizen(identifier: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate citizen by email or synthetic reference."""
    clean_id = identifier.strip()
    clean_id_lower = clean_id.lower()
    clean_id_upper = clean_id.upper()

    user: Optional[Dict[str, Any]] = None

    # Check registered citizens by email
    if clean_id_lower in REGISTERED_CITIZENS:
        user = REGISTERED_CITIZENS[clean_id_lower]
    elif not user:
        for u in REGISTERED_CITIZENS.values():
            if u.get("citizen_ref") == clean_id_upper:
                user = u
                break

    # Check demo users store
    if not user:
        if clean_id_lower in DEMO_USERS:
            candidate = DEMO_USERS[clean_id_lower]
            if candidate.get("role") == "CITIZEN":
                user = candidate
        if not user:
            for candidate in DEMO_USERS.values():
                if candidate.get("role") == "CITIZEN" and candidate.get("citizen_ref") == clean_id_upper:
                    user = candidate
                    break

    if not user:
        return None

    if not verify_password(password, user["password_hash"]):
        return None

    return {
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "citizen_ref": user.get("citizen_ref", f"SYN-CIT-{secrets.token_hex(4).upper()}"),
        "state": user.get("state"),
        "district": user.get("district"),
        "designation": user.get("designation", "Citizen Beneficiary"),
        "department": user.get("department", "Public"),
    }
