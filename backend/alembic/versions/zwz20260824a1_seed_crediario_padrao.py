"""seed default store credit payment method

Revision ID: zwz20260824a1
Revises: zwy20260823a1
"""

from alembic import op
import sqlalchemy as sa


revision = "zwz20260824a1"
down_revision = "zwy20260823a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if not {"tenants", "users", "formas_pagamento"}.issubset(tables):
        return

    bind.execute(
        sa.text(
            """
            INSERT INTO formas_pagamento (
                tenant_id, user_id, nome, tipo, taxa_percentual, taxa_fixa,
                prazo_dias, prazo_recebimento, gera_contas_receber,
                split_parcelas, requer_nsu, ativo, permite_parcelamento,
                max_parcelas, parcelas_maximas, icone, cor, created_at, updated_at
            )
            SELECT
                t.id, MIN(u.id), 'Crediário', 'crediario', 0, 0,
                30, 30, true, false, false, true, false,
                1, 1, 'calendar', '#F59E0B', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            FROM tenants t
            JOIN users u ON u.tenant_id = t.id
            WHERE NOT EXISTS (
                SELECT 1 FROM formas_pagamento fp
                WHERE fp.tenant_id = t.id AND fp.tipo = 'crediario'
            )
            GROUP BY t.id
            """
        )
    )


def downgrade() -> None:
    # Preserva formas que possam ter sido usadas em vendas e contas a receber.
    pass
