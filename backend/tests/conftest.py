"""Pytest fixtures for YogyataMitra backend tests."""

from typing import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.main import app

# Test engine using NullPool to prevent event-loop leakage across async test cases
test_engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    poolclass=NullPool,
    echo=False,
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client fixture bound to the FastAPI application."""
    from app.core.database import get_db

    async def _get_test_db() -> AsyncGenerator[AsyncSession, None]:
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = _get_test_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Async database session fixture using NullPool for isolated testing."""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(autouse=True)
async def cleanup_test_schemes():
    """Ensure non-canonical test schemes are cleaned up after tests."""
    yield
    async with TestSessionLocal() as session:
        from sqlalchemy import text
        statements = [
            "DELETE FROM rule_sets WHERE policy_version_id IN (SELECT id FROM policy_versions WHERE scheme_id IN (SELECT id FROM schemes WHERE scheme_code NOT IN ('PM_KISAN', 'SSY')));",
            "DELETE FROM policy_draft_tests WHERE draft_id IN (SELECT id FROM policy_drafts WHERE scheme_id IN (SELECT id FROM schemes WHERE scheme_code NOT IN ('PM_KISAN', 'SSY')));",
            "DELETE FROM policy_draft_revisions WHERE draft_id IN (SELECT id FROM policy_drafts WHERE scheme_id IN (SELECT id FROM schemes WHERE scheme_code NOT IN ('PM_KISAN', 'SSY')));",
            "DELETE FROM policy_draft_audit_events WHERE draft_id IN (SELECT id FROM policy_drafts WHERE scheme_id IN (SELECT id FROM schemes WHERE scheme_code NOT IN ('PM_KISAN', 'SSY')));",
            "DELETE FROM policy_drafts WHERE scheme_id IN (SELECT id FROM schemes WHERE scheme_code NOT IN ('PM_KISAN', 'SSY'));",
            "DELETE FROM evaluation_traces WHERE scheme_id IN (SELECT id FROM schemes WHERE scheme_code NOT IN ('PM_KISAN', 'SSY'));",
            "DELETE FROM policy_versions WHERE scheme_id IN (SELECT id FROM schemes WHERE scheme_code NOT IN ('PM_KISAN', 'SSY'));",
            "DELETE FROM schemes WHERE scheme_code NOT IN ('PM_KISAN', 'SSY');",
        ]
        for stmt in statements:
            await session.execute(text(stmt))
        await session.commit()

