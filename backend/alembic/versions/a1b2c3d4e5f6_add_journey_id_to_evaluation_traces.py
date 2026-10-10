"""add_journey_id_to_evaluation_traces

Revision ID: a1b2c3d4e5f6
Revises: 9e1f2a3b4c5d
Create Date: 2026-09-30 10:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '9e1f2a3b4c5d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add journey_id and evaluated_by columns to evaluation_traces
    op.add_column('evaluation_traces', sa.Column('journey_id', sa.UUID(), nullable=True))
    op.add_column('evaluation_traces', sa.Column('evaluated_by', sa.String(length=128), nullable=True))

    # 2. Create index on journey_id
    op.create_index(
        op.f('ix_evaluation_traces_journey_id'),
        'evaluation_traces',
        ['journey_id'],
        unique=False
    )

    # 3. Create foreign key referencing evaluation_journeys
    op.create_foreign_key(
        'fk_evaluation_traces_journey_id',
        'evaluation_traces',
        'evaluation_journeys',
        ['journey_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_evaluation_traces_journey_id', 'evaluation_traces', type_='foreignkey')
    op.drop_index(op.f('ix_evaluation_traces_journey_id'), table_name='evaluation_traces')
    op.drop_column('evaluation_traces', 'evaluated_by')
    op.drop_column('evaluation_traces', 'journey_id')
