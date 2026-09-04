"""adiciona fracionamento de estoque para uso clinico

Revision ID: zzc20260903a1
Revises: zzb20260903a1
Create Date: 2026-09-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.tenant_rls_migration import apply_tenant_rls


revision = "zzc20260903a1"
down_revision = "zzb20260903a1"
branch_labels = None
depends_on = None


TABLES = (
    "estoque_fracionamento_vinculos",
    "estoque_fracionamento_conversoes",
)


def _tenant_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    ]


def upgrade() -> None:
    op.create_table(
        "estoque_fracionamento_vinculos",
        sa.Column("produto_origem_id", sa.Integer(), nullable=False),
        sa.Column("produto_destino_id", sa.Integer(), nullable=False),
        sa.Column("fator_conversao", sa.Float(), nullable=False),
        sa.Column("validade_apos_abertura_dias", sa.Integer(), nullable=True),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("ativo", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        *_tenant_columns(),
        sa.ForeignKeyConstraint(["produto_origem_id"], ["produtos.id"]),
        sa.ForeignKeyConstraint(["produto_destino_id"], ["produtos.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint(
            "tenant_id",
            "produto_origem_id",
            "produto_destino_id",
            name="uq_estoque_fracionamento_origem_destino",
        ),
    )
    op.create_index(
        "ix_estoque_fracionamento_vinculos_tenant_id",
        "estoque_fracionamento_vinculos",
        ["tenant_id"],
    )
    op.create_index(
        "ix_estoque_fracionamento_vinculo_origem",
        "estoque_fracionamento_vinculos",
        ["tenant_id", "produto_origem_id"],
    )
    op.create_index(
        "ix_estoque_fracionamento_vinculo_destino",
        "estoque_fracionamento_vinculos",
        ["tenant_id", "produto_destino_id"],
    )

    op.create_table(
        "estoque_fracionamento_conversoes",
        sa.Column("vinculo_id", sa.Integer(), nullable=False),
        sa.Column("produto_origem_id", sa.Integer(), nullable=False),
        sa.Column("produto_destino_id", sa.Integer(), nullable=False),
        sa.Column("quantidade_origem", sa.Float(), nullable=False),
        sa.Column("fator_conversao", sa.Float(), nullable=False),
        sa.Column("quantidade_destino", sa.Float(), nullable=False),
        sa.Column("unidade_origem", sa.String(length=10), nullable=False),
        sa.Column("unidade_destino", sa.String(length=10), nullable=False),
        sa.Column("estoque_origem_anterior", sa.Float(), nullable=False),
        sa.Column("estoque_origem_novo", sa.Float(), nullable=False),
        sa.Column("estoque_destino_anterior", sa.Float(), nullable=False),
        sa.Column("estoque_destino_novo", sa.Float(), nullable=False),
        sa.Column("custo_origem_unitario", sa.Float(), nullable=False),
        sa.Column("custo_destino_unitario", sa.Float(), nullable=False),
        sa.Column("lotes_origem_consumidos", sa.JSON(), nullable=True),
        sa.Column("lotes_destino_criados", sa.JSON(), nullable=True),
        sa.Column("aberto_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "validade_apos_abertura_em", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("documento", sa.String(length=50), nullable=True),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.String(length=20), server_default="confirmado", nullable=False
        ),
        sa.Column("user_id", sa.Integer(), nullable=False),
        *_tenant_columns(),
        sa.ForeignKeyConstraint(["vinculo_id"], ["estoque_fracionamento_vinculos.id"]),
        sa.ForeignKeyConstraint(["produto_origem_id"], ["produtos.id"]),
        sa.ForeignKeyConstraint(["produto_destino_id"], ["produtos.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index(
        "ix_estoque_fracionamento_conversoes_tenant_id",
        "estoque_fracionamento_conversoes",
        ["tenant_id"],
    )
    op.create_index(
        "ix_estoque_fracionamento_conversao_created",
        "estoque_fracionamento_conversoes",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_estoque_fracionamento_conversao_origem",
        "estoque_fracionamento_conversoes",
        ["tenant_id", "produto_origem_id"],
    )
    op.create_index(
        "ix_estoque_fracionamento_conversao_destino",
        "estoque_fracionamento_conversoes",
        ["tenant_id", "produto_destino_id"],
    )

    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=TABLES,
        enable=False,
    )
    op.drop_table("estoque_fracionamento_conversoes")
    op.drop_table("estoque_fracionamento_vinculos")
