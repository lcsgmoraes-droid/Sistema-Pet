"""add_instituicao_bancaria_to_contas_bancarias

Revision ID: 20260215_add_instituicao_bancaria
Revises: 20260215_merge_heads
Create Date: 2026-02-15 21:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '20260215_add_instituicao_bancaria'
down_revision: Union[str, None] = '20260215_merge_heads'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add instituicao_bancaria column to contas_bancarias table."""
    
    # Verificar se a coluna já existe
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('contas_bancarias')]
    
    if 'instituicao_bancaria' in columns:
        print("⚠️  Coluna instituicao_bancaria já existe em contas_bancarias, pulando criação")
        return
    
    print("➕ Adicionando coluna instituicao_bancaria à tabela contas_bancarias...")
    
    # Adicionar coluna
    op.add_column(
        'contas_bancarias',
        sa.Column('instituicao_bancaria', sa.Boolean(), nullable=False, server_default='false')
    )
    
    # Criar índice
    print("📑 Criando índice...")
    op.create_index(
        'ix_contas_bancarias_instituicao_bancaria',
        'contas_bancarias',
        ['instituicao_bancaria'],
        unique=False
    )
    print("✅ Índice criado")
    
    print("✅ Migration concluída com sucesso!")


def downgrade() -> None:
    """Remove instituicao_bancaria column from contas_bancarias table."""
    
    # Verificar se a coluna existe antes de remover
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('contas_bancarias')]
    
    if 'instituicao_bancaria' not in columns:
        print("⚠️  Coluna instituicao_bancaria não existe em contas_bancarias, pulando remoção")
        return
    
    print("🔄 Revertendo migration...")
    
    # Remover índice
    print("📑 Removendo índice...")
    try:
        op.drop_index('ix_contas_bancarias_instituicao_bancaria', table_name='contas_bancarias')
        print("✅ Índice removido")
    except Exception as e:
        print(f"⚠️  Erro ao remover índice (pode não existir): {e}")
    
    # Remover coluna
    print("➖ Removendo coluna instituicao_bancaria...")
    op.drop_column('contas_bancarias', 'instituicao_bancaria')
    print("✅ Coluna instituicao_bancaria removida")
    
    print("✅ Downgrade concluído!")
