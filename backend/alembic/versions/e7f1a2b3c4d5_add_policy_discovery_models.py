"""add_policy_discovery_models

Revision ID: e7f1a2b3c4d5
Revises: d4e9f1a2b3c5
Create Date: 2026-09-19 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e7f1a2b3c4d5'
down_revision: Union[str, None] = 'd4e9f1a2b3c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create Enums safely
    candidate_type_enum = postgresql.ENUM(
        'ELIGIBILITY_CONDITION', 'EXCLUSION', 'DEFINITIONS',
        'DOCUMENTATION_REQUIREMENT', 'PROCEDURAL_REQUIREMENT',
        'BENEFIT_PARAMETER', 'EFFECTIVE_DATE', 'AMENDMENT',
        'CLARIFICATION', 'SOURCE_REFERENCE',
        name='candidate_type_enum'
    )
    candidate_type_enum.create(op.get_bind(), checkfirst=True)

    provenance_status_enum = postgresql.ENUM(
        'OFFICIAL_GAZETTE', 'OFFICIAL_PORTAL', 'OFFICIAL_CIRCULAR',
        'SECONDARY_OFFICIAL', 'UNKNOWN', 'CONFLICT_DETECTED',
        name='provenance_status_enum'
    )
    provenance_status_enum.create(op.get_bind(), checkfirst=True)

    candidate_review_status_enum = postgresql.ENUM(
        'DISCOVERED', 'EXTRACTED', 'PENDING_REVIEW', 'IN_REVIEW',
        'APPROVED', 'REJECTED', 'NEEDS_CLARIFICATION', 'ARCHIVED',
        name='candidate_review_status_enum'
    )
    candidate_review_status_enum.create(op.get_bind(), checkfirst=True)

    effective_date_status_enum = postgresql.ENUM(
        'CONFIRMED', 'PROSPECTIVE', 'RETROSPECTIVE', 'UNKNOWN', 'AMENDMENT_PENDING',
        name='effective_date_status_enum'
    )
    effective_date_status_enum.create(op.get_bind(), checkfirst=True)

    duplicate_status_enum = postgresql.ENUM(
        'UNIQUE', 'POSSIBLE_DUPLICATE', 'CONFIRMED_DUPLICATE',
        name='duplicate_status_enum'
    )
    duplicate_status_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create policy_discovery_candidates table
    op.create_table(
        'policy_discovery_candidates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('scheme_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('schemes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(length=256), nullable=False),
        sa.Column(
            'candidate_type',
            postgresql.ENUM('ELIGIBILITY_CONDITION', 'EXCLUSION', 'DEFINITIONS', 'DOCUMENTATION_REQUIREMENT', 'PROCEDURAL_REQUIREMENT', 'BENEFIT_PARAMETER', 'EFFECTIVE_DATE', 'AMENDMENT', 'CLARIFICATION', 'SOURCE_REFERENCE', name='candidate_type_enum', create_type=False),
            nullable=False,
        ),
        sa.Column('candidate_text_en', sa.Text(), nullable=False),
        sa.Column('candidate_text_hi', sa.Text(), nullable=False),
        sa.Column('normalized_concept', sa.String(length=128), nullable=False),
        sa.Column('source_url', sa.String(length=512), nullable=False),
        sa.Column('source_title', sa.String(length=256), nullable=False),
        sa.Column('source_publisher', sa.String(length=256), nullable=False),
        sa.Column('source_document_identifier', sa.String(length=128), nullable=True),
        sa.Column('source_publication_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('source_effective_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('source_excerpt', sa.Text(), nullable=False),
        sa.Column('discovered_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('discovered_by', sa.String(length=128), nullable=False, server_default='AI_POLICY_DISCOVERY_AGENT'),
        sa.Column('ai_provider', sa.String(length=64), nullable=False),
        sa.Column('ai_model', sa.String(length=64), nullable=False),
        sa.Column('ai_run_id', sa.String(length=64), nullable=False),
        sa.Column('extraction_confidence', sa.Float(), nullable=False),
        sa.Column('confidence_explanation', sa.Text(), nullable=True),
        sa.Column('uncertainty_notes', sa.Text(), nullable=True),
        sa.Column('questions_for_reviewer', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            'provenance_status',
            postgresql.ENUM('OFFICIAL_GAZETTE', 'OFFICIAL_PORTAL', 'OFFICIAL_CIRCULAR', 'SECONDARY_OFFICIAL', 'UNKNOWN', 'CONFLICT_DETECTED', name='provenance_status_enum', create_type=False),
            nullable=False,
            server_default='UNKNOWN',
        ),
        sa.Column(
            'effective_date_status',
            postgresql.ENUM('CONFIRMED', 'PROSPECTIVE', 'RETROSPECTIVE', 'UNKNOWN', 'AMENDMENT_PENDING', name='effective_date_status_enum', create_type=False),
            nullable=False,
            server_default='UNKNOWN',
        ),
        sa.Column('conflict_detected', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('conflict_details_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            'duplicate_status',
            postgresql.ENUM('UNIQUE', 'POSSIBLE_DUPLICATE', 'CONFIRMED_DUPLICATE', name='duplicate_status_enum', create_type=False),
            nullable=False,
            server_default='UNIQUE',
        ),
        sa.Column('duplicate_of_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('policy_discovery_candidates.id', ondelete='SET NULL'), nullable=True),
        sa.Column(
            'review_status',
            postgresql.ENUM('DISCOVERED', 'EXTRACTED', 'PENDING_REVIEW', 'IN_REVIEW', 'APPROVED', 'REJECTED', 'NEEDS_CLARIFICATION', 'ARCHIVED', name='candidate_review_status_enum', create_type=False),
            nullable=False,
            server_default='PENDING_REVIEW',
        ),
        sa.Column('reviewer_id', sa.String(length=128), nullable=True),
        sa.Column('reviewer_role', sa.String(length=64), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewer_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_policy_discovery_candidates_scheme_id'), 'policy_discovery_candidates', ['scheme_id'], unique=False)
    op.create_index(op.f('ix_policy_discovery_candidates_candidate_type'), 'policy_discovery_candidates', ['candidate_type'], unique=False)
    op.create_index(op.f('ix_policy_discovery_candidates_normalized_concept'), 'policy_discovery_candidates', ['normalized_concept'], unique=False)
    op.create_index(op.f('ix_policy_discovery_candidates_provenance_status'), 'policy_discovery_candidates', ['provenance_status'], unique=False)
    op.create_index(op.f('ix_policy_discovery_candidates_review_status'), 'policy_discovery_candidates', ['review_status'], unique=False)

    # 3. Create policy_discovery_review_events table
    op.create_table(
        'policy_discovery_review_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('candidate_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('policy_discovery_candidates.id', ondelete='CASCADE'), nullable=False),
        sa.Column('actor_identity', sa.String(length=128), nullable=False),
        sa.Column('actor_role', sa.String(length=64), nullable=False),
        sa.Column('previous_status', sa.String(length=64), nullable=True),
        sa.Column('new_status', sa.String(length=64), nullable=False),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('details_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_policy_discovery_review_events_candidate_id'), 'policy_discovery_review_events', ['candidate_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_policy_discovery_review_events_candidate_id'), table_name='policy_discovery_review_events')
    op.drop_table('policy_discovery_review_events')

    op.drop_index(op.f('ix_policy_discovery_candidates_review_status'), table_name='policy_discovery_candidates')
    op.drop_index(op.f('ix_policy_discovery_candidates_provenance_status'), table_name='policy_discovery_candidates')
    op.drop_index(op.f('ix_policy_discovery_candidates_normalized_concept'), table_name='policy_discovery_candidates')
    op.drop_index(op.f('ix_policy_discovery_candidates_candidate_type'), table_name='policy_discovery_candidates')
    op.drop_index(op.f('ix_policy_discovery_candidates_scheme_id'), table_name='policy_discovery_candidates')
    op.drop_table('policy_discovery_candidates')

    duplicate_status_enum = postgresql.ENUM('UNIQUE', 'POSSIBLE_DUPLICATE', 'CONFIRMED_DUPLICATE', name='duplicate_status_enum')
    duplicate_status_enum.drop(op.get_bind(), checkfirst=True)

    effective_date_status_enum = postgresql.ENUM('CONFIRMED', 'PROSPECTIVE', 'RETROSPECTIVE', 'UNKNOWN', 'AMENDMENT_PENDING', name='effective_date_status_enum')
    effective_date_status_enum.drop(op.get_bind(), checkfirst=True)

    candidate_review_status_enum = postgresql.ENUM('DISCOVERED', 'EXTRACTED', 'PENDING_REVIEW', 'IN_REVIEW', 'APPROVED', 'REJECTED', 'NEEDS_CLARIFICATION', 'ARCHIVED', name='candidate_review_status_enum')
    candidate_review_status_enum.drop(op.get_bind(), checkfirst=True)

    provenance_status_enum = postgresql.ENUM('OFFICIAL_GAZETTE', 'OFFICIAL_PORTAL', 'OFFICIAL_CIRCULAR', 'SECONDARY_OFFICIAL', 'UNKNOWN', 'CONFLICT_DETECTED', name='provenance_status_enum')
    provenance_status_enum.drop(op.get_bind(), checkfirst=True)

    candidate_type_enum = postgresql.ENUM('ELIGIBILITY_CONDITION', 'EXCLUSION', 'DEFINITIONS', 'DOCUMENTATION_REQUIREMENT', 'PROCEDURAL_REQUIREMENT', 'BENEFIT_PARAMETER', 'EFFECTIVE_DATE', 'AMENDMENT', 'CLARIFICATION', 'SOURCE_REFERENCE', name='candidate_type_enum')
    candidate_type_enum.drop(op.get_bind(), checkfirst=True)
