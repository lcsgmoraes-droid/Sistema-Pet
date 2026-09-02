"""backfill de custos de produtos compostos

Revision ID: zxo20260829a1
Revises: zxn20260829a1
Create Date: 2026-08-29
"""

from alembic import op
import sqlalchemy as sa


revision = "zxo20260829a1"
down_revision = "zxn20260829a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tabelas = set(sa.inspect(bind).get_table_names())
    if not {"produtos", "produto_kit_componentes"}.issubset(tabelas):
        return

    bind.execute(
        sa.text(
            """
            UPDATE produtos AS kit
               SET preco_custo = custos.custo_total
              FROM (
                    SELECT rel.kit_id,
                           rel.tenant_id,
                           SUM(
                               COALESCE(componente.preco_custo, 0)
                               * COALESCE(rel.quantidade, 0)
                           ) AS custo_total
                      FROM produto_kit_componentes AS rel
                      JOIN produtos AS componente
                        ON componente.id = rel.produto_componente_id
                       AND componente.tenant_id = rel.tenant_id
                     WHERE componente.tipo_produto IN ('SIMPLES', 'VARIACAO')
                     GROUP BY rel.kit_id, rel.tenant_id
                   ) AS custos
             WHERE kit.id = custos.kit_id
               AND kit.tenant_id = custos.tenant_id
               AND kit.tipo_produto IN ('KIT', 'VARIACAO')
               AND NULLIF(kit.tipo_kit, '') IS NOT NULL
               AND COALESCE(kit.e_granel, false) = false
               AND lower(COALESCE(kit.nome, '')) NOT LIKE '%granel%'
               AND COALESCE(kit.preco_custo, 0) <> custos.custo_total
            """
        )
    )


def downgrade() -> None:
    # O valor anterior era inconsistente e não deve ser restaurado.
    pass
