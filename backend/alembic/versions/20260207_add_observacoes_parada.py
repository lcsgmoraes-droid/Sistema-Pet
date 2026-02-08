"""Add observacoes to rotas_entrega_paradas

Revision ID: 20260207_add_observacoes
Revises: 
Create Date: 2026-02-07

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '20260207_add_observacoes'
down_revision = None  # Será preenchido automaticamente
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('rotas_entrega_paradas', 
        sa.Column('observacoes', sa.Text(), nullable=True)
    )


def downgrade():
    op.drop_column('rotas_entrega_paradas', 'observacoes')
