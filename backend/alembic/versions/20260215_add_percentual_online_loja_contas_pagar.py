"""add_percentual_online_loja_to_contas_pagar

Revision ID: 20260215_add_percentual_online_loja_contas_pagar
Revises: 20260215_add_instituicao_bancaria
Create Date: 2026-02-15 21:45:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '20260215_add_percentual_online_loja_contas_pagar'
down_revision = '20260215_add_instituicao_bancaria'
branch_labels = None
depends_on = None


def upgrade():
    """Adiciona colunas percentual_online e percentual_loja à tabela contas_pagar"""
    
    conn = op.get_bind()
    
    # Verificar se as colunas já existem
    result = conn.execute(text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'contas_pagar' 
        AND column_name IN ('percentual_online', 'percentual_loja')
    """))
    existing_columns = [row[0] for row in result]
    
    # Adicionar percentual_online se não existir
    if 'percentual_online' not in existing_columns:
        print("➕ Adicionando coluna percentual_online à tabela contas_pagar...")
        op.add_column('contas_pagar', 
            sa.Column('percentual_online', sa.Float(), nullable=True)
        )
        
        # Definir valor padrão para registros existentes
        conn.execute(text("""
            UPDATE contas_pagar 
            SET percentual_online = 0 
            WHERE percentual_online IS NULL
        """))
        print("✅ Coluna percentual_online adicionada")
    else:
        print("⏭️  Coluna percentual_online já existe")
    
    # Adicionar percentual_loja se não existir
    if 'percentual_loja' not in existing_columns:
        print("➕ Adicionando coluna percentual_loja à tabela contas_pagar...")
        op.add_column('contas_pagar', 
            sa.Column('percentual_loja', sa.Float(), nullable=True)
        )
        
        # Definir valor padrão para registros existentes
        conn.execute(text("""
            UPDATE contas_pagar 
            SET percentual_loja = 100 
            WHERE percentual_loja IS NULL
        """))
        print("✅ Coluna percentual_loja adicionada")
    else:
        print("⏭️  Coluna percentual_loja já existe")
    
    print("✅ Migration concluída com sucesso!")


def downgrade():
    """Remove as colunas percentual_online e percentual_loja"""
    
    conn = op.get_bind()
    
    # Verificar se as colunas existem antes de remover
    result = conn.execute(text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'contas_pagar' 
        AND column_name IN ('percentual_online', 'percentual_loja')
    """))
    existing_columns = [row[0] for row in result]
    
    if 'percentual_loja' in existing_columns:
        op.drop_column('contas_pagar', 'percentual_loja')
        print("✅ Coluna percentual_loja removida")
    
    if 'percentual_online' in existing_columns:
        op.drop_column('contas_pagar', 'percentual_online')
        print("✅ Coluna percentual_online removida")
