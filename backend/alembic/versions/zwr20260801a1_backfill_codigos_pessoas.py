"""backfill person codes created outside the ERP form

Revision ID: zwr20260801a1
Revises: zwq20260731a1
Create Date: 2026-08-01
"""

from alembic import op


revision = "zwr20260801a1"
down_revision = "zwq20260731a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Gera codigos deterministas e unicos por tenant, sempre depois do maior
    # codigo numerico ja existente. Inclui ativos e inativos para respeitar a
    # unicidade historica de (tenant_id, codigo).
    op.execute(
        """
        WITH tenant_max AS (
            SELECT
                tenant_id,
                COALESCE(
                    MAX(
                        CASE
                            WHEN BTRIM(codigo) ~ '^[0-9]+$'
                            THEN BTRIM(codigo)::BIGINT
                        END
                    ),
                    10000
                ) AS maior_codigo
            FROM clientes
            GROUP BY tenant_id
        ),
        sem_codigo AS (
            SELECT
                id,
                tenant_id,
                ROW_NUMBER() OVER (
                    PARTITION BY tenant_id
                    ORDER BY created_at NULLS FIRST, id
                ) AS sequencia
            FROM clientes
            WHERE codigo IS NULL OR BTRIM(codigo) = ''
        )
        UPDATE clientes AS cliente
        SET codigo = (tenant_max.maior_codigo + sem_codigo.sequencia)::TEXT
        FROM sem_codigo
        JOIN tenant_max ON tenant_max.tenant_id = sem_codigo.tenant_id
        WHERE cliente.id = sem_codigo.id
        """
    )


def downgrade() -> None:
    # Os codigos passam a ser identificadores validos usados pelo sistema. Nao
    # e seguro apagar essa informacao ao reverter apenas a versao do codigo.
    pass
