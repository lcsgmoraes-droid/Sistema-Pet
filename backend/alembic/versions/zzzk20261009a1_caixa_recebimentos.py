"""Associa o recebimento ao caixa que o registrou, preservando a venda original."""

from alembic import op
import sqlalchemy as sa

revision = "zzzk20261009a1"
down_revision = "zzzj20261006a1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("venda_pagamentos", sa.Column("caixa_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_venda_pagamentos_caixa_id", "venda_pagamentos", "caixas", ["caixa_id"], ["id"]
    )
    op.create_index("ix_venda_pagamentos_caixa_id", "venda_pagamentos", ["caixa_id"])

    # Legados: só atribuir quando o intervalo identifica um único caixa da empresa.
    # Em caixas individuais simultâneos, preservar NULL em vez de inventar o recebedor.
    op.execute(sa.text("""
        WITH candidatos AS (
            SELECT p.id AS pagamento_id, MIN(c.id) AS caixa_id
            FROM venda_pagamentos p
            JOIN vendas v ON v.id = p.venda_id AND v.tenant_id = p.tenant_id
            JOIN caixas c ON c.tenant_id = p.tenant_id
                AND p.data_pagamento >= c.data_abertura
                AND (c.data_fechamento IS NULL OR p.data_pagamento <= c.data_fechamento)
            WHERE p.caixa_id IS NULL AND v.canal = 'loja_fisica'
            GROUP BY p.id HAVING COUNT(c.id) = 1
        )
        UPDATE venda_pagamentos p SET caixa_id = candidatos.caixa_id
        FROM candidatos WHERE p.id = candidatos.pagamento_id
    """))


def downgrade():
    op.drop_index("ix_venda_pagamentos_caixa_id", table_name="venda_pagamentos")
    op.drop_constraint("fk_venda_pagamentos_caixa_id", "venda_pagamentos", type_="foreignkey")
    op.drop_column("venda_pagamentos", "caixa_id")
