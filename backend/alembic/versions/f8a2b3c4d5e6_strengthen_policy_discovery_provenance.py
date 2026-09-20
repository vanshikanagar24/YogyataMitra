"""strengthen_policy_discovery_provenance

Revision ID: f8a2b3c4d5e6
Revises: e7f1a2b3c4d5
Create Date: 2026-09-19 23:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8a2b3c4d5e6'
down_revision: Union[str, None] = 'e7f1a2b3c4d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add strengthened values to provenance_status_enum
    new_provenance_values = [
        'UNVERIFIED',
        'OFFICIAL_DOMAIN_MATCH',
        'SOURCE_RETRIEVED',
        'PROVENANCE_REVIEW_REQUIRED',
        'REVIEWED_BY_AUTHORIZED_REVIEWER',
    ]
    for val in new_provenance_values:
        op.execute(sa.text(f"ALTER TYPE provenance_status_enum ADD VALUE IF NOT EXISTS '{val}'"))

    # 2. Add retrieved_at and adversarial_flag_detected columns to policy_discovery_candidates
    op.add_column(
        'policy_discovery_candidates',
        sa.Column(
            'retrieved_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.add_column(
        'policy_discovery_candidates',
        sa.Column(
            'adversarial_flag_detected',
            sa.Boolean(),
            server_default=sa.text('false'),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column('policy_discovery_candidates', 'adversarial_flag_detected')
    op.drop_column('policy_discovery_candidates', 'retrieved_at')
