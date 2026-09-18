"""Prepara emissão direta pela IntNFe e código IBGE do destinatário.

Revision ID: zzp20260914a1
Revises: zzo20260911a1
Create Date: 2026-09-14
"""

from alembic import op
import sqlalchemy as sa


revision = "zzp20260914a1"
down_revision = "zzo20260911a1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "intnfe_connections",
        sa.Column("production_client_id", sa.String(128), nullable=True),
    )
    op.add_column(
        "intnfe_connections",
        sa.Column("production_client_secret_encrypted", sa.Text(), nullable=True),
    )
    op.add_column(
        "intnfe_connections",
        sa.Column(
            "production_credentials_created_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "intnfe_connections",
        sa.Column(
            "production_credentials_pending",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "intnfe_connections",
        sa.Column(
            "emission_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "intnfe_connections",
        sa.Column(
            "emission_environment",
            sa.SmallInteger(),
            nullable=False,
            server_default="2",
        ),
    )
    op.add_column(
        "intnfe_connections",
        sa.Column("nfe_series", sa.String(3), nullable=False, server_default="1"),
    )
    op.add_column(
        "intnfe_connections",
        sa.Column("nfce_series", sa.String(3), nullable=False, server_default="1"),
    )

    op.add_column(
        "clientes", sa.Column("codigo_municipio", sa.String(7), nullable=True)
    )

    op.add_column("vendas", sa.Column("nfe_provider", sa.String(20), nullable=True))
    op.add_column(
        "vendas", sa.Column("nfe_correlation_id", sa.String(128), nullable=True)
    )
    op.add_column("vendas", sa.Column("nfe_protocolo", sa.String(64), nullable=True))
    op.add_column("vendas", sa.Column("nfe_ambiente", sa.Integer(), nullable=True))
    op.add_column("vendas", sa.Column("nfe_codigo_erro", sa.String(20), nullable=True))
    op.add_column(
        "vendas", sa.Column("nfe_idempotency_key", sa.String(128), nullable=True)
    )
    op.add_column("vendas", sa.Column("nfe_payload_hash", sa.String(64), nullable=True))
    op.add_column(
        "bling_notas_fiscais_cache", sa.Column("venda_id", sa.Integer(), nullable=True)
    )
    op.add_column(
        "bling_notas_fiscais_cache",
        sa.Column("provider", sa.String(20), nullable=True),
    )
    op.create_index(
        "ix_bling_notas_fiscais_cache_venda_id",
        "bling_notas_fiscais_cache",
        ["venda_id"],
        unique=False,
    )
    op.create_index(
        "ix_vendas_nfe_correlation_id", "vendas", ["nfe_correlation_id"], unique=False
    )
    op.create_unique_constraint(
        "uq_vendas_tenant_nfe_correlation_id",
        "vendas",
        ["tenant_id", "nfe_correlation_id"],
    )


def downgrade():
    op.drop_index(
        "ix_bling_notas_fiscais_cache_venda_id",
        table_name="bling_notas_fiscais_cache",
    )
    op.drop_column("bling_notas_fiscais_cache", "provider")
    op.drop_column("bling_notas_fiscais_cache", "venda_id")
    op.drop_constraint("uq_vendas_tenant_nfe_correlation_id", "vendas", type_="unique")
    op.drop_index("ix_vendas_nfe_correlation_id", table_name="vendas")
    for column in (
        "nfe_idempotency_key",
        "nfe_payload_hash",
        "nfe_codigo_erro",
        "nfe_ambiente",
        "nfe_protocolo",
        "nfe_correlation_id",
        "nfe_provider",
    ):
        op.drop_column("vendas", column)
    op.drop_column("clientes", "codigo_municipio")
    for column in (
        "nfce_series",
        "nfe_series",
        "emission_environment",
        "emission_enabled",
        "production_credentials_created_at",
        "production_credentials_pending",
        "production_client_secret_encrypted",
        "production_client_id",
    ):
        op.drop_column("intnfe_connections", column)
