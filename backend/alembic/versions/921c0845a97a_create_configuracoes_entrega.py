"""create configuracoes_entrega

Revision ID: 921c0845a97a
Revises: dee35922f6d0
Create Date: 2026-01-31 16:25:26.739739

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '921c0845a97a'
down_revision: Union[str, Sequence[str], None] = 'dee35922f6d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Verificar se a tabela já existe
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'configuracoes_entrega' in inspector.get_table_names():
        print("⚠️  Tabela configuracoes_entrega já existe, pulando criação")
        return
    
    op.create_table(
        'configuracoes_entrega',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('entregador_padrao_id', sa.Integer(), nullable=True),  # Integer, não UUID
        sa.Column('ponto_inicial_rota', sa.String(300), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['entregador_padrao_id'], ['clientes.id'], ondelete='SET NULL')
    )
    
    # Índice único por tenant
    op.create_index(
        'idx_configuracoes_entrega_tenant_unique',
        'configuracoes_entrega',
        ['tenant_id'],
        unique=True
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_configuracoes_entrega_tenant_unique', table_name='configuracoes_entrega')
    op.drop_table('configuracoes_entrega')
