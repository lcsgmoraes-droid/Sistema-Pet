"""create_users_roles_user_tenants

Revision ID: 743d83c3546c
Revises: 643784162d15
Create Date: 2026-01-26 21:21:37.931883

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '743d83c3546c'
down_revision: Union[str, Sequence[str], None] = '643784162d15'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Cria estrutura multi-empresa para usuários.
    
    Tabelas:
    - users: usuários globais (email único)
    - roles: papéis por tenant (admin, operator, viewer)
    - user_tenants: vínculo user ↔ tenant com role
    
    Um usuário pode estar em múltiplos tenants com roles diferentes.
    """
    
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # USERS (globais) - verificar se já existe
    if 'users' not in existing_tables:
        op.create_table(
            'users',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('email', sa.String(255), nullable=False, unique=True),
            sa.Column('password_hash', sa.String(255), nullable=False),
            sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.true()),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        )
        print("✅ Tabela users criada")
    else:
        print("ℹ️  Tabela users já existe")

    # ROLES (por tenant)
    if 'roles' not in existing_tables:
        op.create_table(
            'roles',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('tenant_id', sa.UUID, nullable=False),
            sa.Column('name', sa.String(50), nullable=False),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        )
        
        op.create_index(
            'ix_roles_tenant_name',
            'roles',
            ['tenant_id', 'name'],
            unique=True
        )
        print("✅ Tabela roles criada")
    else:
        print("ℹ️  Tabela roles já existe")

    # USER ↔ TENANT (vínculo)
    if 'user_tenants' not in existing_tables:
        op.create_table(
            'user_tenants',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('user_id', sa.Integer, nullable=False),
            sa.Column('tenant_id', sa.UUID, nullable=False),
            sa.Column('role_id', sa.Integer, nullable=False),
            sa.Column('is_active', sa.Boolean, nullable=False, server_default=sa.true()),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_user_tenants_user'),
            sa.ForeignKeyConstraint(['role_id'], ['roles.id'], name='fk_user_tenants_role'),
        )
        
        op.create_index(
            'ix_user_tenants_user_tenant',
            'user_tenants',
            ['user_id', 'tenant_id'],
            unique=True
        )
        print("✅ Tabela user_tenants criada")
    else:
        print("ℹ️  Tabela user_tenants já existe")


def downgrade() -> None:
    """Remove estrutura multi-empresa."""
    op.drop_table('user_tenants')
    op.drop_table('roles')
    op.drop_table('users')
    print("✅ Tabelas removidas")
