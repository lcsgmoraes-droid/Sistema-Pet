"""Adiciona campo status_conciliacao a venda_pagamentos

Revision ID: add_status_conciliacao_vpag
Revises: add_unique_nsu_operadora
Create Date: 2026-02-12 00:00:00.000000

Adiciona campo status_conciliacao para controlar visibilidade
dos lançamentos na tela de conciliação.

Valores possíveis:
- 'nao_conciliado': Lançamento pendente de conciliação (padrão)
- 'conciliado': Lançamento já conciliado e confirmado

A conciliação agora depende do status, não da presença de NSU.
Vendas podem ter NSU mas ainda estar não conciliadas.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_status_conciliacao_vpag'
down_revision = '20260211_create_operadoras'
branch_labels = None
depends_on = None


def upgrade():
    """
    Adiciona coluna status_conciliacao à tabela venda_pagamentos.
    
    Todas as vendas existentes serão marcadas como 'nao_conciliado'.
    """
    
    # 1. Criar tipo ENUM
    op.execute("""
        CREATE TYPE status_conciliacao_enum AS ENUM ('nao_conciliado', 'conciliado');
    """)
    
    # 2. Adicionar coluna
    op.add_column(
        'venda_pagamentos',
        sa.Column(
            'status_conciliacao',
            sa.Enum('nao_conciliado', 'conciliado', name='status_conciliacao_enum'),
            nullable=False,
            server_default='nao_conciliado'
        )
    )
    
    # 3. Criar índice para performance nas consultas
    op.create_index(
        'idx_venda_pagamentos_status_conciliacao',
        'venda_pagamentos',
        ['tenant_id', 'status_conciliacao', 'operadora_id'],
        unique=False
    )
    
    print("✅ Campo status_conciliacao adicionado com sucesso!")
    print("   Todas as vendas existentes: status = 'nao_conciliado'")


def downgrade():
    """
    Remove coluna status_conciliacao e tipo ENUM.
    """
    
    # 1. Remover índice
    op.drop_index('idx_venda_pagamentos_status_conciliacao', table_name='venda_pagamentos')
    
    # 2. Remover coluna
    op.drop_column('venda_pagamentos', 'status_conciliacao')
    
    # 3. Remover tipo ENUM
    op.execute("DROP TYPE status_conciliacao_enum;")
    
    print("⚠️  Campo status_conciliacao removido")
