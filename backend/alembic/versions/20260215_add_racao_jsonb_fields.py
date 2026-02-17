"""add_racao_jsonb_fields

Revision ID: 20260215_add_racao_jsonb_fields
Revises: 20260215_add_tenant_id_lembretes
Create Date: 2026-02-15 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = '20260215_add_racao_jsonb_fields'
down_revision: Union[str, Sequence[str], None] = '20260215_add_tenant_id_lembretes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adiciona campos JSONB de classificação IA de rações"""
    
    # Verificar se as colunas já existem antes de adicionar
    conn = op.get_bind()
    
    # porte_animal (JSONB)
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='produtos' AND column_name='porte_animal'
    """))
    if result.fetchone() is None:
        op.add_column('produtos', sa.Column('porte_animal', JSONB, nullable=True, comment='Array de portes: Pequeno, Médio, Grande, Gigante, Todos'))
        print("✅ Coluna porte_animal (JSONB) adicionada")
    else:
        print("⚠️  Coluna porte_animal já existe")
    
    # fase_publico (JSONB)
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='produtos' AND column_name='fase_publico'
    """))
    if result.fetchone() is None:
        op.add_column('produtos', sa.Column('fase_publico', JSONB, nullable=True, comment='Array de fases: Filhote, Adulto, Senior, Gestante, Todos'))
        print("✅ Coluna fase_publico (JSONB) adicionada")
    else:
        print("⚠️  Coluna fase_publico já existe")
    
    # tipo_tratamento (JSONB)
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='produtos' AND column_name='tipo_tratamento'
    """))
    if result.fetchone() is None:
        op.add_column('produtos', sa.Column('tipo_tratamento', JSONB, nullable=True, comment='Array de tratamentos: Obesidade, Alergia, Sensível, etc'))
        print("✅ Coluna tipo_tratamento (JSONB) adicionada")
    else:
        print("⚠️  Coluna tipo_tratamento já existe")
    
    # sabor_proteina (VARCHAR) - para compatibilidade com código antigo
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='produtos' AND column_name='sabor_proteina'
    """))
    if result.fetchone() is None:
        op.add_column('produtos', sa.Column('sabor_proteina', sa.String(100), nullable=True, comment='Sabor/Proteína principal'))
        # Criar índice para busca
        op.create_index('ix_produtos_sabor_proteina', 'produtos', ['sabor_proteina'], if_not_exists=True)
        print("✅ Coluna sabor_proteina (VARCHAR) adicionada")
    else:
        print("⚠️  Coluna sabor_proteina já existe")


def downgrade() -> None:
    """Remove campos JSONB de classificação IA de rações"""
    op.drop_index('ix_produtos_sabor_proteina', table_name='produtos', if_exists=True)
    op.drop_column('produtos', 'sabor_proteina', if_exists=True)
    op.drop_column('produtos', 'tipo_tratamento', if_exists=True)
    op.drop_column('produtos', 'fase_publico', if_exists=True)
    op.drop_column('produtos', 'porte_animal', if_exists=True)
