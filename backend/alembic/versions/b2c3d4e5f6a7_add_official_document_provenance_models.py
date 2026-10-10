"""add_official_document_provenance_models

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-30 18:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Create Enums
    official_source_type_enum = postgresql.ENUM(
        'MINISTRY',
        'DEPARTMENT',
        'OFFICIAL_PORTAL',
        'GAZETTE',
        'OFFICIAL_GUIDELINE',
        'OFFICIAL_NOTIFICATION',
        'OTHER_OFFICIAL_SOURCE',
        name='official_source_type_enum',
        create_type=False,
    )
    official_source_type_enum.create(conn, checkfirst=True)

    official_document_type_enum = postgresql.ENUM(
        'GAZETTE_NOTIFICATION',
        'SCHEME_GUIDELINE',
        'OPERATIONAL_GUIDELINE',
        'FRAMEWORK',
        'MINISTRY_CIRCULAR',
        'OFFICIAL_MANUAL',
        'OFFICIAL_PORTAL_DOCUMENT',
        'OTHER_OFFICIAL_DOCUMENT',
        name='official_document_type_enum',
        create_type=False,
    )
    official_document_type_enum.create(conn, checkfirst=True)

    document_version_status_enum = postgresql.ENUM(
        'ACTIVE',
        'SUPERSEDED',
        'ARCHIVED',
        'CANDIDATE',
        name='document_version_status_enum',
        create_type=False,
    )
    document_version_status_enum.create(conn, checkfirst=True)

    provenance_completeness_enum = postgresql.ENUM(
        'COMPLETE',
        'PARTIAL',
        'UNAVAILABLE',
        'UNDER_REVIEW',
        name='provenance_completeness_enum',
        create_type=False,
    )
    provenance_completeness_enum.create(conn, checkfirst=True)

    policy_source_binding_type_enum = postgresql.ENUM(
        'PRIMARY_SOURCE',
        'SUPPLEMENTARY_SOURCE',
        'AMENDMENT',
        'CLARIFICATION',
        'IMPLEMENTATION_GUIDANCE',
        name='policy_source_binding_type_enum',
        create_type=False,
    )
    policy_source_binding_type_enum.create(conn, checkfirst=True)

    provenance_event_type_enum = postgresql.ENUM(
        'DOCUMENT_REGISTERED',
        'DOCUMENT_VERSION_ADDED',
        'DOCUMENT_SUPERSEDED',
        'POLICY_SOURCE_BOUND',
        'RULE_PROVENANCE_BOUND',
        'PROVENANCE_CORRECTED',
        'DOCUMENT_HASH_VERIFIED',
        name='provenance_event_type_enum',
        create_type=False,
    )
    provenance_event_type_enum.create(conn, checkfirst=True)

    # 2. Create official_sources table
    op.create_table(
        'official_sources',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('scheme_code', sa.String(length=64), nullable=True),
        sa.Column('publisher_name', sa.String(length=255), nullable=False),
        sa.Column(
            'publisher_type',
            postgresql.ENUM(
                'MINISTRY',
                'DEPARTMENT',
                'OFFICIAL_PORTAL',
                'GAZETTE',
                'OFFICIAL_GUIDELINE',
                'OFFICIAL_NOTIFICATION',
                'OTHER_OFFICIAL_SOURCE',
                name='official_source_type_enum',
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column('official_domain', sa.String(length=255), nullable=False),
        sa.Column('canonical_url', sa.String(length=512), nullable=False),
        sa.Column(
            'source_type',
            postgresql.ENUM(
                'MINISTRY',
                'DEPARTMENT',
                'OFFICIAL_PORTAL',
                'GAZETTE',
                'OFFICIAL_GUIDELINE',
                'OFFICIAL_NOTIFICATION',
                'OTHER_OFFICIAL_SOURCE',
                name='official_source_type_enum',
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_official_sources_scheme_code', 'official_sources', ['scheme_code'], unique=False)
    op.create_index('ix_official_sources_domain', 'official_sources', ['official_domain'], unique=False)

    # 3. Create official_documents table
    op.create_table(
        'official_documents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('official_source_id', sa.UUID(), nullable=False),
        sa.Column('scheme_code', sa.String(length=64), nullable=False),
        sa.Column('document_title', sa.String(length=255), nullable=False),
        sa.Column(
            'document_type',
            postgresql.ENUM(
                'GAZETTE_NOTIFICATION',
                'SCHEME_GUIDELINE',
                'OPERATIONAL_GUIDELINE',
                'FRAMEWORK',
                'MINISTRY_CIRCULAR',
                'OFFICIAL_MANUAL',
                'OFFICIAL_PORTAL_DOCUMENT',
                'OTHER_OFFICIAL_DOCUMENT',
                name='official_document_type_enum',
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column('issuing_authority', sa.String(length=255), nullable=False),
        sa.Column('reference_number', sa.String(length=128), nullable=True),
        sa.Column('publication_date', sa.Date(), nullable=True),
        sa.Column('effective_from', sa.Date(), nullable=True),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('official_url', sa.String(length=512), nullable=False),
        sa.Column('language', sa.String(length=16), server_default='en', nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['official_source_id'], ['official_sources.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_official_documents_scheme_code', 'official_documents', ['scheme_code'], unique=False)
    op.create_index('ix_official_documents_source_id', 'official_documents', ['official_source_id'], unique=False)

    # 4. Create official_document_versions table
    op.create_table(
        'official_document_versions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('version_label', sa.String(length=64), nullable=False),
        sa.Column('document_hash', sa.String(length=64), nullable=True),
        sa.Column('hash_algorithm', sa.String(length=32), server_default='SHA-256', nullable=False),
        sa.Column('published_at', sa.Date(), nullable=True),
        sa.Column('effective_from', sa.Date(), nullable=True),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('retrieved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('official_url', sa.String(length=512), nullable=False),
        sa.Column('content_reference', sa.String(length=512), nullable=True),
        sa.Column('byte_size', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(length=64), nullable=True),
        sa.Column('supersedes_version_id', sa.UUID(), nullable=True),
        sa.Column(
            'status',
            postgresql.ENUM(
                'ACTIVE',
                'SUPERSEDED',
                'ARCHIVED',
                'CANDIDATE',
                name='document_version_status_enum',
                create_type=False,
            ),
            server_default='ACTIVE',
            nullable=False,
        ),
        sa.Column(
            'provenance_completeness',
            postgresql.ENUM(
                'COMPLETE',
                'PARTIAL',
                'UNAVAILABLE',
                'UNDER_REVIEW',
                name='provenance_completeness_enum',
                create_type=False,
            ),
            server_default='COMPLETE',
            nullable=False,
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['official_documents.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['supersedes_version_id'], ['official_document_versions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_id', 'version_label', name='uq_doc_version_label'),
    )
    op.create_index('ix_official_doc_versions_doc_id', 'official_document_versions', ['document_id'], unique=False)
    op.create_index('ix_official_doc_versions_status', 'official_document_versions', ['status'], unique=False)

    # 5. Create policy_source_bindings table
    op.create_table(
        'policy_source_bindings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('policy_version_id', sa.UUID(), nullable=False),
        sa.Column('document_version_id', sa.UUID(), nullable=False),
        sa.Column(
            'binding_type',
            postgresql.ENUM(
                'PRIMARY_SOURCE',
                'SUPPLEMENTARY_SOURCE',
                'AMENDMENT',
                'CLARIFICATION',
                'IMPLEMENTATION_GUIDANCE',
                name='policy_source_binding_type_enum',
                create_type=False,
            ),
            server_default='PRIMARY_SOURCE',
            nullable=False,
        ),
        sa.Column('citation', sa.String(length=255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['policy_version_id'], ['policy_versions.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['document_version_id'], ['official_document_versions.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('policy_version_id', 'document_version_id', name='uq_policy_doc_binding'),
    )
    op.create_index('ix_policy_source_bindings_pv', 'policy_source_bindings', ['policy_version_id'], unique=False)
    op.create_index('ix_policy_source_bindings_dv', 'policy_source_bindings', ['document_version_id'], unique=False)

    # 6. Create rule_provenances table
    op.create_table(
        'rule_provenances',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('rule_id', sa.String(length=128), nullable=False),
        sa.Column('policy_version_id', sa.UUID(), nullable=False),
        sa.Column('document_version_id', sa.UUID(), nullable=False),
        sa.Column('citation', sa.String(length=255), nullable=True),
        sa.Column('source_locator', sa.String(length=128), nullable=True),
        sa.Column('provenance_type', sa.String(length=64), server_default='STATUTORY_RULE', nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['policy_version_id'], ['policy_versions.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['document_version_id'], ['official_document_versions.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('rule_id', 'policy_version_id', 'document_version_id', name='uq_rule_policy_doc_prov'),
    )
    op.create_index('ix_rule_prov_rule_policy', 'rule_provenances', ['rule_id', 'policy_version_id'], unique=False)
    op.create_index('ix_rule_prov_doc_ver', 'rule_provenances', ['document_version_id'], unique=False)

    # 7. Create provenance_audit_events table
    op.create_table(
        'provenance_audit_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column(
            'event_type',
            postgresql.ENUM(
                'DOCUMENT_REGISTERED',
                'DOCUMENT_VERSION_ADDED',
                'DOCUMENT_SUPERSEDED',
                'POLICY_SOURCE_BOUND',
                'RULE_PROVENANCE_BOUND',
                'PROVENANCE_CORRECTED',
                'DOCUMENT_HASH_VERIFIED',
                name='provenance_event_type_enum',
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column('entity_type', sa.String(length=64), nullable=False),
        sa.Column('entity_id', sa.String(length=64), nullable=False),
        sa.Column('actor_id', sa.String(length=128), nullable=True),
        sa.Column('actor_role', sa.String(length=64), nullable=True),
        sa.Column('previous_state', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('new_state', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_provenance_audit_events_entity_id', 'provenance_audit_events', ['entity_id'], unique=False)
    op.create_index('ix_provenance_audit_events_created_at', 'provenance_audit_events', ['created_at'], unique=False)


def downgrade() -> None:
    conn = op.get_bind()

    # Drop tables in reverse dependency order
    op.drop_index('ix_provenance_audit_events_created_at', table_name='provenance_audit_events')
    op.drop_index('ix_provenance_audit_events_entity_id', table_name='provenance_audit_events')
    op.drop_table('provenance_audit_events')

    op.drop_index('ix_rule_prov_doc_ver', table_name='rule_provenances')
    op.drop_index('ix_rule_prov_rule_policy', table_name='rule_provenances')
    op.drop_table('rule_provenances')

    op.drop_index('ix_policy_source_bindings_dv', table_name='policy_source_bindings')
    op.drop_index('ix_policy_source_bindings_pv', table_name='policy_source_bindings')
    op.drop_table('policy_source_bindings')

    op.drop_index('ix_official_doc_versions_status', table_name='official_document_versions')
    op.drop_index('ix_official_doc_versions_doc_id', table_name='official_document_versions')
    op.drop_table('official_document_versions')

    op.drop_index('ix_official_documents_source_id', table_name='official_documents')
    op.drop_index('ix_official_documents_scheme_code', table_name='official_documents')
    op.drop_table('official_documents')

    op.drop_index('ix_official_sources_domain', table_name='official_sources')
    op.drop_index('ix_official_sources_scheme_code', table_name='official_sources')
    op.drop_table('official_sources')

    # Drop enums
    for enum_name in [
        'provenance_event_type_enum',
        'policy_source_binding_type_enum',
        'provenance_completeness_enum',
        'document_version_status_enum',
        'official_document_type_enum',
        'official_source_type_enum',
    ]:
        sa_enum = postgresql.ENUM(name=enum_name)
        sa_enum.drop(conn, checkfirst=True)
