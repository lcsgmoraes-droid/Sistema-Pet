"""create quick no-sale records and requested items

Revision ID: zxh20260827a1
Revises: zxg20260827a1
Create Date: 2026-08-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.tenant_rls_migration import apply_tenant_rls


revision = "zxh20260827a1"
down_revision = "zxg20260827a1"
branch_labels = None
depends_on = None


MOTIVOS = (
    "produto_sem_estoque",
    "produto_nao_trabalhado",
    "variacao_indisponivel",
    "preco",
    "forma_pagamento",
    "cliente_pesquisando",
    "demora_atendimento",
    "comprou_concorrente",
    "outro",
)


def upgrade() -> None:
    motivo_sql = ", ".join(f"'{motivo}'" for motivo in MOTIVOS)

    op.create_table(
        "nao_vendas",
        sa.Column("cliente_id", sa.Integer(), nullable=True),
        sa.Column("usuario_registrou_id", sa.Integer(), nullable=False),
        sa.Column("cliente_nome", sa.String(length=255), nullable=True),
        sa.Column("cliente_telefone", sa.String(length=50), nullable=True),
        sa.Column("motivo", sa.String(length=40), nullable=False),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("valor_estimado_total", sa.Numeric(12, 2), nullable=True),
        sa.Column("origem", sa.String(length=30), server_default="pdv", nullable=False),
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
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
        sa.CheckConstraint(f"motivo IN ({motivo_sql})", name="ck_nao_vendas_motivo"),
        sa.CheckConstraint(
            "valor_estimado_total IS NULL OR valor_estimado_total >= 0",
            name="ck_nao_vendas_valor_estimado",
        ),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["usuario_registrou_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_nao_vendas_tenant_id", "nao_vendas", ["tenant_id"])
    op.create_index("ix_nao_vendas_cliente_id", "nao_vendas", ["cliente_id"])
    op.create_index(
        "ix_nao_vendas_usuario_registrou_id",
        "nao_vendas",
        ["usuario_registrou_id"],
    )
    op.create_index("ix_nao_vendas_motivo", "nao_vendas", ["motivo"])
    op.create_index(
        "ix_nao_vendas_tenant_created_at",
        "nao_vendas",
        ["tenant_id", "created_at"],
    )

    op.create_table(
        "nao_venda_itens",
        sa.Column("nao_venda_id", sa.Integer(), nullable=False),
        sa.Column("produto_id", sa.Integer(), nullable=True),
        sa.Column("marca_id", sa.Integer(), nullable=True),
        sa.Column("fornecedor_id", sa.Integer(), nullable=True),
        sa.Column("produto_nome", sa.String(length=200), nullable=False),
        sa.Column("sku", sa.String(length=50), nullable=True),
        sa.Column("marca_nome", sa.String(length=100), nullable=True),
        sa.Column("fornecedor_nome", sa.String(length=255), nullable=True),
        sa.Column("quantidade", sa.Numeric(12, 4), server_default="1", nullable=False),
        sa.Column("valor_unitario_estimado", sa.Numeric(12, 2), nullable=True),
        sa.Column(
            "adicionado_lista_espera",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
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
        sa.CheckConstraint("quantidade > 0", name="ck_nao_venda_itens_quantidade"),
        sa.CheckConstraint(
            "valor_unitario_estimado IS NULL OR valor_unitario_estimado >= 0",
            name="ck_nao_venda_itens_valor",
        ),
        sa.ForeignKeyConstraint(
            ["nao_venda_id"], ["nao_vendas.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["produto_id"], ["produtos.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["marca_id"], ["marcas.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["fornecedor_id"], ["clientes.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_nao_venda_itens_tenant_id", "nao_venda_itens", ["tenant_id"])
    op.create_index(
        "ix_nao_venda_itens_nao_venda_id", "nao_venda_itens", ["nao_venda_id"]
    )
    op.create_index("ix_nao_venda_itens_produto_id", "nao_venda_itens", ["produto_id"])
    op.create_index("ix_nao_venda_itens_marca_id", "nao_venda_itens", ["marca_id"])
    op.create_index(
        "ix_nao_venda_itens_fornecedor_id", "nao_venda_itens", ["fornecedor_id"]
    )
    op.create_index(
        "ix_nao_venda_itens_tenant_produto",
        "nao_venda_itens",
        ["tenant_id", "produto_id"],
    )

    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=("nao_vendas", "nao_venda_itens"),
        enable=True,
    )


def downgrade() -> None:
    op.drop_table("nao_venda_itens")
    op.drop_table("nao_vendas")
