"""normalize product SKU unique index with trim

Revision ID: oc20260509a1
Revises: ob20260509a1
Create Date: 2026-05-09 17:40:00.000000
"""

from alembic import op


revision = "oc20260509a1"
down_revision = "ob20260509a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fecha a regra no banco com a mesma normalizacao usada pelo backend:
    # tenant + lower(trim(SKU)). Antes de recriar o indice, qualquer duplicado
    # historico ganha sufixo explicito para nao bloquear a migracao.
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
    op.execute("DROP INDEX IF EXISTS ux_produtos_tenant_codigo_lower")
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_produtos_tenant_codigo_lower
        ON produtos (tenant_id, lower(btrim(codigo)))
        WHERE codigo IS NOT NULL AND btrim(codigo) <> ''
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_produtos_tenant_codigo_lower")
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_produtos_tenant_codigo_lower
        ON produtos (tenant_id, lower(codigo))
        """
    )
