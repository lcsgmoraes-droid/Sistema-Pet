"""Add intelligent classification fields for pet food products

Revision ID: 20260214_add_racao_ai_fields
Revises: 20260212_fix_historico_timestamps
Create Date: 2026-02-14

Adiciona campos para classificação inteligente de rações:
- porte_animal: Array de portes (Pequeno, Médio, Grande, Gigante, Todos)
- fase_publico: Array de fases (Filhote, Adulto, Senior, Gestante, Todos)
- tipo_tratamento: Array de tratamentos especiais (Obesidade, Alergia, Sensível, etc.)
- sabor_proteina: String para sabor/proteína principal (Frango, Carne, Peixe, etc.)
- auto_classificar_nome: Boolean para ativar auto-classificação via IA

Estes campos permitem:
1. Auto-classificação de produtos através de análise de nome
2. Suporte a múltiplas classificações (ex: "todas as raças")
3. Alertas de alergia no PDV
4. Análise de margem por segmento
5. Comparação de preços por linha similar
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers
revision = '20260214_add_racao_ai_fields'
down_revision = '20260212_fix_historico_timestamps'
branch_labels = None
depends_on = None


def upgrade():
    # Adicionar campo porte_animal (JSONB array)
    op.add_column(
        'produtos',
        sa.Column('porte_animal', JSONB, nullable=True, comment='Array de portes: Pequeno, Médio, Grande, Gigante, Todos')
    )
    
    # Adicionar campo fase_publico (JSONB array)
    op.add_column(
        'produtos',
        sa.Column('fase_publico', JSONB, nullable=True, comment='Array de fases: Filhote, Adulto, Senior, Gestante, Todos')
    )
    
    # Adicionar campo tipo_tratamento (JSONB array)
    op.add_column(
        'produtos',
        sa.Column('tipo_tratamento', JSONB, nullable=True, comment='Array de tratamentos: Obesidade, Alergia, Sensível, Digestivo, Urinário, etc.')
    )
    
    # Adicionar campo sabor_proteina (String)
    op.add_column(
        'produtos',
        sa.Column('sabor_proteina', sa.String(100), nullable=True, comment='Sabor/Proteína principal: Frango, Carne, Peixe, Cordeiro, etc.')
    )
    
    # Adicionar campo auto_classificar_nome (Boolean)
    op.add_column(
        'produtos',
        sa.Column('auto_classificar_nome', sa.Boolean, nullable=False, server_default='true', comment='Ativa auto-classificação via IA ao salvar')
    )
    
    # Criar índice para otimizar queries por sabor
    op.create_index(
        'ix_produtos_sabor_proteina',
        'produtos',
        ['sabor_proteina']
    )


def downgrade():
    # Remover índice
    op.drop_index('ix_produtos_sabor_proteina', 'produtos')
    
    # Remover colunas
    op.drop_column('produtos', 'auto_classificar_nome')
    op.drop_column('produtos', 'sabor_proteina')
    op.drop_column('produtos', 'tipo_tratamento')
    op.drop_column('produtos', 'fase_publico')
    op.drop_column('produtos', 'porte_animal')
