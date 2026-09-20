"""add_human_review_and_audit_models

Revision ID: d4e9f1a2b3c5
Revises: 9bc038aebd36
Create Date: 2026-09-19 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd4e9f1a2b3c5'
down_revision: Union[str, None] = '9bc038aebd36'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create Enum safely
    human_review_status_enum = postgresql.ENUM(
        'PENDING', 'IN_REVIEW', 'CLARIFICATION_REQUIRED', 'VERIFIED',
        'REJECTED', 'ESCALATED', 'COMPLETED',
        name='human_review_status_enum'
    )
    human_review_status_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create human_reviews table
    op.create_table(
        'human_reviews',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('journey_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('evaluation_journeys.id', ondelete='CASCADE'), nullable=False),
        sa.Column('evaluation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('evaluation_traces.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reviewer_identity', sa.String(length=128), nullable=False),
        sa.Column('reviewer_role', sa.String(length=64), nullable=False),
        sa.Column(
            'status',
            postgresql.ENUM('PENDING', 'IN_REVIEW', 'CLARIFICATION_REQUIRED', 'VERIFIED', 'REJECTED', 'ESCALATED', 'COMPLETED', name='human_review_status_enum', create_type=False),
            nullable=False,
            server_default='PENDING',
        ),
        sa.Column('decision', sa.String(length=64), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('details_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_human_reviews_journey_id'), 'human_reviews', ['journey_id'], unique=False)
    op.create_index(op.f('ix_human_reviews_evaluation_id'), 'human_reviews', ['evaluation_id'], unique=False)
    op.create_index(op.f('ix_human_reviews_status'), 'human_reviews', ['status'], unique=False)

    # 3. Create human_review_audit_events table
    op.create_table(
        'human_review_audit_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('review_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('human_reviews.id', ondelete='CASCADE'), nullable=False),
        sa.Column('journey_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('evaluation_journeys.id', ondelete='CASCADE'), nullable=False),
        sa.Column('actor_identity', sa.String(length=128), nullable=False),
        sa.Column('actor_role', sa.String(length=64), nullable=False),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('previous_status', sa.String(length=64), nullable=True),
        sa.Column('new_status', sa.String(length=64), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('details_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_human_review_audit_events_review_id'), 'human_review_audit_events', ['review_id'], unique=False)
    op.create_index(op.f('ix_human_review_audit_events_journey_id'), 'human_review_audit_events', ['journey_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_human_review_audit_events_journey_id'), table_name='human_review_audit_events')
    op.drop_index(op.f('ix_human_review_audit_events_review_id'), table_name='human_review_audit_events')
    op.drop_table('human_review_audit_events')

    op.drop_index(op.f('ix_human_reviews_status'), table_name='human_reviews')
    op.drop_index(op.f('ix_human_reviews_evaluation_id'), table_name='human_reviews')
    op.drop_index(op.f('ix_human_reviews_journey_id'), table_name='human_reviews')
    op.drop_table('human_reviews')

    human_review_status_enum = postgresql.ENUM(
        'PENDING', 'IN_REVIEW', 'CLARIFICATION_REQUIRED', 'VERIFIED',
        'REJECTED', 'ESCALATED', 'COMPLETED',
        name='human_review_status_enum'
    )
    human_review_status_enum.drop(op.get_bind(), checkfirst=True)
