"""update_provenance_completeness_records

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-10-01 11:32:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    # Update existing online official document versions (where document_hash IS NULL) from COMPLETE to SOURCE_METADATA_VERIFIED
    conn.execute(sa.text("""
        UPDATE official_document_versions 
        SET provenance_completeness = 'SOURCE_METADATA_VERIFIED' 
        WHERE document_hash IS NULL AND provenance_completeness = 'COMPLETE';
    """))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE official_document_versions 
        SET provenance_completeness = 'COMPLETE' 
        WHERE provenance_completeness = 'SOURCE_METADATA_VERIFIED';
    """))
