"""create credito_logs table

Revision ID: a9b0c1d2e3f4
Revises: f7a8b9c0d1e2
Create Date: 2026-03-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a9b0c1d2e3f4'
down_revision: Union[str, None] = 'f7a8b9c0d1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table('credito_logs'):
        op.create_table(
            'credito_logs',
            sa.Column('id', sa.Integer(), sa.Identity(always=True), primary_key=True),
            sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

            sa.Column('cliente_id', sa.Integer(), sa.ForeignKey('clientes.id', ondelete='CASCADE'), nullable=False),
            sa.Column('tipo', sa.String(length=30), nullable=False),
            sa.Column('valor', sa.Numeric(10, 2), nullable=False),
            sa.Column('saldo_anterior', sa.Numeric(10, 2), nullable=False),
            sa.Column('saldo_atual', sa.Numeric(10, 2), nullable=False),
            sa.Column('motivo', sa.Text(), nullable=True),
            sa.Column('referencia_id', sa.Integer(), nullable=True),
            sa.Column('usuario_nome', sa.String(length=255), nullable=True),
        )

    existing_indexes = {
        idx['name'] for idx in inspector.get_indexes('credito_logs')
    } if inspector.has_table('credito_logs') else set()

    if 'ix_credito_logs_tenant_id' not in existing_indexes:
        op.create_index('ix_credito_logs_tenant_id', 'credito_logs', ['tenant_id'])
    if 'ix_credito_logs_cliente_id' not in existing_indexes:
        op.create_index('ix_credito_logs_cliente_id', 'credito_logs', ['cliente_id'])
    if 'ix_credito_logs_tipo' not in existing_indexes:
        op.create_index('ix_credito_logs_tipo', 'credito_logs', ['tipo'])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table('credito_logs'):
        op.drop_table('credito_logs')
