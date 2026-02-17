"""create_pendencias_estoque_table

Revision ID: 20260215_create_pendencias_estoque
Revises: 20260215_add_opcoes_racao_tables
Create Date: 2026-02-15 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '20260215_create_pendencias_estoque'
down_revision: Union[str, Sequence[str], None] = '20260215_add_opcoes_racao_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create pendencias_estoque table."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if 'pendencias_estoque' in inspector.get_table_names():
        print("⚠️  Tabela pendencias_estoque já existe, pulando criação")
        return

    op.create_table(
        'pendencias_estoque',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('cliente_id', sa.Integer(), nullable=False),
        sa.Column('produto_id', sa.Integer(), nullable=False),
        sa.Column('usuario_registrou_id', sa.Integer(), nullable=False),
        sa.Column('quantidade_desejada', sa.Float(), nullable=False),
        sa.Column('valor_referencia', sa.Float(), nullable=True),
        sa.Column('observacoes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pendente'),
        sa.Column('data_notificacao', sa.DateTime(), nullable=True),
        sa.Column('whatsapp_enviado', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('mensagem_whatsapp_id', sa.String(length=100), nullable=True),
        sa.Column('data_finalizacao', sa.DateTime(), nullable=True),
        sa.Column('venda_id', sa.Integer(), nullable=True),
        sa.Column('motivo_cancelamento', sa.Text(), nullable=True),
        sa.Column('prioridade', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('data_registro', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['cliente_id'], ['clientes.id']),
        sa.ForeignKeyConstraint(['produto_id'], ['produtos.id']),
        sa.ForeignKeyConstraint(['usuario_registrou_id'], ['users.id']),
        sa.ForeignKeyConstraint(['venda_id'], ['vendas.id']),
    )

    op.create_index('ix_pendencias_estoque_tenant_id', 'pendencias_estoque', ['tenant_id'], if_not_exists=True)
    op.create_index('ix_pendencias_estoque_cliente_id', 'pendencias_estoque', ['cliente_id'], if_not_exists=True)
    op.create_index('ix_pendencias_estoque_produto_id', 'pendencias_estoque', ['produto_id'], if_not_exists=True)
    op.create_index('ix_pendencias_estoque_status', 'pendencias_estoque', ['status'], if_not_exists=True)
    op.create_index('ix_pendencias_estoque_data_registro', 'pendencias_estoque', ['data_registro'], if_not_exists=True)


def downgrade() -> None:
    """Drop pendencias_estoque table."""
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if 'pendencias_estoque' not in inspector.get_table_names():
        return

    op.drop_index('ix_pendencias_estoque_data_registro', table_name='pendencias_estoque', if_exists=True)
    op.drop_index('ix_pendencias_estoque_status', table_name='pendencias_estoque', if_exists=True)
    op.drop_index('ix_pendencias_estoque_produto_id', table_name='pendencias_estoque', if_exists=True)
    op.drop_index('ix_pendencias_estoque_cliente_id', table_name='pendencias_estoque', if_exists=True)
    op.drop_index('ix_pendencias_estoque_tenant_id', table_name='pendencias_estoque', if_exists=True)
    op.drop_table('pendencias_estoque')
