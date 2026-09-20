"""Tests for Alembic database migrations and schema lifecycle."""

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


from pathlib import Path

def get_alembic_config() -> Config:
    """Load Alembic configuration pointing to alembic.ini."""
    base_dir = Path(__file__).resolve().parent.parent
    ini_path = base_dir / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("script_location", str(base_dir / "alembic"))
    return cfg


@pytest.mark.integration
def test_alembic_migration_lifecycle():
    """Verify that Alembic can downgrade to base and re-upgrade to head cleanly."""
    cfg = get_alembic_config()

    # Downgrade to base
    command.downgrade(cfg, "base")

    # Re-upgrade to head
    command.upgrade(cfg, "head")

    # Re-materialize declarative policies so test database remains consistent for subsequent tests
    import asyncio
    from app.services.policy_loader import load_all_policies
    asyncio.run(load_all_policies())


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
