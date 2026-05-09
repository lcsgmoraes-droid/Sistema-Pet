"""scope sale numbers and product SKU uniqueness by tenant

Revision ID: ob20260509a1
Revises: oa20260508a6
Create Date: 2026-05-09 16:25:00.000000
"""

from alembic import op


revision = "ob20260509a1"
down_revision = "oa20260508a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing data can have the same SKU with only case changes. Keep the
    # oldest product untouched and make later duplicates explicit before the
    # case-insensitive unique index is created.
    op.execute(
        """
        WITH duplicados AS (
            SELECT
                id,
                row_number() OVER (
                    PARTITION BY tenant_id, lower(btrim(codigo))
                    ORDER BY id
                ) AS rn
            FROM produtos
            WHERE codigo IS NOT NULL
              AND btrim(codigo) <> ''
        )
        UPDATE produtos p
        SET
            codigo = left(btrim(p.codigo), greatest(1, 50 - length('-DUP' || p.id::text)))
                     || '-DUP' || p.id::text,
            updated_at = CURRENT_TIMESTAMP
        FROM duplicados d
        WHERE p.id = d.id
          AND d.rn > 1
        """
    )

    op.execute("ALTER TABLE produtos DROP CONSTRAINT IF EXISTS produtos_codigo_key")
    op.execute("DROP INDEX IF EXISTS produtos_codigo_key")
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_produtos_tenant_codigo_lower
        ON produtos (tenant_id, lower(codigo))
        """
    )

    op.execute("DROP INDEX IF EXISTS ix_vendas_numero_venda")
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_vendas_tenant_numero_venda
        ON vendas (tenant_id, numero_venda)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_vendas_tenant_numero_venda")
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ix_vendas_numero_venda
        ON vendas (numero_venda)
        """
    )

    op.execute("DROP INDEX IF EXISTS ux_produtos_tenant_codigo_lower")
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS produtos_codigo_key
        ON produtos (codigo)
        """
    )
