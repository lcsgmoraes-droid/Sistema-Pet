"""add tenant_id to vendas

Revision ID: cb4a6a716db2
Revises: d29b48195a64
Create Date: 2026-01-26 10:46:56.889636

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'cb4a6a716db2'
down_revision: Union[str, Sequence[str], None] = 'd29b48195a64'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # =========================
    # TABELA: vendas
    # =========================
    op.add_column(
        'vendas',
        sa.Column('tenant_id', postgresql.UUID(), nullable=True)
    )
    op.create_index('ix_vendas_tenant_id', 'vendas', ['tenant_id'])
    op.execute(
        """
        UPDATE vendas
        SET tenant_id = (
            SELECT id FROM tenants
            ORDER BY created_at
            LIMIT 1
        )
        """
    )
    op.alter_column('vendas', 'tenant_id', nullable=False)
    op.create_foreign_key(
        'fk_vendas_tenant',
        'vendas',
        'tenants',
        ['tenant_id'],
        ['id'],
        ondelete='RESTRICT'
    )

    # =========================
    # TABELA: venda_itens
    # =========================
    op.add_column(
        'venda_itens',
        sa.Column('tenant_id', postgresql.UUID(), nullable=True)
    )
    op.create_index('ix_venda_itens_tenant_id', 'venda_itens', ['tenant_id'])
    op.execute(
        """
        UPDATE venda_itens
        SET tenant_id = (
            SELECT tenant_id FROM vendas
            WHERE vendas.id = venda_itens.venda_id
        )
        """
    )
    op.alter_column('venda_itens', 'tenant_id', nullable=False)
    op.create_foreign_key(
        'fk_venda_itens_tenant',
        'venda_itens',
        'tenants',
        ['tenant_id'],
        ['id'],
        ondelete='RESTRICT'
    )

    # =========================
    # TABELA: venda_pagamentos
    # =========================
    op.add_column(
        'venda_pagamentos',
        sa.Column('tenant_id', postgresql.UUID(), nullable=True)
    )
    op.create_index(
        'ix_venda_pagamentos_tenant_id',
        'venda_pagamentos',
        ['tenant_id']
    )
    op.execute(
        """
        UPDATE venda_pagamentos
        SET tenant_id = (
            SELECT tenant_id FROM vendas
            WHERE vendas.id = venda_pagamentos.venda_id
        )
        """
    )
    op.alter_column('venda_pagamentos', 'tenant_id', nullable=False)
    op.create_foreign_key(
        'fk_venda_pagamentos_tenant',
        'venda_pagamentos',
        'tenants',
        ['tenant_id'],
        ['id'],
        ondelete='RESTRICT'
    )

    # =========================
    # TABELA: venda_baixas
    # =========================
    op.add_column(
        'venda_baixas',
        sa.Column('tenant_id', postgresql.UUID(), nullable=True)
    )
    op.create_index(
        'ix_venda_baixas_tenant_id',
        'venda_baixas',
        ['tenant_id']
    )
    op.execute(
        """
        UPDATE venda_baixas
        SET tenant_id = (
            SELECT tenant_id FROM vendas
            WHERE vendas.id = venda_baixas.venda_id
        )
        """
    )
    op.alter_column('venda_baixas', 'tenant_id', nullable=False)
    op.create_foreign_key(
        'fk_venda_baixas_tenant',
        'venda_baixas',
        'tenants',
        ['tenant_id'],
        ['id'],
        ondelete='RESTRICT'
    )

    # =========================
    # TABELA: configuracoes_entrega
    # =========================
    op.add_column(
        'configuracoes_entrega',
        sa.Column('tenant_id', postgresql.UUID(), nullable=True)
    )
    op.create_index(
        'ix_configuracoes_entrega_tenant_id',
        'configuracoes_entrega',
        ['tenant_id']
    )
    op.execute(
        """
        UPDATE configuracoes_entrega
        SET tenant_id = (
            SELECT id FROM tenants
            ORDER BY created_at
            LIMIT 1
        )
        """
    )
    op.alter_column(
        'configuracoes_entrega',
        'tenant_id',
        nullable=False
    )
    op.create_foreign_key(
        'fk_configuracoes_entrega_tenant',
        'configuracoes_entrega',
        'tenants',
        ['tenant_id'],
        ['id'],
        ondelete='RESTRICT'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_configuracoes_entrega_tenant', 'configuracoes_entrega', type_='foreignkey')
    op.drop_index('ix_configuracoes_entrega_tenant_id', table_name='configuracoes_entrega')
    op.drop_column('configuracoes_entrega', 'tenant_id')

    op.drop_constraint('fk_venda_baixas_tenant', 'venda_baixas', type_='foreignkey')
    op.drop_index('ix_venda_baixas_tenant_id', table_name='venda_baixas')
    op.drop_column('venda_baixas', 'tenant_id')

    op.drop_constraint('fk_venda_pagamentos_tenant', 'venda_pagamentos', type_='foreignkey')
    op.drop_index('ix_venda_pagamentos_tenant_id', table_name='venda_pagamentos')
    op.drop_column('venda_pagamentos', 'tenant_id')

    op.drop_constraint('fk_venda_itens_tenant', 'venda_itens', type_='foreignkey')
    op.drop_index('ix_venda_itens_tenant_id', table_name='venda_itens')
    op.drop_column('venda_itens', 'tenant_id')

    op.drop_constraint('fk_vendas_tenant', 'vendas', type_='foreignkey')
    op.drop_index('ix_vendas_tenant_id', table_name='vendas')
    op.drop_column('vendas', 'tenant_id')
