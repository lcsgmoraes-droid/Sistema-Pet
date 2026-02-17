"""create_permissions_and_role_permissions

Revision ID: e74e03e7cf41
Revises: 743d83c3546c
Create Date: 2026-01-26 21:24:36.336894

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e74e03e7cf41'
down_revision: Union[str, Sequence[str], None] = '743d83c3546c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Cria sistema de permissões RBAC (Role-Based Access Control).
    
    Tabelas:
    - permissions: catálogo global de permissões (codes)
    - role_permissions: vínculo role ↔ permission por tenant
    
    Exemplos de permissions:
    - vendas.criar, vendas.editar, vendas.excluir
    - produtos.visualizar, produtos.editar
    - relatorios.financeiro, relatorios.gerencial
    """
    
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # PERMISSIONS (globais - catálogo de códigos)
    if 'permissions' not in existing_tables:
        op.create_table(
            'permissions',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('code', sa.String(100), nullable=False, unique=True, index=True),
            sa.Column('description', sa.String(255), nullable=True),
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        )
        print("✅ Tabela permissions criada")
        
        # Inserir permissões básicas
        op.execute("""
            INSERT INTO permissions (code, description) VALUES
            ('vendas.criar', 'Criar vendas'),
            ('vendas.editar', 'Editar vendas'),
            ('vendas.excluir', 'Excluir vendas'),
            ('vendas.visualizar', 'Visualizar vendas'),
            ('produtos.criar', 'Criar produtos'),
            ('produtos.editar', 'Editar produtos'),
            ('produtos.excluir', 'Excluir produtos'),
            ('produtos.visualizar', 'Visualizar produtos'),
            ('clientes.criar', 'Criar clientes'),
            ('clientes.editar', 'Editar clientes'),
            ('clientes.excluir', 'Excluir clientes'),
            ('clientes.visualizar', 'Visualizar clientes'),
            ('relatorios.financeiro', 'Acessar relatórios financeiros'),
            ('relatorios.gerencial', 'Acessar relatórios gerenciais'),
            ('configuracoes.editar', 'Editar configurações do sistema'),
            ('usuarios.gerenciar', 'Gerenciar usuários e permissões')
        """)
        print("✅ Permissões básicas inseridas")
    else:
        print("ℹ️  Tabela permissions já existe")

    # ROLE ↔ PERMISSIONS (por tenant)
    if 'role_permissions' not in existing_tables:
        op.create_table(
            'role_permissions',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('tenant_id', sa.UUID, nullable=False),
            sa.Column('role_id', sa.Integer, nullable=False),
            sa.Column('permission_id', sa.Integer, nullable=False),
            sa.ForeignKeyConstraint(['role_id'], ['roles.id'], name='fk_role_permissions_role'),
            sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], name='fk_role_permissions_permission'),
        )
        
        op.create_index(
            'ix_role_permissions_tenant_role',
            'role_permissions',
            ['tenant_id', 'role_id'],
            unique=False
        )
        
        # Índice para lookup rápido de permissões
        op.create_index(
            'ix_role_permissions_tenant_role_permission',
            'role_permissions',
            ['tenant_id', 'role_id', 'permission_id'],
            unique=True
        )
        print("✅ Tabela role_permissions criada")
    else:
        print("ℹ️  Tabela role_permissions já existe")


def downgrade() -> None:
    """Remove sistema de permissões."""
    op.drop_table('role_permissions')
    op.drop_table('permissions')
    print("✅ Tabelas removidas")
