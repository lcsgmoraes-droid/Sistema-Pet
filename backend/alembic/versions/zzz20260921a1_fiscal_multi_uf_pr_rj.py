"""Adiciona confirmacao fiscal e campos estaduais de ICMS.

Revision ID: zzz20260921a1
Revises: zzy20260921a1
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "zzz20260921a1"
down_revision: Union[str, Sequence[str], None] = "zzy20260921a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PRODUCT_TABLES = ("produto_config_fiscal", "kit_config_fiscal")


def upgrade() -> None:
    op.add_column(
        "empresa_config_fiscal",
        sa.Column(
            "configuracao_confirmada",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "empresa_config_fiscal",
        sa.Column("configuracao_confirmada_em", sa.DateTime(timezone=True)),
    )
    op.execute("""
        UPDATE empresa_config_fiscal AS config
        SET
            uf = UPPER(SUBSTRING(TRIM(tenant.uf) FROM 1 FOR 2)),
            icms_aliquota_interna = CASE
                WHEN config.herdado_do_estado AND UPPER(TRIM(tenant.uf)) = 'PR' THEN 19.50
                WHEN config.herdado_do_estado AND UPPER(TRIM(tenant.uf)) = 'RJ' THEN 20.00
                WHEN config.herdado_do_estado AND UPPER(TRIM(tenant.uf)) = 'SP' THEN 18.00
                ELSE config.icms_aliquota_interna
            END
        FROM tenants AS tenant
        WHERE config.tenant_id::text = tenant.id::text
          AND tenant.uf IS NOT NULL
          AND LENGTH(TRIM(tenant.uf)) >= 2
        """)
    op.execute("""
        UPDATE empresa_config_fiscal
        SET aplica_difal = FALSE
        WHERE LOWER(regime_tributario) LIKE '%simples%'
        """)
    for table in PRODUCT_TABLES:
        op.add_column(table, sa.Column("codigo_beneficio_fiscal", sa.String(10)))
        op.add_column(table, sa.Column("fcp_aliquota", sa.Numeric(5, 2)))


def downgrade() -> None:
    for table in reversed(PRODUCT_TABLES):
        op.drop_column(table, "fcp_aliquota")
        op.drop_column(table, "codigo_beneficio_fiscal")
    op.drop_column("empresa_config_fiscal", "configuracao_confirmada_em")
    op.drop_column("empresa_config_fiscal", "configuracao_confirmada")
