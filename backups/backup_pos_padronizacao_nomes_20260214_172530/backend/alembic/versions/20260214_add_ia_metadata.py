"""add_ia_metadata_fields

Revision ID: 20260214_ia_metadata
Revises: 20260214_opcoes_racao
Create Date: 2026-02-14 04:30:00.000000

Adiciona campos de metadados para auditoria e controle da classificação IA:
- classificacao_ia_versao: Versão do algoritmo que classificou
- classificacao_origem: Origem de cada campo (IA vs MANUAL)
- peso_embalagem: Peso oficial da embalagem (numérico)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260214_ia_metadata'
down_revision = '20260214_opcoes_racao'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Versão do algoritmo de classificação
    op.add_column(
        'produtos',
        sa.Column('classificacao_ia_versao', sa.String(20), nullable=True, comment='Versão da IA que classificou (ex: v1.0.0)')
    )
    
    # 2. Origem de cada campo (IA ou MANUAL)
    op.add_column(
        'produtos',
        sa.Column(
            'classificacao_origem',
            postgresql.JSONB,
            nullable=True,
            comment='Origem de cada campo classificado: {"porte_animal": "IA", "sabor_proteina": "MANUAL"}'
        )
    )
    
    # 3. Peso oficial da embalagem (numérico para cálculos)
    # Nota: Este campo pode já existir em alguns ambientes, então verificamos primeiro
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'produtos' AND column_name = 'peso_embalagem'
            ) THEN
                ALTER TABLE produtos ADD COLUMN peso_embalagem NUMERIC(10,3);
            END IF;
        END $$;
    """)
    
    # Adicionar comentário ao campo peso_embalagem
    op.execute("""
        COMMENT ON COLUMN produtos.peso_embalagem IS 'Peso da embalagem em kg (usado para cálculo de preço/kg)';
    """)
    
    # Criar índice para consultas por versão (útil para migração de dados)
    op.create_index(
        'ix_produtos_classificacao_ia_versao',
        'produtos',
        ['classificacao_ia_versao'],
        postgresql_where=sa.text('classificacao_ia_versao IS NOT NULL')
    )


def downgrade():
    op.drop_index('ix_produtos_classificacao_ia_versao', table_name='produtos')
    
    # Nota: Não removemos peso_embalagem pois pode ter sido criado anteriormente
    # op.drop_column('produtos', 'peso_embalagem')
    
    op.drop_column('produtos', 'classificacao_origem')
    op.drop_column('produtos', 'classificacao_ia_versao')
