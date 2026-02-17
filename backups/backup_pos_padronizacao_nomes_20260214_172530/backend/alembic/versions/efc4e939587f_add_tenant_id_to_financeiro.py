"""add tenant_id to financeiro

Revision ID: efc4e939587f
Revises: cb4a6a716db2
Create Date: 2026-01-26 11:02:45.603848

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'efc4e939587f'
down_revision: Union[str, Sequence[str], None] = 'cb4a6a716db2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # =========================
    # TABELAS ESTRUTURAIS
    # =========================
    op.add_column('categorias_financeiras', sa.Column('tenant_id', postgresql.UUID(), nullable=True))
    op.add_column('formas_pagamento', sa.Column('tenant_id', postgresql.UUID(), nullable=True))
    op.add_column('contas_bancarias', sa.Column('tenant_id', postgresql.UUID(), nullable=True))

    op.execute("""
        UPDATE categorias_financeiras
        SET tenant_id = (SELECT id FROM tenants ORDER BY created_at LIMIT 1);
        UPDATE formas_pagamento
        SET tenant_id = (SELECT id FROM tenants ORDER BY created_at LIMIT 1);
        UPDATE contas_bancarias
        SET tenant_id = (SELECT id FROM tenants ORDER BY created_at LIMIT 1);
    """)

    op.alter_column('categorias_financeiras', 'tenant_id', nullable=False)
    op.alter_column('formas_pagamento', 'tenant_id', nullable=False)
    op.alter_column('contas_bancarias', 'tenant_id', nullable=False)

    op.create_index('ix_cat_fin_tenant', 'categorias_financeiras', ['tenant_id'])
    op.create_index('ix_forma_pg_tenant', 'formas_pagamento', ['tenant_id'])
    op.create_index('ix_conta_banc_tenant', 'contas_bancarias', ['tenant_id'])

    op.create_foreign_key('fk_cat_fin_tenant', 'categorias_financeiras', 'tenants', ['tenant_id'], ['id'])
    op.create_foreign_key('fk_forma_pg_tenant', 'formas_pagamento', 'tenants', ['tenant_id'], ['id'])
    op.create_foreign_key('fk_conta_banc_tenant', 'contas_bancarias', 'tenants', ['tenant_id'], ['id'])

    # =========================
    # TABELAS TRANSACIONAIS
    # =========================
    tables = [
        'contas_pagar',
        'contas_receber',
        'pagamentos',
        'recebimentos',
        'movimentacoes_financeiras',
        'lancamentos_manuais',
        'lancamentos_recorrentes'
    ]

    for t in tables:
        op.add_column(t, sa.Column('tenant_id', postgresql.UUID(), nullable=True))
        op.execute(f"""
            UPDATE {t}
            SET tenant_id = (
                SELECT id FROM tenants ORDER BY created_at LIMIT 1
            )
        """)
        op.alter_column(t, 'tenant_id', nullable=False)
        op.create_index(f'ix_{t}_tenant', t, ['tenant_id'])
        op.create_foreign_key(f'fk_{t}_tenant', t, 'tenants', ['tenant_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    tables = [
        'lancamentos_recorrentes',
        'lancamentos_manuais',
        'movimentacoes_financeiras',
        'recebimentos',
        'pagamentos',
        'contas_receber',
        'contas_pagar'
    ]

    for t in tables:
        op.drop_constraint(f'fk_{t}_tenant', t, type_='foreignkey')
        op.drop_index(f'ix_{t}_tenant', table_name=t)
        op.drop_column(t, 'tenant_id')

    op.drop_constraint('fk_conta_banc_tenant', 'contas_bancarias', type_='foreignkey')
    op.drop_constraint('fk_forma_pg_tenant', 'formas_pagamento', type_='foreignkey')
    op.drop_constraint('fk_cat_fin_tenant', 'categorias_financeiras', type_='foreignkey')

    op.drop_index('ix_conta_banc_tenant', table_name='contas_bancarias')
    op.drop_index('ix_forma_pg_tenant', table_name='formas_pagamento')
    op.drop_index('ix_cat_fin_tenant', table_name='categorias_financeiras')

    op.drop_column('contas_bancarias', 'tenant_id')
    op.drop_column('formas_pagamento', 'tenant_id')
    op.drop_column('categorias_financeiras', 'tenant_id')
