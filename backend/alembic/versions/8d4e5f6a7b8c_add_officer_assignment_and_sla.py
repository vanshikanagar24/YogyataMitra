"""add_officer_assignment_and_sla

Revision ID: 8d4e5f6a7b8c
Revises: 7a3c4b5e6f8d
Create Date: 2026-09-29 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '8d4e5f6a7b8c'
down_revision: Union[str, None] = '7a3c4b5e6f8d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create assignment_status_enum
    assignment_status_enum = postgresql.ENUM(
        'UNASSIGNED',
        'ASSIGNED',
        'IN_PROGRESS',
        'REASSIGNED',
        'COMPLETED',
        name='assignment_status_enum',
        create_type=False,
    )
    assignment_status_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create officer_assignments table
    op.create_table(
        'officer_assignments',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('journey_id', sa.UUID(), nullable=False),
        sa.Column('officer_identity', sa.String(length=128), nullable=False),
        sa.Column('officer_name', sa.String(length=128), nullable=True),
        sa.Column('assigned_by', sa.String(length=128), server_default='SYSTEM_BALANCER', nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('due_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('sla_duration_hours', sa.Integer(), server_default='48', nullable=False),
        sa.Column(
            'status',
            postgresql.ENUM(
                'UNASSIGNED',
                'ASSIGNED',
                'IN_PROGRESS',
                'REASSIGNED',
                'COMPLETED',
                name='assignment_status_enum',
                create_type=False,
            ),
            server_default='ASSIGNED',
            nullable=False,
        ),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('reassigned_to_id', sa.UUID(), nullable=True),
        sa.Column('reassignment_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['journey_id'], ['evaluation_journeys.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reassigned_to_id'], ['officer_assignments.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )

    # 3. Create indexes
    op.create_index(
        op.f('ix_officer_assignment_journey_id'),
        'officer_assignments',
        ['journey_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_officer_assignment_officer_identity'),
        'officer_assignments',
        ['officer_identity'],
        unique=False,
    )
    op.create_index(
        op.f('ix_officer_assignment_is_active'),
        'officer_assignments',
        ['is_active'],
        unique=False,
    )
    op.create_index(
        op.f('ix_officer_assignment_status'),
        'officer_assignments',
        ['status'],
        unique=False,
    )
    op.create_index(
        op.f('ix_officer_assignment_due_at'),
        'officer_assignments',
        ['due_at'],
        unique=False,
    )

    # Partial unique index ensuring at most ONE active assignment per journey
    op.create_index(
        'uq_officer_assignment_active_journey',
        'officer_assignments',
        ['journey_id'],
        unique=True,
        postgresql_where=sa.text('is_active = true'),
    )


def downgrade() -> None:
    op.drop_index('uq_officer_assignment_active_journey', table_name='officer_assignments')
    op.drop_index(op.f('ix_officer_assignment_due_at'), table_name='officer_assignments')
    op.drop_index(op.f('ix_officer_assignment_status'), table_name='officer_assignments')
    op.drop_index(op.f('ix_officer_assignment_is_active'), table_name='officer_assignments')
    op.drop_index(op.f('ix_officer_assignment_officer_identity'), table_name='officer_assignments')
    op.drop_index(op.f('ix_officer_assignment_journey_id'), table_name='officer_assignments')
    op.drop_table('officer_assignments')

    assignment_status_enum = postgresql.ENUM(
        'UNASSIGNED',
        'ASSIGNED',
        'IN_PROGRESS',
        'REASSIGNED',
        'COMPLETED',
        name='assignment_status_enum',
    )
    assignment_status_enum.drop(op.get_bind(), checkfirst=True)
