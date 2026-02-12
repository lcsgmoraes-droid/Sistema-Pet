"""Adiciona constraint unique para NSU por operadora

Revision ID: add_unique_nsu_operadora
Revises: 
Create Date: 2026-02-11 21:00:00.000000

Previne NSUs duplicados na mesma operadora.
Permite NSU repetido se for de operadoras diferentes.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_unique_nsu_operadora'
down_revision = None  # Ajustar para última migration
branch_labels = None
depends_on = None


def upgrade():
    """
    Adiciona constraint UNIQUE composta:
    - tenant_id + nsu_cartao + operadora_id
    
    Permite que o mesmo NSU exista apenas uma vez por operadora.
    """
    
    # 1. Primeiro, limpar NSUs duplicados existentes (se houver)
    op.execute("""
        -- Identificar e limpar duplicatas mantendo apenas a primeira ocorrência
        WITH duplicatas AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY tenant_id, nsu_cartao, operadora_id 
                       ORDER BY id
                   ) as row_num
            FROM venda_pagamentos
            WHERE nsu_cartao IS NOT NULL
              AND operadora_id IS NOT NULL
        )
        UPDATE venda_pagamentos
        SET nsu_cartao = NULL
        WHERE id IN (
            SELECT id FROM duplicatas WHERE row_num > 1
        );
    """)
    
    # 2. Criar índice único parcial (ignora NULLs)
    op.create_index(
        'idx_unique_nsu_por_operadora',
        'venda_pagamentos',
        ['tenant_id', 'nsu_cartao', 'operadora_id'],
        unique=True,
        postgresql_where=sa.text('nsu_cartao IS NOT NULL AND operadora_id IS NOT NULL')
    )


def downgrade():
    """Remove constraint"""
    op.drop_index('idx_unique_nsu_por_operadora', table_name='venda_pagamentos')
