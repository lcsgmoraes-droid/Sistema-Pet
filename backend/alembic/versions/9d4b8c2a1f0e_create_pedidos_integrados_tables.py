"""create pedidos integrados tables

Revision ID: 9d4b8c2a1f0e
Revises: 7c1d2e3f4a5b
Create Date: 2026-03-18 10:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '9d4b8c2a1f0e'
down_revision: Union[str, Sequence[str], None] = '7c1d2e3f4a5b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


NOW_SQL = 'now()'


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table('pedidos_integrados'):
        op.create_table(
            'pedidos_integrados',
            sa.Column('pedido_bling_id', sa.String(length=50), nullable=False),
            sa.Column('pedido_bling_numero', sa.String(length=50), nullable=True),
            sa.Column('canal', sa.String(length=50), nullable=False),
            sa.Column('status', sa.String(length=30), server_default='aberto', nullable=False),
            sa.Column('criado_em', sa.DateTime(), nullable=True),
            sa.Column('expira_em', sa.DateTime(), nullable=False),
            sa.Column('confirmado_em', sa.DateTime(), nullable=True),
            sa.Column('cancelado_em', sa.DateTime(), nullable=True),
            sa.Column('payload', sa.JSON(), nullable=False),
            sa.Column('id', sa.Integer(), sa.Identity(always=True), nullable=False),
            sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text(NOW_SQL), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text(NOW_SQL), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )

    if not inspector.has_table('pedidos_integrados_itens'):
        op.create_table(
            'pedidos_integrados_itens',
            sa.Column('pedido_integrado_id', sa.Integer(), nullable=False),
            sa.Column('sku', sa.String(length=100), nullable=False),
            sa.Column('descricao', sa.String(length=255), nullable=True),
            sa.Column('quantidade', sa.Integer(), nullable=False),
            sa.Column('reservado_em', sa.DateTime(), nullable=True),
            sa.Column('liberado_em', sa.DateTime(), nullable=True),
            sa.Column('vendido_em', sa.DateTime(), nullable=True),
            sa.Column('id', sa.Integer(), sa.Identity(always=True), nullable=False),
            sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text(NOW_SQL), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text(NOW_SQL), nullable=False),
            sa.ForeignKeyConstraint(['pedido_integrado_id'], ['pedidos_integrados.id']),
            sa.PrimaryKeyConstraint('id')
        )

    op.execute('CREATE INDEX IF NOT EXISTS ix_pedidos_integrados_tenant_id ON pedidos_integrados (tenant_id)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_pedidos_integrados_pedido_bling_id ON pedidos_integrados (pedido_bling_id)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_pedidos_integrados_status ON pedidos_integrados (status)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_pedidos_integrados_expira_em ON pedidos_integrados (expira_em)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_pedidos_integrados_itens_tenant_id ON pedidos_integrados_itens (tenant_id)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_pedidos_integrados_itens_pedido_integrado_id ON pedidos_integrados_itens (pedido_integrado_id)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_pedidos_integrados_itens_sku ON pedidos_integrados_itens (sku)')


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table('pedidos_integrados_itens'):
        op.execute('DROP INDEX IF EXISTS ix_pedidos_integrados_itens_sku')
        op.execute('DROP INDEX IF EXISTS ix_pedidos_integrados_itens_pedido_integrado_id')
        op.execute('DROP INDEX IF EXISTS ix_pedidos_integrados_itens_tenant_id')
        op.drop_table('pedidos_integrados_itens')

    if inspector.has_table('pedidos_integrados'):
        op.execute('DROP INDEX IF EXISTS ix_pedidos_integrados_expira_em')
        op.execute('DROP INDEX IF EXISTS ix_pedidos_integrados_status')
        op.execute('DROP INDEX IF EXISTS ix_pedidos_integrados_pedido_bling_id')
        op.execute('DROP INDEX IF EXISTS ix_pedidos_integrados_tenant_id')
        op.drop_table('pedidos_integrados')