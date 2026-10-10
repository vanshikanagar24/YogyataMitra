"""add_policy_version_and_submitted_at_to_journey

Revision ID: 7a3c4b5e6f8d
Revises: 6b2e477e42cb
Create Date: 2026-09-29 09:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '7a3c4b5e6f8d'
down_revision: Union[str, None] = '6b2e477e42cb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('evaluation_journeys', sa.Column('policy_version_id', sa.UUID(), nullable=True))
    op.add_column('evaluation_journeys', sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        'fk_evaluation_journeys_policy_version_id',
        'evaluation_journeys',
        'policy_versions',
        ['policy_version_id'],
        ['id'],
        ondelete='RESTRICT'
    )
    op.create_index(
        op.f('ix_evaluation_journeys_policy_version_id'),
        'evaluation_journeys',
        ['policy_version_id'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_evaluation_journeys_policy_version_id'), table_name='evaluation_journeys')
    op.drop_constraint('fk_evaluation_journeys_policy_version_id', 'evaluation_journeys', type_='foreignkey')
    op.drop_column('evaluation_journeys', 'submitted_at')
    op.drop_column('evaluation_journeys', 'policy_version_id')
