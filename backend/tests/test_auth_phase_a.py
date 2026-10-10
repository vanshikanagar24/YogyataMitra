"""Phase A Authentication & Role-Based Access Control Automated Tests.

Verifies strict authentication and authorization foundation for the TWO user-facing product roles:
1. CITIZEN
2. OFFICER

Covers:
1. Valid Citizen authentication
2. Valid Officer authentication
3. Invalid authentication (wrong credentials / non-existent user)
4. Unauthenticated access to protected Citizen route (401)
5. Unauthenticated access to protected Officer route (401)
6. Citizen token attempting Officer access (403)
7. Officer token attempting Citizen-only access (403)
8. Authenticated access to correct role route (200)
9. Token expiration / invalid signature rejection (401)
10. Citizen registration (signup) and subsequent login (201 & 200)
"""

from __future__ import annotations

import datetime
import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_01_valid_citizen_login(async_client: AsyncClient):
    """1. Valid Citizen authentication via /citizen/auth/login returns JWT."""
    response = await async_client.post(
        "/api/v1/citizen/auth/login",
        json={
            "identifier": "citizen.test@yogyatamitra.local",
            "password": "Citizen@123",
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "access_token" in data
    assert data["token_type"].lower() == "bearer"
    assert data["role"] == "CITIZEN"
    assert data["email"] == "citizen.test@yogyatamitra.local"
    assert data["citizen_ref"] == "SYN-CIT-DEMO0001"


@pytest.mark.asyncio
async def test_02_valid_officer_login(async_client: AsyncClient):
    """2. Valid Officer authentication via /officer/auth/login returns JWT."""
    response = await async_client.post(
        "/api/v1/officer/auth/login",
        json={
            "email": "officer@yogyatamitra.local",
            "password": "Officer@123",
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "access_token" in data
    assert data["token_type"].lower() == "bearer"
    assert data["officer_role"] in ("OFFICER", "SUPERVISOR", "ADMIN")
    assert data["demo_environment"] is True


@pytest.mark.asyncio
async def test_03_invalid_authentication(async_client: AsyncClient):
    """3. Invalid authentication (wrong password or non-existent user) returns 401."""
    # Wrong password for citizen
    cit_res = await async_client.post(
        "/api/v1/citizen/auth/login",
        json={
            "identifier": "citizen.test@yogyatamitra.local",
            "password": "WrongPassword999",
        },
    )
    assert cit_res.status_code == 401

    # Non-existent citizen
    cit_res2 = await async_client.post(
        "/api/v1/citizen/auth/login",
        json={
            "identifier": "nonexistent@example.com",
            "password": "Password@123",
        },
    )
    assert cit_res2.status_code == 401

    # Wrong password for officer
    off_res = await async_client.post(
        "/api/v1/officer/auth/login",
        json={
            "email": "officer@yogyatamitra.local",
            "password": "WrongPassword999",
        },
    )
    assert off_res.status_code == 401

    # Non-existent officer
    off_res2 = await async_client.post(
        "/api/v1/officer/auth/login",
        json={
            "email": "fake.officer@yogyatamitra.local",
            "password": "Officer@123",
        },
    )
    assert off_res2.status_code == 401


@pytest.mark.asyncio
async def test_04_unauthenticated_citizen_route_rejected(async_client: AsyncClient):
    """4. Unauthenticated access to protected Citizen route (/citizen/auth/me) returns 401."""
    response = await async_client.get("/api/v1/citizen/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_05_unauthenticated_officer_route_rejected(async_client: AsyncClient):
    """5. Unauthenticated access to protected Officer route (/officer/queue) returns 401."""
    response = await async_client.get("/api/v1/officer/queue")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_06_citizen_token_cannot_access_officer_route(async_client: AsyncClient):
    """6. Citizen JWT attempting Officer route (/officer/queue) receives 403 Forbidden."""
    # Login as citizen
    login_res = await async_client.post(
        "/api/v1/citizen/auth/login",
        json={
            "identifier": "citizen.test@yogyatamitra.local",
            "password": "Citizen@123",
        },
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    # Attempt officer queue
    officer_res = await async_client.get(
        "/api/v1/officer/queue",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert officer_res.status_code == 403
    assert "Citizen accounts cannot access internal verification portal" in officer_res.text


@pytest.mark.asyncio
async def test_07_officer_token_cannot_access_citizen_route(async_client: AsyncClient):
    """7. Officer JWT attempting Citizen route (/citizen/auth/me) receives 403 Forbidden."""
    # Login as officer
    login_res = await async_client.post(
        "/api/v1/officer/auth/login",
        json={
            "email": "officer@yogyatamitra.local",
            "password": "Officer@123",
        },
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    # Attempt citizen profile
    citizen_res = await async_client.get(
        "/api/v1/citizen/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert citizen_res.status_code == 403
    assert "Officer accounts must use internal portal endpoints" in citizen_res.text


@pytest.mark.asyncio
async def test_08_authenticated_correct_role_access(async_client: AsyncClient):
    """8. Authenticated access to respective role routes succeeds with 200."""
    # 8a. Officer -> /officer/queue
    off_login = await async_client.post(
        "/api/v1/officer/auth/login",
        json={
            "email": "officer@yogyatamitra.local",
            "password": "Officer@123",
        },
    )
    off_token = off_login.json()["access_token"]
    off_queue = await async_client.get(
        "/api/v1/officer/queue",
        headers={"Authorization": f"Bearer {off_token}"},
    )
    assert off_queue.status_code == 200

    # 8b. Citizen -> /citizen/auth/me
    cit_login = await async_client.post(
        "/api/v1/citizen/auth/login",
        json={
            "identifier": "citizen.test@yogyatamitra.local",
            "password": "Citizen@123",
        },
    )
    cit_token = cit_login.json()["access_token"]
    cit_me = await async_client.get(
        "/api/v1/citizen/auth/me",
        headers={"Authorization": f"Bearer {cit_token}"},
    )
    assert cit_me.status_code == 200
    cit_data = cit_me.json()
    assert cit_data["role"] == "CITIZEN"
    assert cit_data["email"] == "citizen.test@yogyatamitra.local"


@pytest.mark.asyncio
async def test_09_expired_or_invalid_signature_token_rejected(async_client: AsyncClient):
    """9. Token expiration or invalid signature returns 401 Unauthorized."""
    # 9a. Invalid signature token (tampered secret)
    tampered_token = create_access_token(
        data={"sub": "citizen.test@yogyatamitra.local", "role": "CITIZEN"}
    ) + "tampered"
    res1 = await async_client.get(
        "/api/v1/citizen/auth/me",
        headers={"Authorization": f"Bearer {tampered_token}"},
    )
    assert res1.status_code == 401

    # 9b. Expired token
    expired_token = create_access_token(
        data={"sub": "citizen.test@yogyatamitra.local", "role": "CITIZEN"},
        expires_delta=datetime.timedelta(seconds=-10),
    )
    res2 = await async_client.get(
        "/api/v1/citizen/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert res2.status_code == 401


@pytest.mark.asyncio
async def test_10_citizen_signup_and_subsequent_login(async_client: AsyncClient):
    """10. Citizen registration (/citizen/auth/signup) returns 201, and subsequent login returns 200."""
    new_citizen_email = f"citizen.new_{datetime.datetime.now().timestamp()}@yogyatamitra.local"
    signup_payload = {
        "email": new_citizen_email,
        "password": "StrongPassword@123",
        "name": "Ramesh Kumar",
        "state": "Uttar Pradesh",
        "district": "Varanasi",
    }

    # Signup
    signup_res = await async_client.post(
        "/api/v1/citizen/auth/signup",
        json=signup_payload,
    )
    assert signup_res.status_code == 201, signup_res.text
    signup_data = signup_res.json()
    assert signup_data["role"] == "CITIZEN"
    assert signup_data["citizen_name"] == "Ramesh Kumar"
    assert "SYN-CIT-" in signup_data["citizen_ref"]
    assert "access_token" in signup_data

    # Subsequent Login using email
    login_res = await async_client.post(
        "/api/v1/citizen/auth/login",
        json={
            "identifier": new_citizen_email,
            "password": "StrongPassword@123",
        },
    )
    assert login_res.status_code == 200, login_res.text
    login_data = login_res.json()
    assert login_data["role"] == "CITIZEN"
    assert login_data["citizen_ref"] == signup_data["citizen_ref"]

    # Subsequent Login using synthetic reference
    login_ref_res = await async_client.post(
        "/api/v1/citizen/auth/login",
        json={
            "identifier": signup_data["citizen_ref"],
            "password": "StrongPassword@123",
        },
    )
    assert login_ref_res.status_code == 200, login_ref_res.text
    assert login_ref_res.json()["email"] == new_citizen_email
