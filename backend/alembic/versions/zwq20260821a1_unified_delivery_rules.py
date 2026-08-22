"""unify delivery pricing rules for app and ecommerce

Revision ID: zwq20260821a1
Revises: zwp20260816a1
"""

from alembic import op
import sqlalchemy as sa


revision = "zwq20260821a1"
down_revision = "zwp20260816a1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "configuracoes_entrega",
        sa.Column(
            "entrega_ativa",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.add_column(
        "configuracoes_entrega",
        sa.Column(
            "retirada_ativa",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.add_column(
        "configuracoes_entrega",
        sa.Column(
            "modalidade_cobranca",
            sa.String(length=20),
            server_default="fixa",
            nullable=False,
        ),
    )
    op.add_column(
        "configuracoes_entrega",
        sa.Column("taxa_fixa", sa.Numeric(10, 2), server_default="0", nullable=False),
    )
    op.add_column(
        "configuracoes_entrega",
        sa.Column("valor_por_km_cobrado", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "configuracoes_entrega",
        sa.Column("taxa_minima", sa.Numeric(10, 2), server_default="0", nullable=False),
    )
    op.add_column(
        "configuracoes_entrega",
        sa.Column("distancia_maxima_entrega_km", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "configuracoes_entrega",
        sa.Column("frete_gratis_acima", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "configuracoes_entrega",
        sa.Column("distancia_maxima_frete_gratis_km", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "configuracoes_entrega",
        sa.Column(
            "pedido_minimo", sa.Numeric(10, 2), server_default="0", nullable=False
        ),
    )
    op.add_column(
        "configuracoes_entrega",
        sa.Column("prazo_entrega_texto", sa.String(length=120), nullable=True),
    )

    op.execute(
        """
        UPDATE configuracoes_entrega ce
        SET entrega_ativa = COALESCE(t.ecommerce_entrega_ativa, true),
            retirada_ativa = COALESCE(t.ecommerce_retirada_ativa, true),
            taxa_fixa = COALESCE(t.ecommerce_taxa_entrega, 0),
            frete_gratis_acima = t.ecommerce_frete_gratis_acima,
            pedido_minimo = COALESCE(t.ecommerce_pedido_minimo, 0),
            prazo_entrega_texto = t.ecommerce_prazo_entrega_texto
        FROM tenants t
        WHERE CAST(ce.tenant_id AS text) = CAST(t.id AS text)
        """
    )

    op.add_column("pedidos", sa.Column("endereco_entrega", sa.Text(), nullable=True))
    op.add_column(
        "pedidos",
        sa.Column("frete_valor", sa.Float(), server_default="0", nullable=False),
    )
    op.add_column("pedidos", sa.Column("frete_distancia_km", sa.Float(), nullable=True))
    op.add_column("pedidos", sa.Column("frete_valor_por_km", sa.Float(), nullable=True))
    op.add_column(
        "pedidos", sa.Column("frete_modalidade", sa.String(length=20), nullable=True)
    )
    op.add_column(
        "pedidos",
        sa.Column(
            "frete_gratis_aplicado",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )


def downgrade():
    op.drop_column("pedidos", "frete_gratis_aplicado")
    op.drop_column("pedidos", "frete_modalidade")
    op.drop_column("pedidos", "frete_valor_por_km")
    op.drop_column("pedidos", "frete_distancia_km")
    op.drop_column("pedidos", "frete_valor")
    op.drop_column("pedidos", "endereco_entrega")

    op.drop_column("configuracoes_entrega", "prazo_entrega_texto")
    op.drop_column("configuracoes_entrega", "pedido_minimo")
    op.drop_column("configuracoes_entrega", "distancia_maxima_frete_gratis_km")
    op.drop_column("configuracoes_entrega", "frete_gratis_acima")
    op.drop_column("configuracoes_entrega", "distancia_maxima_entrega_km")
    op.drop_column("configuracoes_entrega", "taxa_minima")
    op.drop_column("configuracoes_entrega", "valor_por_km_cobrado")
    op.drop_column("configuracoes_entrega", "taxa_fixa")
    op.drop_column("configuracoes_entrega", "modalidade_cobranca")
    op.drop_column("configuracoes_entrega", "retirada_ativa")
    op.drop_column("configuracoes_entrega", "entrega_ativa")
