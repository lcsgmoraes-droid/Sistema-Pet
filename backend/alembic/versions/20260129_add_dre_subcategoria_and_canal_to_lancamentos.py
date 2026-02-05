"""add dre_subcategoria_id and canal to lancamentos

Revision ID: 20260129_dre_lancamentos
Revises: 20260129_dre_plano_contas
Create Date: 2026-01-29 14:00:00.000000

OBJETIVO:
Adicionar campos dre_subcategoria_id e canal às tabelas de lançamentos financeiros
para suportar a integração em tempo real com DRE.

ESTRATÉGIA DE SEGURANÇA:
- Campos NULLABLE (não quebra dados existentes)
- Sem ForeignKey física (multi-tenant por tenant_id)
- Sem Enum (String simples para canal)
- Índices para performance

TABELAS IMPACTADAS:
- contas_pagar
- contas_receber
- vendas (se necessário futuramente)
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260129_dre_lancamentos'
down_revision: Union[str, Sequence[str], None] = '20260129_dre_plano_contas'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Adiciona campos de integração DRE aos lançamentos financeiros.
    
    IMPORTANTE:
    - Campos NULLABLE para não quebrar dados existentes
    - Aplicação deve validar campos em novas criações
    - Migração de dados (backfill) deve ser feita separadamente
    """
    
    # ============================================
    # CONTAS A PAGAR
    # ============================================
    
    # Campo dre_subcategoria_id
    op.add_column(
        'contas_pagar',
        sa.Column(
            'dre_subcategoria_id',
            sa.Integer(),
            nullable=True,  # NULLABLE: não quebra dados existentes
            comment='ID da subcategoria DRE (fonte da verdade contábil)'
        )
    )
    
    # Campo canal
    op.add_column(
        'contas_pagar',
        sa.Column(
            'canal',
            sa.String(length=50),
            nullable=True,  # NULLABLE: não quebra dados existentes
            comment='Canal de vendas: loja_fisica, mercado_livre, etc'
        )
    )
    
    # Índices para performance
    op.create_index(
        'ix_contas_pagar_dre_subcategoria_id',
        'contas_pagar',
        ['dre_subcategoria_id'],
        unique=False
    )
    
    op.create_index(
        'ix_contas_pagar_canal',
        'contas_pagar',
        ['canal'],
        unique=False
    )
    
    # Índice composto para queries multi-tenant
    op.create_index(
        'ix_contas_pagar_tenant_dre_canal',
        'contas_pagar',
        ['tenant_id', 'dre_subcategoria_id', 'canal'],
        unique=False
    )
    
    # ============================================
    # CONTAS A RECEBER
    # ============================================
    
    # Campo dre_subcategoria_id
    op.add_column(
        'contas_receber',
        sa.Column(
            'dre_subcategoria_id',
            sa.Integer(),
            nullable=True,  # NULLABLE: não quebra dados existentes
            comment='ID da subcategoria DRE (fonte da verdade contábil)'
        )
    )
    
    # Campo canal
    op.add_column(
        'contas_receber',
        sa.Column(
            'canal',
            sa.String(length=50),
            nullable=True,  # NULLABLE: não quebra dados existentes
            comment='Canal de vendas: loja_fisica, mercado_livre, etc'
        )
    )
    
    # Índices para performance
    op.create_index(
        'ix_contas_receber_dre_subcategoria_id',
        'contas_receber',
        ['dre_subcategoria_id'],
        unique=False
    )
    
    op.create_index(
        'ix_contas_receber_canal',
        'contas_receber',
        ['canal'],
        unique=False
    )
    
    # Índice composto para queries multi-tenant
    op.create_index(
        'ix_contas_receber_tenant_dre_canal',
        'contas_receber',
        ['tenant_id', 'dre_subcategoria_id', 'canal'],
        unique=False
    )


def downgrade() -> None:
    """
    Remove campos de integração DRE (rollback seguro).
    """
    
    # ============================================
    # CONTAS A RECEBER - ROLLBACK
    # ============================================
    
    # Remove índices
    op.drop_index('ix_contas_receber_tenant_dre_canal', table_name='contas_receber')
    op.drop_index('ix_contas_receber_canal', table_name='contas_receber')
    op.drop_index('ix_contas_receber_dre_subcategoria_id', table_name='contas_receber')
    
    # Remove colunas
    op.drop_column('contas_receber', 'canal')
    op.drop_column('contas_receber', 'dre_subcategoria_id')
    
    # ============================================
    # CONTAS A PAGAR - ROLLBACK
    # ============================================
    
    # Remove índices
    op.drop_index('ix_contas_pagar_tenant_dre_canal', table_name='contas_pagar')
    op.drop_index('ix_contas_pagar_canal', table_name='contas_pagar')
    op.drop_index('ix_contas_pagar_dre_subcategoria_id', table_name='contas_pagar')
    
    # Remove colunas
    op.drop_column('contas_pagar', 'canal')
    op.drop_column('contas_pagar', 'dre_subcategoria_id')
