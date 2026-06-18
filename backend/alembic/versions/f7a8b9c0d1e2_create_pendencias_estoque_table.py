"""create pendencias_estoque table

Revision ID: f7a8b9c0d1e2
Revises: e5f6a7b8c9d0
Create Date: 2026-03-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f7a8b9c0d1e2'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table('pendencias_estoque'):
        op.create_table(
            'pendencias_estoque',
            sa.Column('id', sa.Integer(), sa.Identity(always=True), primary_key=True),
            sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

            sa.Column('cliente_id', sa.Integer(), sa.ForeignKey('clientes.id'), nullable=False),
            sa.Column('produto_id', sa.Integer(), sa.ForeignKey('produtos.id'), nullable=False),
            sa.Column('usuario_registrou_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),

            sa.Column('quantidade_desejada', sa.Float(), nullable=False),
            sa.Column('valor_referencia', sa.Float(), nullable=True),
            sa.Column('observacoes', sa.Text(), nullable=True),
            sa.Column('status', sa.String(length=20), nullable=False, server_default='pendente'),

            sa.Column('data_notificacao', sa.DateTime(), nullable=True),
            sa.Column('whatsapp_enviado', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('mensagem_whatsapp_id', sa.String(length=100), nullable=True),

            sa.Column('data_finalizacao', sa.DateTime(), nullable=True),
            sa.Column('venda_id', sa.Integer(), sa.ForeignKey('vendas.id'), nullable=True),
            sa.Column('motivo_cancelamento', sa.Text(), nullable=True),

            sa.Column('prioridade', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('data_registro', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    existing_indexes = {idx['name'] for idx in inspector.get_indexes('pendencias_estoque')} if inspector.has_table('pendencias_estoque') else set()

    if 'ix_pendencias_estoque_tenant_id' not in existing_indexes:
        op.create_index('ix_pendencias_estoque_tenant_id', 'pendencias_estoque', ['tenant_id'])
    if 'ix_pendencias_estoque_cliente_id' not in existing_indexes:
        op.create_index('ix_pendencias_estoque_cliente_id', 'pendencias_estoque', ['cliente_id'])
    if 'ix_pendencias_estoque_produto_id' not in existing_indexes:
        op.create_index('ix_pendencias_estoque_produto_id', 'pendencias_estoque', ['produto_id'])
    if 'ix_pendencias_estoque_status' not in existing_indexes:
        op.create_index('ix_pendencias_estoque_status', 'pendencias_estoque', ['status'])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table('pendencias_estoque'):
        for index_name in [
            'ix_pendencias_estoque_status',
            'ix_pendencias_estoque_produto_id',
            'ix_pendencias_estoque_cliente_id',
            'ix_pendencias_estoque_tenant_id',
        ]:
            existing_indexes = {idx['name'] for idx in inspector.get_indexes('pendencias_estoque')}
            if index_name in existing_indexes:
                op.drop_index(index_name, table_name='pendencias_estoque')

        op.drop_table('pendencias_estoque')
