"""add tenant_id to estoque

Revision ID: d29b48195a64
Revises: 0853358c4a74
Create Date: 2026-01-26 10:05:49.191467

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd29b48195a64'
down_revision: Union[str, Sequence[str], None] = '0853358c4a74'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ===== PRODUTO_LOTES =====
    op.add_column(
        'produto_lotes',
        sa.Column('tenant_id', postgresql.UUID(), nullable=True)
    )

    op.create_index(
        'ix_produto_lotes_tenant_id',
        'produto_lotes',
        ['tenant_id']
    )

    op.execute(
        """
        UPDATE produto_lotes
        SET tenant_id = (
            SELECT id FROM tenants
            ORDER BY created_at
            LIMIT 1
        )
        """
    )

    op.alter_column(
        'produto_lotes',
        'tenant_id',
        nullable=False
    )

    op.create_foreign_key(
        'fk_produto_lotes_tenant',
        'produto_lotes',
        'tenants',
        ['tenant_id'],
        ['id'],
        ondelete='RESTRICT'
    )

    # ===== ESTOQUE_MOVIMENTACOES =====
    op.add_column(
        'estoque_movimentacoes',
        sa.Column('tenant_id', postgresql.UUID(), nullable=True)
    )

    op.create_index(
        'ix_estoque_movimentacoes_tenant_id',
        'estoque_movimentacoes',
        ['tenant_id']
    )

    op.execute(
        """
        UPDATE estoque_movimentacoes
        SET tenant_id = (
            SELECT id FROM tenants
            ORDER BY created_at
            LIMIT 1
        )
        """
    )

    op.alter_column(
        'estoque_movimentacoes',
        'tenant_id',
        nullable=False
    )

    op.create_foreign_key(
        'fk_estoque_movimentacoes_tenant',
        'estoque_movimentacoes',
        'tenants',
        ['tenant_id'],
        ['id'],
        ondelete='RESTRICT'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop estoque_movimentacoes tenant_id
    op.drop_constraint('fk_estoque_movimentacoes_tenant', 'estoque_movimentacoes', type_='foreignkey')
    op.drop_index('ix_estoque_movimentacoes_tenant_id', table_name='estoque_movimentacoes')
    op.drop_column('estoque_movimentacoes', 'tenant_id')

    # Drop produto_lotes tenant_id
    op.drop_constraint('fk_produto_lotes_tenant', 'produto_lotes', type_='foreignkey')
    op.drop_index('ix_produto_lotes_tenant_id', table_name='produto_lotes')
    op.drop_column('produto_lotes', 'tenant_id')
