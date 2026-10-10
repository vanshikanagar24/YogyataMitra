"""phase_j_production_hardening_enums_and_triggers

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-10-01 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Expand provenance_completeness_enum with granular verification states (Phase I F-01)
    conn.execute(sa.text("ALTER TYPE provenance_completeness_enum ADD VALUE IF NOT EXISTS 'SOURCE_METADATA_VERIFIED';"))
    conn.execute(sa.text("ALTER TYPE provenance_completeness_enum ADD VALUE IF NOT EXISTS 'PHYSICAL_ARTIFACT_VERIFIED';"))

    # 2. Create PostgreSQL trigger to protect provenance_audit_events against UPDATE and DELETE (Phase I F-04 / J-J)
    conn.execute(sa.text("""
        CREATE OR REPLACE FUNCTION prevent_provenance_audit_mutation()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'provenance_audit_events table is strictly append-only; UPDATE and DELETE operations are forbidden.';
        END;
        $$ LANGUAGE plpgsql;
    """))

    conn.execute(sa.text("DROP TRIGGER IF EXISTS trg_provenance_audit_events_immutable ON provenance_audit_events;"))

    conn.execute(sa.text("""
        CREATE TRIGGER trg_provenance_audit_events_immutable
        BEFORE UPDATE OR DELETE ON provenance_audit_events
        FOR EACH ROW
        EXECUTE FUNCTION prevent_provenance_audit_mutation();
    """))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DROP TRIGGER IF EXISTS trg_provenance_audit_events_immutable ON provenance_audit_events;"))
    conn.execute(sa.text("DROP FUNCTION IF EXISTS prevent_provenance_audit_mutation();"))
