"""create supplier purchase pending workflow

Revision ID: nq20260504a1
Revises: np20260504a1
Create Date: 2026-05-04 23:55:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "nq20260504a1"
down_revision = "np20260504a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "compras_pendencias_fornecedor",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("codigo", sa.String(length=40), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("origem", sa.String(length=30), nullable=False),
        sa.Column("tipo", sa.String(length=40), nullable=False),
        sa.Column("fornecedor_id", sa.Integer(), nullable=True),
        sa.Column("fornecedor_nome", sa.String(length=255), nullable=False),
        sa.Column("fornecedor_cnpj", sa.String(length=18), nullable=True),
        sa.Column("nota_entrada_id", sa.Integer(), nullable=True),
        sa.Column("pedido_compra_id", sa.Integer(), nullable=True),
        sa.Column("numero_nota", sa.String(length=20), nullable=True),
        sa.Column("numero_pedido", sa.String(length=50), nullable=True),
        sa.Column("titulo", sa.String(length=255), nullable=False),
        sa.Column("resumo", sa.Text(), nullable=True),
        sa.Column("prazo_previsto", sa.DateTime(), nullable=True),
        sa.Column("email_destinatario", sa.String(length=255), nullable=True),
        sa.Column("email_assunto", sa.String(length=255), nullable=True),
        sa.Column("email_mensagem", sa.Text(), nullable=True),
        sa.Column("email_enviado_em", sa.DateTime(), nullable=True),
        sa.Column("pdf_gerado_em", sa.DateTime(), nullable=True),
        sa.Column("resolvida_em", sa.DateTime(), nullable=True),
        sa.Column("resolucao_observacao", sa.Text(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["nota_entrada_id"], ["notas_entrada.id"]),
        sa.ForeignKeyConstraint(["pedido_compra_id"], ["pedidos_compra.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_compras_pendencias_fornecedor_id"), "compras_pendencias_fornecedor", ["id"], unique=False)
    op.create_index(op.f("ix_compras_pendencias_fornecedor_tenant_id"), "compras_pendencias_fornecedor", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_compras_pendencias_fornecedor_codigo"), "compras_pendencias_fornecedor", ["codigo"], unique=False)
    op.create_index(op.f("ix_compras_pendencias_fornecedor_status"), "compras_pendencias_fornecedor", ["status"], unique=False)
    op.create_index(op.f("ix_compras_pendencias_fornecedor_fornecedor_id"), "compras_pendencias_fornecedor", ["fornecedor_id"], unique=False)
    op.create_index(op.f("ix_compras_pendencias_fornecedor_nota_entrada_id"), "compras_pendencias_fornecedor", ["nota_entrada_id"], unique=False)
    op.create_index(op.f("ix_compras_pendencias_fornecedor_pedido_compra_id"), "compras_pendencias_fornecedor", ["pedido_compra_id"], unique=False)
    op.create_index(op.f("ix_compras_pendencias_fornecedor_user_id"), "compras_pendencias_fornecedor", ["user_id"], unique=False)
    op.create_index(
        "ix_compras_pendencias_fornecedor_tenant_status",
        "compras_pendencias_fornecedor",
        ["tenant_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_compras_pendencias_fornecedor_tenant_nota",
        "compras_pendencias_fornecedor",
        ["tenant_id", "nota_entrada_id"],
        unique=False,
    )

    op.create_table(
        "compras_pendencias_fornecedor_itens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pendencia_id", sa.Integer(), nullable=False),
        sa.Column("nota_entrada_item_id", sa.Integer(), nullable=True),
        sa.Column("produto_id", sa.Integer(), nullable=True),
        sa.Column("codigo_produto", sa.String(length=100), nullable=True),
        sa.Column("descricao", sa.String(length=500), nullable=False),
        sa.Column("unidade", sa.String(length=10), nullable=True),
        sa.Column("quantidade_nf", sa.Float(), nullable=False),
        sa.Column("quantidade_recebida", sa.Float(), nullable=False),
        sa.Column("quantidade_faltante", sa.Float(), nullable=False),
        sa.Column("quantidade_avariada", sa.Float(), nullable=False),
        sa.Column("valor_unitario", sa.Float(), nullable=False),
        sa.Column("valor_total_divergente", sa.Float(), nullable=False),
        sa.Column("status_conferencia", sa.String(length=30), nullable=False),
        sa.Column("acao_sugerida", sa.String(length=40), nullable=False),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("resolvido", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["pendencia_id"], ["compras_pendencias_fornecedor.id"]),
        sa.ForeignKeyConstraint(["nota_entrada_item_id"], ["notas_entrada_itens.id"]),
        sa.ForeignKeyConstraint(["produto_id"], ["produtos.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_compras_pendencias_fornecedor_itens_id"), "compras_pendencias_fornecedor_itens", ["id"], unique=False)
    op.create_index(op.f("ix_compras_pendencias_fornecedor_itens_tenant_id"), "compras_pendencias_fornecedor_itens", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_compras_pendencias_fornecedor_itens_pendencia_id"), "compras_pendencias_fornecedor_itens", ["pendencia_id"], unique=False)
    op.create_index(op.f("ix_compras_pendencias_fornecedor_itens_nota_entrada_item_id"), "compras_pendencias_fornecedor_itens", ["nota_entrada_item_id"], unique=False)
    op.create_index(op.f("ix_compras_pendencias_fornecedor_itens_produto_id"), "compras_pendencias_fornecedor_itens", ["produto_id"], unique=False)
    op.create_index(
        "ix_compras_pendencias_fornecedor_itens_tenant_pendencia",
        "compras_pendencias_fornecedor_itens",
        ["tenant_id", "pendencia_id"],
        unique=False,
    )

    op.create_table(
        "compras_pendencias_fornecedor_historico",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pendencia_id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(length=40), nullable=False),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("status_anterior", sa.String(length=30), nullable=True),
        sa.Column("status_novo", sa.String(length=30), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["pendencia_id"], ["compras_pendencias_fornecedor.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_compras_pendencias_fornecedor_historico_id"), "compras_pendencias_fornecedor_historico", ["id"], unique=False)
    op.create_index(op.f("ix_compras_pendencias_fornecedor_historico_tenant_id"), "compras_pendencias_fornecedor_historico", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_compras_pendencias_fornecedor_historico_pendencia_id"), "compras_pendencias_fornecedor_historico", ["pendencia_id"], unique=False)
    op.create_index(op.f("ix_compras_pendencias_fornecedor_historico_user_id"), "compras_pendencias_fornecedor_historico", ["user_id"], unique=False)
    op.create_index(
        "ix_compras_pendencias_fornecedor_hist_tenant_pendencia",
        "compras_pendencias_fornecedor_historico",
        ["tenant_id", "pendencia_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_compras_pendencias_fornecedor_hist_tenant_pendencia", table_name="compras_pendencias_fornecedor_historico")
    op.drop_index(op.f("ix_compras_pendencias_fornecedor_historico_user_id"), table_name="compras_pendencias_fornecedor_historico")
    op.drop_index(op.f("ix_compras_pendencias_fornecedor_historico_pendencia_id"), table_name="compras_pendencias_fornecedor_historico")
    op.drop_index(op.f("ix_compras_pendencias_fornecedor_historico_tenant_id"), table_name="compras_pendencias_fornecedor_historico")
    op.drop_index(op.f("ix_compras_pendencias_fornecedor_historico_id"), table_name="compras_pendencias_fornecedor_historico")
    op.drop_table("compras_pendencias_fornecedor_historico")

    op.drop_index("ix_compras_pendencias_fornecedor_itens_tenant_pendencia", table_name="compras_pendencias_fornecedor_itens")
    op.drop_index(op.f("ix_compras_pendencias_fornecedor_itens_produto_id"), table_name="compras_pendencias_fornecedor_itens")
    op.drop_index(op.f("ix_compras_pendencias_fornecedor_itens_nota_entrada_item_id"), table_name="compras_pendencias_fornecedor_itens")
    op.drop_index(op.f("ix_compras_pendencias_fornecedor_itens_pendencia_id"), table_name="compras_pendencias_fornecedor_itens")
    op.drop_index(op.f("ix_compras_pendencias_fornecedor_itens_tenant_id"), table_name="compras_pendencias_fornecedor_itens")
    op.drop_index(op.f("ix_compras_pendencias_fornecedor_itens_id"), table_name="compras_pendencias_fornecedor_itens")
    op.drop_table("compras_pendencias_fornecedor_itens")

    op.drop_index("ix_compras_pendencias_fornecedor_tenant_nota", table_name="compras_pendencias_fornecedor")
    op.drop_index("ix_compras_pendencias_fornecedor_tenant_status", table_name="compras_pendencias_fornecedor")
    op.drop_index(op.f("ix_compras_pendencias_fornecedor_user_id"), table_name="compras_pendencias_fornecedor")
    op.drop_index(op.f("ix_compras_pendencias_fornecedor_pedido_compra_id"), table_name="compras_pendencias_fornecedor")
    op.drop_index(op.f("ix_compras_pendencias_fornecedor_nota_entrada_id"), table_name="compras_pendencias_fornecedor")
    op.drop_index(op.f("ix_compras_pendencias_fornecedor_fornecedor_id"), table_name="compras_pendencias_fornecedor")
    op.drop_index(op.f("ix_compras_pendencias_fornecedor_status"), table_name="compras_pendencias_fornecedor")
    op.drop_index(op.f("ix_compras_pendencias_fornecedor_codigo"), table_name="compras_pendencias_fornecedor")
    op.drop_index(op.f("ix_compras_pendencias_fornecedor_tenant_id"), table_name="compras_pendencias_fornecedor")
    op.drop_index(op.f("ix_compras_pendencias_fornecedor_id"), table_name="compras_pendencias_fornecedor")
    op.drop_table("compras_pendencias_fornecedor")
