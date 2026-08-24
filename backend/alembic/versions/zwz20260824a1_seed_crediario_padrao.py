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


def _set_rls(bind, *, enabled: bool) -> None:
    if bind.dialect.name != "postgresql":
        return
    for table_name in ("users", "formas_pagamento"):
        if enabled:
            op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
            op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")
        else:
            op.execute(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY")


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if not {"users", "formas_pagamento"}.issubset(tables):
        return

    _set_rls(bind, enabled=False)
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
                u.tenant_id, MIN(u.id), 'Crediário', 'crediario', 0, 0,
                30, 30, true, false, false, true, false,
                1, 1, 'calendar', '#F59E0B', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            FROM users u
            WHERE u.tenant_id IS NOT NULL
              AND NOT EXISTS (
                SELECT 1 FROM formas_pagamento fp
                WHERE fp.tenant_id = u.tenant_id AND fp.tipo = 'crediario'
              )
            GROUP BY u.tenant_id
            """
        )
    )
    _set_rls(bind, enabled=True)


def downgrade() -> None:
    # Preserva formas que possam ter sido usadas em vendas e contas a receber.
    pass
