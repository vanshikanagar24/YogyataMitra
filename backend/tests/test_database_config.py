"""Tests for database configuration, sessionmaker setup, and connectivity."""

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.orm import DeclarativeBase

from app.core.config import Settings, settings
from app.core.database import AsyncSessionLocal, engine
from app.models.base import Base


def test_database_config_loading():
    """Verify database configuration builds a valid asyncpg connection URI."""
    assert settings.POSTGRES_USER is not None
    assert settings.POSTGRES_SERVER is not None
    assert isinstance(settings.POSTGRES_PORT, int) and settings.POSTGRES_PORT > 0
    assert settings.POSTGRES_DB is not None
    assert settings.SQLALCHEMY_DATABASE_URI.startswith("postgresql+asyncpg://")
    assert f"@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}" in settings.SQLALCHEMY_DATABASE_URI


def test_database_url_override():
    """Verify DATABASE_URL_OVERRIDE takes precedence when configured."""
    custom_uri = "postgresql+asyncpg://custom_user:custom_pass@custom_host:5433/custom_db"
    custom_settings = Settings(DATABASE_URL_OVERRIDE=custom_uri)
    assert custom_settings.SQLALCHEMY_DATABASE_URI == custom_uri


def test_declarative_base_is_valid():
    """Verify that Base is a valid SQLAlchemy 2.x DeclarativeBase."""
    assert issubclass(Base, DeclarativeBase)
    assert hasattr(Base, "metadata")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_connectivity_live(async_client: AsyncClient):
    """Integration test: Verify GET /health/db connects to PostgreSQL when service is reachable.
    
    If PostgreSQL is unreachable in the current environment, this test verifies that the
    endpoint handles connection errors deterministically with HTTP 503 rather than crashing unhandled.
    """
    response = await async_client.get("/health/db")
    if response.status_code == 200:
        assert response.json() == {
            "status": "ok",
            "database": "connected",
            "service": settings.PROJECT_NAME,
        }
    else:
        assert response.status_code == 503
        assert "Database unreachable" in response.json().get("detail", "")
