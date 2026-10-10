"""Tests for Alembic database migrations and schema lifecycle."""

import asyncio
from pathlib import Path
from typing import Optional
import uuid

import asyncpg
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine.url import URL
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.services.policy_loader import load_all_policies


def get_alembic_config(database_name: Optional[str] = None) -> Config:
    """Load Alembic configuration pointing to alembic.ini, optionally targeting an isolated database."""
    base_dir = Path(__file__).resolve().parent.parent
    ini_path = base_dir / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("script_location", str(base_dir / "alembic"))
    if database_name:
        isolated_url = URL.create(
            drivername="postgresql+asyncpg",
            username=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            host=settings.POSTGRES_SERVER,
            port=settings.POSTGRES_PORT,
            database=database_name,
        ).render_as_string(hide_password=False)
        cfg.set_main_option("sqlalchemy.url", isolated_url)
    return cfg


async def _execute_admin_sql(sql: str) -> None:
    """Execute raw SQL statement against the default administrative database connection."""
    conn = await asyncpg.connect(
        host=settings.POSTGRES_SERVER,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        database=settings.POSTGRES_DB,
    )
    try:
        await conn.execute(sql)
    finally:
        await conn.close()


@pytest.mark.integration
def test_alembic_migration_lifecycle():
    """Verify that Alembic can downgrade to base and re-upgrade to head cleanly in an isolated database."""
    isolated_db_name = f"{settings.POSTGRES_DB}_mig_test_{uuid.uuid4().hex[:8]}"

    # Create isolated database for this test run
    asyncio.run(_execute_admin_sql(f'CREATE DATABASE "{isolated_db_name}" OWNER "{settings.POSTGRES_USER}";'))

    try:
        cfg = get_alembic_config(isolated_db_name)

        # Upgrade from base to head
        command.upgrade(cfg, "head")

        # Downgrade to base
        command.downgrade(cfg, "base")

        # Re-upgrade to head
        command.upgrade(cfg, "head")

        # Verify policy loader works in re-upgraded database
        isolated_url = URL.create(
            drivername="postgresql+asyncpg",
            username=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            host=settings.POSTGRES_SERVER,
            port=settings.POSTGRES_PORT,
            database=isolated_db_name,
        ).render_as_string(hide_password=False)

        async def _verify_isolated():
            engine = create_async_engine(isolated_url, poolclass=NullPool)
            Session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
            try:
                async with Session() as session:
                    await load_all_policies(session=session)
            finally:
                await engine.dispose()

        asyncio.run(_verify_isolated())

    finally:
        # Clean up isolated database unconditionally
        asyncio.run(_execute_admin_sql(f'DROP DATABASE IF EXISTS "{isolated_db_name}" WITH (FORCE);'))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_tables_exist_in_database(db_session: AsyncSession):
    """Verify that all 8 core domain tables exist in the PostgreSQL database."""
    expected_tables = {
        "schemes",
        "policy_versions",
        "rule_sets",
        "citizens",
        "claims",
        "evidence",
        "verification_records",
        "evaluation_traces",
    }
    result = await db_session.execute(
        text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
    )
    existing_tables = {row[0] for row in result.fetchall()}
    assert expected_tables.issubset(existing_tables)
