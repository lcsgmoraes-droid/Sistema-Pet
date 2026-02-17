"""add updated_at to venda_itens

Revision ID: 20260126_venda_itens_updated_at
Revises: 20260126_fix_seq
Create Date: 2026-01-26 15:20:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260126_venda_itens_updated_at'
down_revision = '20260126_fix_seq'
branch_labels = None
depends_on = None


def upgrade():
    """
    Adiciona coluna updated_at à tabela venda_itens
    """
    op.add_column('venda_itens', 
        sa.Column('updated_at', sa.DateTime(timezone=True), 
                  server_default=sa.text('now()'), nullable=False)
    )


def downgrade():
    """
    Remove coluna updated_at da tabela venda_itens
    """
    op.drop_column('venda_itens', 'updated_at')
