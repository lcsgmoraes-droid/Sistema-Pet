"""create bling nf cache

Revision ID: r3s4t5u6v7w8
Revises: a7b8c9d0e1f2
Create Date: 2026-03-30 09:35:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "r3s4t5u6v7w8"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bling_notas_fiscais_cache",
        sa.Column("bling_id", sa.String(length=50), nullable=False),
        sa.Column("modelo", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(length=10), nullable=False),
        sa.Column("numero", sa.String(length=50), nullable=True),
        sa.Column("serie", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=True),
        sa.Column("chave", sa.String(length=64), nullable=True),
        sa.Column("data_emissao", sa.DateTime(), nullable=True),
        sa.Column("valor", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("cliente", sa.JSON(), nullable=True),
        sa.Column("loja", sa.JSON(), nullable=True),
        sa.Column("unidade_negocio", sa.JSON(), nullable=True),
        sa.Column("canal", sa.String(length=50), nullable=True),
        sa.Column("canal_label", sa.String(length=100), nullable=True),
        sa.Column("numero_loja_virtual", sa.String(length=100), nullable=True),
        sa.Column("origem_loja_virtual", sa.String(length=100), nullable=True),
        sa.Column("origem_canal_venda", sa.String(length=100), nullable=True),
        sa.Column("numero_pedido_loja", sa.String(length=100), nullable=True),
        sa.Column("pedido_bling_id_ref", sa.String(length=50), nullable=True),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("resumo_payload", sa.JSON(), nullable=True),
        sa.Column("detalhe_payload", sa.JSON(), nullable=True),
        sa.Column("detalhada_em", sa.DateTime(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "bling_id",
            "modelo",
            name="uq_bling_notas_fiscais_cache_tenant_bling_modelo",
        ),
    )
    op.create_index(
        "ix_bling_notas_fiscais_cache_tenant_id",
        "bling_notas_fiscais_cache",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_bling_notas_fiscais_cache_data_emissao",
        "bling_notas_fiscais_cache",
        ["data_emissao"],
        unique=False,
    )
    op.create_index(
        "ix_bling_notas_fiscais_cache_last_synced_at",
        "bling_notas_fiscais_cache",
        ["last_synced_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_bling_notas_fiscais_cache_last_synced_at", table_name="bling_notas_fiscais_cache")
    op.drop_index("ix_bling_notas_fiscais_cache_data_emissao", table_name="bling_notas_fiscais_cache")
    op.drop_index("ix_bling_notas_fiscais_cache_tenant_id", table_name="bling_notas_fiscais_cache")
    op.drop_table("bling_notas_fiscais_cache")
