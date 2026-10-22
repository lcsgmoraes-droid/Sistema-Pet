"""Preparacao local do catalogo iFood e premissas de margem por loja."""

from alembic import op
import sqlalchemy as sa

revision = "zzzzg20261019a1"
down_revision = "zzzzf20261019a1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "produtos",
        sa.Column(
            "anunciar_ifood", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.add_column(
        "produtos",
        sa.Column(
            "ifood_pausado", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    for name in ("preco_ifood", "preco_ifood_promo"):
        op.add_column("produtos", sa.Column(name, sa.Float(), nullable=True))
    for name in ("preco_ifood_promo_inicio", "preco_ifood_promo_fim"):
        op.add_column(
            "produtos", sa.Column(name, sa.DateTime(timezone=True), nullable=True)
        )
    for name in (
        "commission_merchant_percent",
        "commission_ifood_percent",
        "payment_fee_percent",
        "tax_percent",
        "additional_unit_cost",
        "target_margin_percent",
    ):
        op.add_column(
            "ifood_merchant_configs", sa.Column(name, sa.Float(), nullable=True)
        )


def downgrade():
    for name in (
        "target_margin_percent",
        "additional_unit_cost",
        "tax_percent",
        "payment_fee_percent",
        "commission_ifood_percent",
        "commission_merchant_percent",
    ):
        op.drop_column("ifood_merchant_configs", name)
    for name in (
        "preco_ifood_promo_fim",
        "preco_ifood_promo_inicio",
        "preco_ifood_promo",
        "preco_ifood",
        "ifood_pausado",
        "anunciar_ifood",
    ):
        op.drop_column("produtos", name)
