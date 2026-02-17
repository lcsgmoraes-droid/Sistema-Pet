"""add_updated_at_to_rbac_tables

Revision ID: 6855106d3e7e
Revises: e74e03e7cf41
Create Date: 2026-01-26 21:37:42.731988

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6855106d3e7e'
down_revision: Union[str, Sequence[str], None] = 'e74e03e7cf41'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Adicionar updated_at em roles
    op.add_column('roles', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    
    # Adicionar updated_at em user_tenants
    op.add_column('user_tenants', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    
    # Adicionar updated_at em role_permissions
    op.add_column('role_permissions', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    
    print("✅ Coluna updated_at adicionada em roles, user_tenants, role_permissions")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('role_permissions', 'updated_at')
    op.drop_column('user_tenants', 'updated_at')
    op.drop_column('roles', 'updated_at')
