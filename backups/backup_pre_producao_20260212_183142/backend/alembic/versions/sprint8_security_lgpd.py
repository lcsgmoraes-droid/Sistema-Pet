"""Sprint 8: Security and LGPD tables

Revision ID: sprint8_security_lgpd
Revises: 88069ece4849
Create Date: 2026-02-01 23:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'sprint8_security_lgpd'
down_revision: Union[str, None] = '88069ece4849'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Create LGPD and Security tables."""
    
    # ============================================================================
    # 1. LGPD: Data Privacy Consent
    # ============================================================================
    op.create_table(
        'data_privacy_consents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subject_type', sa.String(length=50), nullable=False, comment='customer, employee, user'),
        sa.Column('subject_id', sa.String(length=255), nullable=False, comment='ID do titular'),
        sa.Column('consent_type', sa.String(length=100), nullable=False, comment='whatsapp, email, sms, etc'),
        sa.Column('consent_given', sa.Boolean(), nullable=False),
        sa.Column('consent_text', sa.Text(), nullable=False, comment='Texto exato aceito'),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('phone_number', sa.String(length=20), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('revoke_reason', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_consent_tenant_subject', 'data_privacy_consents', ['tenant_id', 'subject_id', 'consent_type'])
    op.create_index('ix_consent_type', 'data_privacy_consents', ['consent_type'])
    
    # ============================================================================
    # 2. LGPD: Data Access Log
    # ============================================================================
    op.create_table(
        'data_access_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subject_type', sa.String(length=50), nullable=False),
        sa.Column('subject_id', sa.String(length=255), nullable=False),
        sa.Column('accessed_by_user_id', sa.Integer(), nullable=True),
        sa.Column('access_type', sa.String(length=50), nullable=False, comment='read, write, delete, export'),
        sa.Column('resource_type', sa.String(length=100), nullable=False, comment='customer, order, message, etc'),
        sa.Column('resource_id', sa.String(length=255), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('justification', sa.Text(), nullable=True, comment='Justificativa de acesso'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['accessed_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_access_log_tenant_time', 'data_access_logs', ['tenant_id', 'created_at'])
    op.create_index('ix_access_log_subject', 'data_access_logs', ['subject_id', 'subject_type'])
    
    # ============================================================================
    # 3. LGPD: Data Deletion Requests
    # ============================================================================
    op.create_table(
        'data_deletion_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subject_type', sa.String(length=50), nullable=False),
        sa.Column('subject_id', sa.String(length=255), nullable=False),
        sa.Column('request_date', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending', comment='pending, approved, rejected, completed'),
        sa.Column('processed_by_user_id', sa.Integer(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('contact_phone', sa.String(length=20), nullable=True),
        sa.Column('contact_email', sa.String(length=255), nullable=True),
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='JSON metadata'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['processed_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_deletion_tenant_status', 'data_deletion_requests', ['tenant_id', 'status'])
    op.create_index('ix_deletion_subject', 'data_deletion_requests', ['subject_id', 'subject_type'])
    
    # ============================================================================
    # 4. Security: Security Audit Log
    # ============================================================================
    op.create_table(
        'security_audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False, comment='login, logout, data_access, etc'),
        sa.Column('severity', sa.String(length=20), nullable=False, comment='info, warning, error, critical'),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('resource_type', sa.String(length=100), nullable=True),
        sa.Column('resource_id', sa.String(length=255), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('extra_data', sa.Text(), nullable=True, comment='JSON adicional'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_tenant_time', 'security_audit_logs', ['tenant_id', 'created_at'])
    op.create_index('ix_audit_event_type', 'security_audit_logs', ['event_type'])
    op.create_index('ix_audit_severity', 'security_audit_logs', ['severity'])


def downgrade() -> None:
    """Downgrade schema - Remove LGPD and Security tables."""
    
    # Drop indexes first
    op.drop_index('ix_audit_severity', 'security_audit_logs')
    op.drop_index('ix_audit_event_type', 'security_audit_logs')
    op.drop_index('ix_audit_tenant_time', 'security_audit_logs')
    op.drop_table('security_audit_logs')
    
    op.drop_index('ix_deletion_subject', 'data_deletion_requests')
    op.drop_index('ix_deletion_tenant_status', 'data_deletion_requests')
    op.drop_table('data_deletion_requests')
    
    op.drop_index('ix_access_log_subject', 'data_access_logs')
    op.drop_index('ix_access_log_tenant_time', 'data_access_logs')
    op.drop_table('data_access_logs')
    
    op.drop_index('ix_consent_type', 'data_privacy_consents')
    op.drop_index('ix_consent_tenant_subject', 'data_privacy_consents')
    op.drop_table('data_privacy_consents')
