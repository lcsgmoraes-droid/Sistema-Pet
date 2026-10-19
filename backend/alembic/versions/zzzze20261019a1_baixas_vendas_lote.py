"""Recebimento em lote com rateio explícito e estorno auditável."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "zzzze20261019a1"
down_revision = "zzzzd20261015a1"
branch_labels = None
depends_on = None


def _base():
    return [
        sa.Column("id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    ]


def upgrade():
    op.create_table(
        "vendas_baixas_lotes",
        *_base(),
        sa.Column(
            "cliente_id", sa.Integer(), sa.ForeignKey("clientes.id"), nullable=False
        ),
        sa.Column("caixa_id", sa.Integer(), sa.ForeignKey("caixas.id"), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("usuario_nome", sa.String(200), nullable=False),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column("requisicao", sa.JSON(), nullable=False),
        sa.Column("observacoes", sa.Text()),
        sa.Column("resultado", sa.JSON()),
        sa.Column("valor_total", sa.Numeric(10, 2), nullable=False),
        sa.Column("forma_pagamento", sa.String(50), nullable=False),
        sa.Column("numero_transacao", sa.String(100)),
        sa.Column("data", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("estornado_em", sa.DateTime()),
        sa.Column("estornado_por_id", sa.Integer()),
        sa.Column("estornado_por_nome", sa.String(200)),
        sa.Column("caixa_estorno_id", sa.Integer(), sa.ForeignKey("caixas.id")),
        sa.Column("motivo_estorno", sa.Text()),
    )
    op.create_index(
        "ix_vendas_baixas_lotes_tenant_id", "vendas_baixas_lotes", ["tenant_id"]
    )
    op.create_index(
        "ux_baixa_lote_tenant_request",
        "vendas_baixas_lotes",
        ["tenant_id", "request_id"],
        unique=True,
    )
    op.create_index(
        "ix_baixa_lote_cliente_data",
        "vendas_baixas_lotes",
        ["tenant_id", "cliente_id", "data"],
    )
    op.create_table(
        "vendas_baixas_lote_itens",
        *_base(),
        sa.Column(
            "lote_id",
            sa.Integer(),
            sa.ForeignKey("vendas_baixas_lotes.id"),
            nullable=False,
        ),
        sa.Column("venda_id", sa.Integer(), sa.ForeignKey("vendas.id"), nullable=False),
        sa.Column("numero_venda", sa.String(20), nullable=False),
        sa.Column("valor", sa.Numeric(10, 2), nullable=False),
        sa.Column("pagamento_id", sa.Integer(), nullable=False),
        sa.Column("pagamento_estorno_id", sa.Integer()),
        sa.Column("efeitos", sa.JSON(), nullable=False),
    )
    for campo in ("tenant_id", "lote_id", "venda_id"):
        op.create_index(
            f"ix_vendas_baixas_lote_itens_{campo}", "vendas_baixas_lote_itens", [campo]
        )
    op.create_index(
        "ux_baixa_lote_pagamento",
        "vendas_baixas_lote_itens",
        ["pagamento_id"],
        unique=True,
    )
    op.add_column(
        "venda_pagamentos",
        sa.Column(
            "baixa_lote_id", sa.Integer(), sa.ForeignKey("vendas_baixas_lotes.id")
        ),
    )
    op.create_index(
        "ix_venda_pagamentos_baixa_lote_id", "venda_pagamentos", ["baixa_lote_id"]
    )


def downgrade():
    op.drop_index("ix_venda_pagamentos_baixa_lote_id", table_name="venda_pagamentos")
    op.drop_column("venda_pagamentos", "baixa_lote_id")
    op.drop_table("vendas_baixas_lote_itens")
    op.drop_table("vendas_baixas_lotes")
