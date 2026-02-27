"""ecommerce config fields and notify requests table

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-03-01

"""
from typing import Union, Sequence

# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    # --- Colunas de configuração da loja no tenant ---
    op.add_column('tenants', sa.Column('ecommerce_ativo', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('tenants', sa.Column('ecommerce_descricao', sa.Text(), nullable=True))
    op.add_column('tenants', sa.Column('ecommerce_horario_abertura', sa.String(5), nullable=True))
    op.add_column('tenants', sa.Column('ecommerce_horario_fechamento', sa.String(5), nullable=True))
    op.add_column('tenants', sa.Column('ecommerce_dias_funcionamento', sa.String(200), nullable=True))

    # --- Tabela de solicitações "Avise-me quando chegar" ---
    op.create_table(
        'ecommerce_notify_requests',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.String(36), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('product_name', sa.String(255), nullable=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('notified', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('notified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_ecommerce_notify_requests_tenant_id', 'ecommerce_notify_requests', ['tenant_id'])
    op.create_index('ix_ecommerce_notify_requests_product_id', 'ecommerce_notify_requests', ['product_id'])


def downgrade() -> None:
    op.drop_index('ix_ecommerce_notify_requests_product_id', table_name='ecommerce_notify_requests')
    op.drop_index('ix_ecommerce_notify_requests_tenant_id', table_name='ecommerce_notify_requests')
    op.drop_table('ecommerce_notify_requests')

    op.drop_column('tenants', 'ecommerce_dias_funcionamento')
    op.drop_column('tenants', 'ecommerce_horario_fechamento')
    op.drop_column('tenants', 'ecommerce_horario_abertura')
    op.drop_column('tenants', 'ecommerce_descricao')
    op.drop_column('tenants', 'ecommerce_ativo')
