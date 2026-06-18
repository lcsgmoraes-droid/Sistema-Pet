"""add bling sync queue and retry fields

Revision ID: 7c1d2e3f4a5b
Revises: 31142854c9e6
Create Date: 2026-03-18 09:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '7c1d2e3f4a5b'
down_revision: Union[str, Sequence[str], None] = '31142854c9e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SYNC_COLUMNS = [
    ('ultima_conferencia_bling', sa.DateTime(), True, None),
    ('ultima_tentativa_sync', sa.DateTime(), True, None),
    ('proxima_tentativa_sync', sa.DateTime(), True, None),
    ('ultima_sincronizacao_sucesso', sa.DateTime(), True, None),
    ('tentativas_sync', sa.Integer(), False, '0'),
    ('ultimo_estoque_bling', sa.Float(), True, None),
    ('ultima_divergencia', sa.Float(), True, None),
]


def _add_missing_sync_columns(inspector) -> None:
    if not inspector.has_table('produto_bling_sync'):
        return

    colunas = {coluna['name'] for coluna in inspector.get_columns('produto_bling_sync')}
    for nome, tipo, nullable, default in SYNC_COLUMNS:
        if nome in colunas:
            continue

        argumentos = {}
        if default is not None:
            argumentos['server_default'] = default

        op.add_column('produto_bling_sync', sa.Column(nome, tipo, nullable=nullable, **argumentos))


def _create_queue_table_if_missing(inspector) -> None:
    if inspector.has_table('produto_bling_sync_queue'):
        return

    op.create_table(
        'produto_bling_sync_queue',
        sa.Column('id', sa.Integer(), sa.Identity(always=True), nullable=False),
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
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['produto_id'], ['produtos.id']),
        sa.ForeignKeyConstraint(['sync_id'], ['produto_bling_sync.id']),
        sa.PrimaryKeyConstraint('id')
    )


def _drop_sync_columns_if_present(inspector) -> None:
    if not inspector.has_table('produto_bling_sync'):
        return

    colunas = {coluna['name'] for coluna in inspector.get_columns('produto_bling_sync')}
    for nome, _, _, _ in reversed(SYNC_COLUMNS):
        if nome in colunas:
            op.drop_column('produto_bling_sync', nome)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    _add_missing_sync_columns(inspector)
    _create_queue_table_if_missing(inspector)

    op.execute('CREATE INDEX IF NOT EXISTS ix_produto_bling_sync_queue_produto_id ON produto_bling_sync_queue (produto_id)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_produto_bling_sync_queue_sync_id ON produto_bling_sync_queue (sync_id)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_produto_bling_sync_queue_tenant_id ON produto_bling_sync_queue (tenant_id)')


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table('produto_bling_sync_queue'):
        op.execute('DROP INDEX IF EXISTS ix_produto_bling_sync_queue_tenant_id')
        op.execute('DROP INDEX IF EXISTS ix_produto_bling_sync_queue_sync_id')
        op.execute('DROP INDEX IF EXISTS ix_produto_bling_sync_queue_produto_id')
        op.drop_table('produto_bling_sync_queue')

    _drop_sync_columns_if_present(inspector)
