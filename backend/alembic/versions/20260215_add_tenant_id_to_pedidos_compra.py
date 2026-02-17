"""add_tenant_id_to_pedidos_compra

Revision ID: 20260215_add_tenant_id_to_pedidos_compra
Revises: 20260215_add_data_fechamento_comissao_to_users
Create Date: 2026-02-15 20:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '20260215_add_tenant_id_to_pedidos_compra'
down_revision: Union[str, None] = '20260215_add_entregador_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add tenant_id column to pedidos_compra table."""
    
    # Verificar se a coluna já existe
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('pedidos_compra')]
    
    if 'tenant_id' in columns:
        print("⚠️  Coluna tenant_id já existe em pedidos_compra, pulando criação")
        return
    
    print("➕ Adicionando coluna tenant_id à tabela pedidos_compra...")
    
    # Adicionar coluna como nullable temporariamente
    op.add_column(
        'pedidos_compra',
        sa.Column('tenant_id', UUID(), nullable=True)
    )
    
    # Atualizar registros existentes com primeiro tenant disponível
    print("🔄 Atualizando registros existentes...")
    connection = op.get_bind()
    
    # Buscar primeiro tenant
    result = connection.execute(sa.text("SELECT id FROM tenants LIMIT 1"))
    first_tenant = result.fetchone()
    
    if first_tenant:
        tenant_id = str(first_tenant[0])
        print(f"   Usando tenant_id: {tenant_id}")
        connection.execute(
            sa.text(f"UPDATE pedidos_compra SET tenant_id = :tenant_id WHERE tenant_id IS NULL"),
            {"tenant_id": tenant_id}
        )
        print("   ✅ Registros atualizados")
    else:
        print("   ⚠️  Nenhum tenant encontrado, mas tabela pode estar vazia")
    
    # Tornar coluna NOT NULL
    op.alter_column('pedidos_compra', 'tenant_id', nullable=False)
    print("✅ Coluna tenant_id configurada como NOT NULL")
    
    # Criar foreign key
    print("🔗 Criando foreign key...")
    op.create_foreign_key(
        'fk_pedidos_compra_tenant',
        'pedidos_compra',
        'tenants',
        ['tenant_id'],
        ['id'],
        ondelete='CASCADE'
    )
    print("✅ Foreign key criada")
    
    # Criar índice
    print("📑 Criando índice...")
    op.create_index(
        'ix_pedidos_compra_tenant_id',
        'pedidos_compra',
        ['tenant_id'],
        unique=False
    )
    print("✅ Índice criado")
    
    print("✅ Migration concluída com sucesso!")


def downgrade() -> None:
    """Remove tenant_id column from pedidos_compra table."""
    
    # Verificar se a coluna existe antes de remover
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('pedidos_compra')]
    
    if 'tenant_id' not in columns:
        print("⚠️  Coluna tenant_id não existe em pedidos_compra, pulando remoção")
        return
    
    print("🔄 Revertendo migration...")
    
    # Remover índice
    print("📑 Removendo índice...")
    try:
        op.drop_index('ix_pedidos_compra_tenant_id', table_name='pedidos_compra')
        print("✅ Índice removido")
    except Exception as e:
        print(f"⚠️  Erro ao remover índice (pode não existir): {e}")
    
    # Remover foreign key
    print("🔗 Removendo foreign key...")
    try:
        op.drop_constraint('fk_pedidos_compra_tenant', 'pedidos_compra', type_='foreignkey')
        print("✅ Foreign key removida")
    except Exception as e:
        print(f"⚠️  Erro ao remover foreign key (pode não existir): {e}")
    
    # Remover coluna
    print("➖ Removendo coluna tenant_id...")
    op.drop_column('pedidos_compra', 'tenant_id')
    print("✅ Coluna tenant_id removida")
    
    print("✅ Downgrade concluído!")
