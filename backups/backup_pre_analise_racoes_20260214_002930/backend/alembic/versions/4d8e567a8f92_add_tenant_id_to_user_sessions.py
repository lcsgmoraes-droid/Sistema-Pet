"""add_tenant_id_to_user_sessions

Revision ID: 4d8e567a8f92
Revises: 3c7c456bf7a1
Create Date: 2026-01-26 22:57:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '4d8e567a8f92'
down_revision = '3c7c456bf7a1'
branch_labels = None
depends_on = None


def upgrade():
    # Add tenant_id column to user_sessions
    op.add_column('user_sessions', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f('ix_user_sessions_tenant_id'), 'user_sessions', ['tenant_id'], unique=False)
    op.create_foreign_key('fk_user_sessions_tenant_id', 'user_sessions', 'tenants', ['tenant_id'], ['id'])


def downgrade():
    op.drop_constraint('fk_user_sessions_tenant_id', 'user_sessions', type_='foreignkey')
    op.drop_index(op.f('ix_user_sessions_tenant_id'), table_name='user_sessions')
    op.drop_column('user_sessions', 'tenant_id')
