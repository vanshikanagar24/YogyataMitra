"""add_policy_authoring_models

Revision ID: 6b2e477e42cb
Revises: f8a2b3c4d5e6
Create Date: 2026-09-20 08:42:30.168807

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '6b2e477e42cb'
down_revision: Union[str, None] = 'f8a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create Enums safely with checkfirst=True
    lifecycle_enum = postgresql.ENUM(
        'DRAFT', 'AUTHORING', 'VALIDATING', 'TESTING', 'PENDING_REVIEW',
        'IN_REVIEW', 'REJECTED', 'NEEDS_CLARIFICATION', 'STAGED', 'ARCHIVED',
        name='policy_draft_lifecycle_status_enum'
    )
    lifecycle_enum.create(op.get_bind(), checkfirst=True)

    validation_enum = postgresql.ENUM(
        'NOT_VALIDATED', 'VALID', 'INVALID',
        name='policy_draft_validation_status_enum'
    )
    validation_enum.create(op.get_bind(), checkfirst=True)

    test_status_enum = postgresql.ENUM(
        'NOT_TESTED', 'PASSED', 'FAILED',
        name='policy_draft_test_status_enum'
    )
    test_status_enum.create(op.get_bind(), checkfirst=True)

    test_type_enum = postgresql.ENUM(
        'AUTO_GENERATED', 'HUMAN_AUTHORED',
        name='policy_draft_test_type_enum'
    )
    test_type_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create policy_drafts table
    op.create_table(
        'policy_drafts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('scheme_id', sa.UUID(), nullable=False),
        sa.Column('policy_title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column(
            'lifecycle_status',
            postgresql.ENUM(
                'DRAFT', 'AUTHORING', 'VALIDATING', 'TESTING', 'PENDING_REVIEW',
                'IN_REVIEW', 'REJECTED', 'NEEDS_CLARIFICATION', 'STAGED', 'ARCHIVED',
                name='policy_draft_lifecycle_status_enum',
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column('source_candidate_id', sa.UUID(), nullable=True),
        sa.Column('source_url', sa.String(length=512), nullable=True),
        sa.Column('source_title', sa.String(length=255), nullable=True),
        sa.Column('source_publisher', sa.String(length=255), nullable=True),
        sa.Column('source_document_identifier', sa.String(length=128), nullable=True),
        sa.Column('source_publication_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('source_effective_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('source_retrieved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('source_excerpt', sa.Text(), nullable=True),
        sa.Column('provenance_status', sa.String(length=64), nullable=True),
        sa.Column('adversarial_flag_detected', sa.Boolean(), nullable=False),
        sa.Column('candidate_type', sa.String(length=64), nullable=True),
        sa.Column('authored_rules_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('canonical_rules_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('rule_hash', sa.String(length=64), nullable=True),
        sa.Column('schema_version', sa.String(length=32), nullable=False),
        sa.Column('compiler_version', sa.String(length=32), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=True),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('parent_policy_version_id', sa.UUID(), nullable=True),
        sa.Column('change_summary', sa.Text(), nullable=True),
        sa.Column(
            'validation_status',
            postgresql.ENUM('NOT_VALIDATED', 'VALID', 'INVALID', name='policy_draft_validation_status_enum', create_type=False),
            nullable=False,
        ),
        sa.Column('validation_details_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            'test_status',
            postgresql.ENUM('NOT_TESTED', 'PASSED', 'FAILED', name='policy_draft_test_status_enum', create_type=False),
            nullable=False,
        ),
        sa.Column('test_summary_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('author_id', sa.String(length=255), nullable=False),
        sa.Column('author_role', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_by', sa.String(length=255), nullable=True),
        sa.Column('reviewed_by_role', sa.String(length=64), nullable=True),
        sa.Column('reviewer_reason', sa.Text(), nullable=True),
        sa.Column('staged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('staged_by', sa.String(length=255), nullable=True),
        sa.Column('staged_by_role', sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(['parent_policy_version_id'], ['policy_versions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['scheme_id'], ['schemes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_candidate_id'], ['policy_discovery_candidates.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_policy_drafts_lifecycle_status'), 'policy_drafts', ['lifecycle_status'], unique=False)
    op.create_index(op.f('ix_policy_drafts_rule_hash'), 'policy_drafts', ['rule_hash'], unique=False)
    op.create_index(op.f('ix_policy_drafts_scheme_id'), 'policy_drafts', ['scheme_id'], unique=False)
    op.create_index(op.f('ix_policy_drafts_source_candidate_id'), 'policy_drafts', ['source_candidate_id'], unique=False)

    # 3. Create policy_draft_audit_events table
    op.create_table(
        'policy_draft_audit_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('draft_id', sa.UUID(), nullable=False),
        sa.Column('actor_identity', sa.String(length=255), nullable=False),
        sa.Column('actor_role', sa.String(length=64), nullable=False),
        sa.Column('previous_status', sa.String(length=64), nullable=True),
        sa.Column('new_status', sa.String(length=64), nullable=False),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('details_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['draft_id'], ['policy_drafts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_policy_draft_audit_events_draft_id'), 'policy_draft_audit_events', ['draft_id'], unique=False)

    # 4. Create policy_draft_revisions table
    op.create_table(
        'policy_draft_revisions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('draft_id', sa.UUID(), nullable=False),
        sa.Column('revision_number', sa.Integer(), nullable=False),
        sa.Column('author_id', sa.String(length=255), nullable=False),
        sa.Column('author_role', sa.String(length=64), nullable=False),
        sa.Column('change_summary', sa.Text(), nullable=True),
        sa.Column('previous_rule_hash', sa.String(length=64), nullable=True),
        sa.Column('new_rule_hash', sa.String(length=64), nullable=True),
        sa.Column('rules_snapshot_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['draft_id'], ['policy_drafts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_policy_draft_revisions_draft_id'), 'policy_draft_revisions', ['draft_id'], unique=False)

    # 5. Create policy_draft_tests table
    op.create_table(
        'policy_draft_tests',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('draft_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column(
            'test_type',
            postgresql.ENUM('AUTO_GENERATED', 'HUMAN_AUTHORED', name='policy_draft_test_type_enum', create_type=False),
            nullable=False,
        ),
        sa.Column('facts_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('expected_result', sa.String(length=32), nullable=False),
        sa.Column('actual_result', sa.String(length=32), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('execution_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['draft_id'], ['policy_drafts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_policy_draft_tests_draft_id'), 'policy_draft_tests', ['draft_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_policy_draft_tests_draft_id'), table_name='policy_draft_tests')
    op.drop_table('policy_draft_tests')
    op.drop_index(op.f('ix_policy_draft_revisions_draft_id'), table_name='policy_draft_revisions')
    op.drop_table('policy_draft_revisions')
    op.drop_index(op.f('ix_policy_draft_audit_events_draft_id'), table_name='policy_draft_audit_events')
    op.drop_table('policy_draft_audit_events')
    op.drop_index(op.f('ix_policy_drafts_source_candidate_id'), table_name='policy_drafts')
    op.drop_index(op.f('ix_policy_drafts_scheme_id'), table_name='policy_drafts')
    op.drop_index(op.f('ix_policy_drafts_rule_hash'), table_name='policy_drafts')
    op.drop_index(op.f('ix_policy_drafts_lifecycle_status'), table_name='policy_drafts')
    op.drop_table('policy_drafts')

    # Drop enums safely with checkfirst=True
    test_type_enum = postgresql.ENUM('AUTO_GENERATED', 'HUMAN_AUTHORED', name='policy_draft_test_type_enum')
    test_type_enum.drop(op.get_bind(), checkfirst=True)

    test_status_enum = postgresql.ENUM('NOT_TESTED', 'PASSED', 'FAILED', name='policy_draft_test_status_enum')
    test_status_enum.drop(op.get_bind(), checkfirst=True)

    validation_enum = postgresql.ENUM('NOT_VALIDATED', 'VALID', 'INVALID', name='policy_draft_validation_status_enum')
    validation_enum.drop(op.get_bind(), checkfirst=True)

    lifecycle_enum = postgresql.ENUM(
        'DRAFT', 'AUTHORING', 'VALIDATING', 'TESTING', 'PENDING_REVIEW',
        'IN_REVIEW', 'REJECTED', 'NEEDS_CLARIFICATION', 'STAGED', 'ARCHIVED',
        name='policy_draft_lifecycle_status_enum'
    )
    lifecycle_enum.drop(op.get_bind(), checkfirst=True)
