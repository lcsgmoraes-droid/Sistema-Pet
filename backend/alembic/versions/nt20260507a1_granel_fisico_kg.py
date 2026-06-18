"""add granel physical stock support

Revision ID: nt20260507a1
Revises: ns20260507a1
Create Date: 2026-05-07 15:10:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


revision = "nt20260507a1"
down_revision = "ns20260507a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("produtos"):
        colunas_produtos = {
            coluna["name"] for coluna in inspector.get_columns("produtos")
        }
        if "e_granel" not in colunas_produtos:
            op.add_column(
                "produtos",
                sa.Column(
                    "e_granel",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("false"),
                ),
            )

        op.execute(
            """
            UPDATE produtos
               SET e_granel = true,
                   tipo_produto = 'KIT',
                   tipo_kit = 'FISICO',
                   unidade = 'KG',
                   updated_at = now()
             WHERE lower(coalesce(nome, '')) LIKE '%granel%'
            """
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_produtos_tenant_granel "
            "ON produtos (tenant_id, e_granel)"
        )

    if not inspector.has_table("granel_conversoes"):
        op.create_table(
            "granel_conversoes",
            sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
            sa.Column("produto_granel_id", sa.Integer(), nullable=False),
            sa.Column("produto_origem_id", sa.Integer(), nullable=False),
            sa.Column("quantidade_origem", sa.Float(), nullable=False),
            sa.Column("peso_por_unidade_kg", sa.Float(), nullable=False),
            sa.Column("quantidade_granel_kg", sa.Float(), nullable=False),
            sa.Column("estoque_origem_anterior", sa.Float(), nullable=True),
            sa.Column("estoque_origem_novo", sa.Float(), nullable=True),
            sa.Column("estoque_granel_anterior", sa.Float(), nullable=True),
            sa.Column("estoque_granel_novo", sa.Float(), nullable=True),
            sa.Column("documento", sa.String(length=50), nullable=True),
            sa.Column("observacao", sa.Text(), nullable=True),
            sa.Column(
                "status",
                sa.String(length=20),
                nullable=False,
                server_default="confirmado",
            ),
            sa.Column("user_id", sa.Integer(), nullable=False),
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
            sa.ForeignKeyConstraint(["produto_granel_id"], ["produtos.id"]),
            sa.ForeignKeyConstraint(["produto_origem_id"], ["produtos.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_granel_conversoes_tenant_created "
        "ON granel_conversoes (tenant_id, created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_granel_conversoes_granel "
        "ON granel_conversoes (produto_granel_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_granel_conversoes_origem "
        "ON granel_conversoes (produto_origem_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_granel_conversoes_origem")
    op.execute("DROP INDEX IF EXISTS idx_granel_conversoes_granel")
    op.execute("DROP INDEX IF EXISTS idx_granel_conversoes_tenant_created")
    op.drop_table("granel_conversoes")
    op.execute("DROP INDEX IF EXISTS ix_produtos_tenant_granel")
    op.drop_column("produtos", "e_granel")
