"""Tests for FastAPI application startup and basic health check."""

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.main import app


def test_app_starts():
    """Verify FastAPI application instance initializes with proper metadata."""
    assert app.title == settings.PROJECT_NAME
    assert app.openapi_url == f"{settings.API_V1_STR}/openapi.json"
    assert app.version == "1.0.0"


@pytest.mark.asyncio
async def test_health_endpoint_status_200(async_client: AsyncClient):
    """Verify GET /health returns HTTP 200 OK."""
    response = await async_client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_endpoint_payload(async_client: AsyncClient):
    """Verify GET /health response body contains the expected deterministic payload."""
    response = await async_client.get("/health")
    payload = response.json()
    assert payload == {
        "status": "ok",
        "service": settings.PROJECT_NAME,
    }
