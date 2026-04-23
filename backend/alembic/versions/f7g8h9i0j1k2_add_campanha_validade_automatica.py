"""add campanha validade automatica

Revision ID: f7g8h9i0j1k2
Revises: e6f7a8b9c0d1
Create Date: 2026-04-18 18:20:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "f7g8h9i0j1k2"
down_revision = "e6f7a8b9c0d1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "campanha_validade_automatica",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("aplicar_app", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("aplicar_ecommerce", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("desconto_60_dias", sa.Float(), nullable=False, server_default=sa.text("10")),
        sa.Column("desconto_30_dias", sa.Float(), nullable=False, server_default=sa.text("20")),
        sa.Column("desconto_7_dias", sa.Float(), nullable=False, server_default=sa.text("35")),
        sa.Column("rotulo_publico", sa.String(length=80), nullable=True),
        sa.Column("mensagem_publica", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_campanha_validade_automatica_tenant_id",
        "campanha_validade_automatica",
        ["tenant_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_campanha_validade_automatica_tenant",
        "campanha_validade_automatica",
        ["tenant_id"],
    )

    op.create_table(
        "campanha_validade_exclusoes",
        sa.Column("id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("produto_id", sa.Integer(), nullable=False),
        sa.Column("lote_id", sa.Integer(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("motivo", sa.String(length=120), nullable=True),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["produto_id"], ["produtos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lote_id"], ["produto_lotes.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_campanha_validade_exclusoes_tenant_id",
        "campanha_validade_exclusoes",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_campanha_validade_exclusoes_produto_id",
        "campanha_validade_exclusoes",
        ["produto_id"],
        unique=False,
    )
    op.create_index(
        "ix_campanha_validade_exclusoes_lote_id",
        "campanha_validade_exclusoes",
        ["lote_id"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_campanha_validade_exclusoes_lote_id", table_name="campanha_validade_exclusoes")
    op.drop_index("ix_campanha_validade_exclusoes_produto_id", table_name="campanha_validade_exclusoes")
    op.drop_index("ix_campanha_validade_exclusoes_tenant_id", table_name="campanha_validade_exclusoes")
    op.drop_table("campanha_validade_exclusoes")

    op.drop_constraint(
        "uq_campanha_validade_automatica_tenant",
        "campanha_validade_automatica",
        type_="unique",
    )
    op.drop_index("ix_campanha_validade_automatica_tenant_id", table_name="campanha_validade_automatica")
    op.drop_table("campanha_validade_automatica")
