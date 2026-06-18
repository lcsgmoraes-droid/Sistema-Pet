"""cashback expires_at and tx_type

Revision ID: h1b2c3d4e5f6
Revises: 31dfe937b9dd
Create Date: 2026-03-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'h1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '31dfe937b9dd'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Adiciona coluna expires_at (validade do crédito — só usada em lançamentos positivos)
    op.add_column(
        'cashback_transactions',
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    )
    # Adiciona coluna tx_type: 'credit' | 'debit' | 'expired'
    op.add_column(
        'cashback_transactions',
        sa.Column('tx_type', sa.String(20), nullable=False, server_default='credit'),
    )
    # Adiciona 'expiration' e 'redemption' ao enum existente
    op.execute("ALTER TYPE cashback_source_type_enum ADD VALUE IF NOT EXISTS 'expiration'")
    op.execute("ALTER TYPE cashback_source_type_enum ADD VALUE IF NOT EXISTS 'redemption'")

    # Índice para o job de expiração (busca por expires_at)
    op.create_index(
        'ix_ct_tenant_expires_at',
        'cashback_transactions',
        ['tenant_id', 'expires_at'],
        postgresql_where=sa.text("expires_at IS NOT NULL AND tx_type = 'credit'"),
    )


def downgrade() -> None:
    op.drop_index('ix_ct_tenant_expires_at', table_name='cashback_transactions')
    op.drop_column('cashback_transactions', 'tx_type')
    op.drop_column('cashback_transactions', 'expires_at')
    # Nota: valores de enum não podem ser removidos facilmente no PostgreSQL
