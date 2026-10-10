"""add_evidence_clarification_and_verification_rounds

Revision ID: 9e1f2a3b4c5d
Revises: 8d4e5f6a7b8c
Create Date: 2026-09-29 14:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '9e1f2a3b4c5d'
down_revision: Union[str, None] = '8d4e5f6a7b8c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add CLARIFICATION_REQUIRED to existing evidence_status_enum in PostgreSQL
    # In PostgreSQL, ALTER TYPE ... ADD VALUE must be executed outside a multi-statement transaction or safely committed.
    conn = op.get_bind()
    conn.execute(sa.text("ALTER TYPE evidence_status_enum ADD VALUE IF NOT EXISTS 'CLARIFICATION_REQUIRED'"))

    # 2. Create clarification_status_enum
    clarification_status_enum = postgresql.ENUM(
        'OPEN',
        'RESPONDED',
        'UNDER_REVIEW',
        'RESOLVED',
        'CLOSED',
        name='clarification_status_enum',
        create_type=False,
    )
    clarification_status_enum.create(conn, checkfirst=True)

    # 3. Create clarification_requests table
    op.create_table(
        'clarification_requests',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('journey_id', sa.UUID(), nullable=False),
        sa.Column('claim_id', sa.UUID(), nullable=True),
        sa.Column('evidence_id', sa.UUID(), nullable=True),
        sa.Column('round', sa.Integer(), server_default='1', nullable=False),
        sa.Column('requesting_officer', sa.String(length=128), nullable=False),
        sa.Column('requesting_officer_role', sa.String(length=64), server_default='OFFICER', nullable=False),
        sa.Column('request_reason', sa.Text(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column(
            'status',
            postgresql.ENUM(
                'OPEN',
                'RESPONDED',
                'UNDER_REVIEW',
                'RESOLVED',
                'CLOSED',
                name='clarification_status_enum',
                create_type=False,
            ),
            server_default='OPEN',
            nullable=False,
        ),
        sa.Column('requested_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('response_text', sa.Text(), nullable=True),
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('replacement_evidence_id', sa.UUID(), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['journey_id'], ['evaluation_journeys.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['claim_id'], ['claims.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['evidence_id'], ['evidence.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['replacement_evidence_id'], ['evidence.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_clarification_journey_id', 'clarification_requests', ['journey_id'], unique=False)
    op.create_index('ix_clarification_evidence_id', 'clarification_requests', ['evidence_id'], unique=False)
    op.create_index('ix_clarification_claim_id', 'clarification_requests', ['claim_id'], unique=False)
    op.create_index('ix_clarification_status', 'clarification_requests', ['status'], unique=False)
    op.create_index('ix_clarification_round', 'clarification_requests', ['journey_id', 'round'], unique=False)

    # 4. Add round and clarification_request_id to verification_records
    op.add_column(
        'verification_records',
        sa.Column('round', sa.Integer(), server_default='1', nullable=False)
    )
    op.add_column(
        'verification_records',
        sa.Column('clarification_request_id', sa.UUID(), nullable=True)
    )
    op.create_foreign_key(
        'fk_verification_records_clarification_request_id',
        'verification_records',
        'clarification_requests',
        ['clarification_request_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_verification_records_clarification_request_id', 'verification_records', ['clarification_request_id'], unique=False)


def downgrade() -> None:
    op.drop_constraint('fk_verification_records_clarification_request_id', 'verification_records', type_='foreignkey')
    op.drop_index('ix_verification_records_clarification_request_id', table_name='verification_records')
    op.drop_column('verification_records', 'clarification_request_id')
    op.drop_column('verification_records', 'round')

    op.drop_index('ix_clarification_round', table_name='clarification_requests')
    op.drop_index('ix_clarification_status', table_name='clarification_requests')
    op.drop_index('ix_clarification_claim_id', table_name='clarification_requests')
    op.drop_index('ix_clarification_evidence_id', table_name='clarification_requests')
    op.drop_index('ix_clarification_journey_id', table_name='clarification_requests')
    op.drop_table('clarification_requests')

    conn = op.get_bind()
    clarification_status_enum = postgresql.ENUM(name='clarification_status_enum')
    clarification_status_enum.drop(conn, checkfirst=True)
