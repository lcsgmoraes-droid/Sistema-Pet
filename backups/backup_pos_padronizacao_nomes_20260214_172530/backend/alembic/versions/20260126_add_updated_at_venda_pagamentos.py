"""add updated_at to venda_pagamentos

Revision ID: 20260126_venda_pagamentos_updated_at
Revises: 20260126_venda_itens_updated_at
Create Date: 2026-01-26 15:25:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260126_vpag_upd'
down_revision = '20260126_venda_itens_updated_at'
branch_labels = None
depends_on = None


def upgrade():
    """
    Adiciona coluna updated_at à tabela venda_pagamentos
    """
    op.add_column('venda_pagamentos', 
        sa.Column('updated_at', sa.DateTime(timezone=True), 
                  server_default=sa.text('now()'), nullable=False)
    )


def downgrade():
    """
    Remove coluna updated_at da tabela venda_pagamentos
    """
    op.drop_column('venda_pagamentos', 'updated_at')
