"""add bling sync queue and retry fields

Revision ID: 7c1d2e3f4a5b
Revises: 31142854c9e6
Create Date: 2026-03-18 09:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c1d2e3f4a5b'
down_revision: Union[str, Sequence[str], None] = '31142854c9e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('produto_bling_sync', sa.Column('ultima_conferencia_bling', sa.DateTime(), nullable=True))
    op.add_column('produto_bling_sync', sa.Column('ultima_tentativa_sync', sa.DateTime(), nullable=True))
    op.add_column('produto_bling_sync', sa.Column('proxima_tentativa_sync', sa.DateTime(), nullable=True))
    op.add_column('produto_bling_sync', sa.Column('ultima_sincronizacao_sucesso', sa.DateTime(), nullable=True))
    op.add_column('produto_bling_sync', sa.Column('tentativas_sync', sa.Integer(), server_default='0', nullable=False))
    op.add_column('produto_bling_sync', sa.Column('ultimo_estoque_bling', sa.Float(), nullable=True))
    op.add_column('produto_bling_sync', sa.Column('ultima_divergencia', sa.Float(), nullable=True))

    op.create_table(
        'produto_bling_sync_queue',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('produto_id', sa.Integer(), nullable=False),
        sa.Column('sync_id', sa.Integer(), nullable=False),
        sa.Column('estoque_novo', sa.Float(), nullable=False),
        sa.Column('motivo', sa.String(length=80), nullable=True),
        sa.Column('origem', sa.String(length=30), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='pendente', nullable=False),
        sa.Column('forcar_sync', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('tentativas', sa.Integer(), server_default='0', nullable=False),
        sa.Column('ultima_tentativa_em', sa.DateTime(), nullable=True),
        sa.Column('proxima_tentativa_em', sa.DateTime(), nullable=True),
        sa.Column('processado_em', sa.DateTime(), nullable=True),
        sa.Column('ultimo_erro', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['produto_id'], ['produtos.id']),
        sa.ForeignKeyConstraint(['sync_id'], ['produto_bling_sync.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_produto_bling_sync_queue_produto_id'), 'produto_bling_sync_queue', ['produto_id'], unique=False)
    op.create_index(op.f('ix_produto_bling_sync_queue_sync_id'), 'produto_bling_sync_queue', ['sync_id'], unique=False)
    op.create_index(op.f('ix_produto_bling_sync_queue_tenant_id'), 'produto_bling_sync_queue', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_produto_bling_sync_queue_tenant_id'), table_name='produto_bling_sync_queue')
    op.drop_index(op.f('ix_produto_bling_sync_queue_sync_id'), table_name='produto_bling_sync_queue')
    op.drop_index(op.f('ix_produto_bling_sync_queue_produto_id'), table_name='produto_bling_sync_queue')
    op.drop_table('produto_bling_sync_queue')

    op.drop_column('produto_bling_sync', 'ultima_divergencia')
    op.drop_column('produto_bling_sync', 'ultimo_estoque_bling')
    op.drop_column('produto_bling_sync', 'tentativas_sync')
    op.drop_column('produto_bling_sync', 'ultima_sincronizacao_sucesso')
    op.drop_column('produto_bling_sync', 'proxima_tentativa_sync')
    op.drop_column('produto_bling_sync', 'ultima_tentativa_sync')
    op.drop_column('produto_bling_sync', 'ultima_conferencia_bling')
