"""create offer studio publications

Revision ID: zxm20260829a1
Revises: zxl20260828a1
Create Date: 2026-08-29
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "zxm20260829a1"
down_revision = "zxl20260828a1"
branch_labels = None
depends_on = None


PUBLICACOES = "oferta_publicacoes"
TOKENS = "oferta_publicacao_tokens"
POLICY = "oferta_publicacoes_tenant_isolation"
TENANT_GUARD = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(PUBLICACOES):
        op.create_table(
            PUBLICACOES,
            sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("titulo", sa.String(length=160), nullable=False),
            sa.Column("periodicidade", sa.String(length=20), nullable=False),
            sa.Column("tipo_arte", sa.String(length=24), nullable=False),
            sa.Column("formato", sa.String(length=24), nullable=False),
            sa.Column("inicio_em", sa.DateTime(timezone=True), nullable=False),
            sa.Column("fim_em", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
            sa.Column("desativada_em", sa.DateTime(timezone=True), nullable=True),
            sa.Column("imagens_urls", sa.JSON(), nullable=False),
            sa.Column("produtos_snapshot", sa.JSON(), nullable=False),
            sa.Column("configuracao", sa.JSON(), nullable=False),
            sa.Column("criado_por_id", sa.Integer(), nullable=False),
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
            sa.ForeignKeyConstraint(["criado_por_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_oferta_publicacoes_tenant_id", PUBLICACOES, ["tenant_id"])

    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(TOKENS):
        op.create_table(
            TOKENS,
            sa.Column("token", sa.String(length=64), nullable=False),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("publicacao_id", sa.Integer(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["publicacao_id"], [f"{PUBLICACOES}.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("token"),
            sa.UniqueConstraint("publicacao_id"),
        )
        op.create_index("ix_oferta_publicacao_tokens_tenant_id", TOKENS, ["tenant_id"])

    if op.get_bind().dialect.name == "postgresql":
        op.execute(f"ALTER TABLE {PUBLICACOES} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {PUBLICACOES} FORCE ROW LEVEL SECURITY")
        policies = {
            row[0]
            for row in op.get_bind().execute(
                sa.text("SELECT policyname FROM pg_policies WHERE tablename = :table"),
                {"table": PUBLICACOES},
            )
        }
        if POLICY not in policies:
            op.execute(
                f"CREATE POLICY {POLICY} ON {PUBLICACOES} "
                f"USING ({TENANT_GUARD}) WITH CHECK ({TENANT_GUARD})"
            )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table(TOKENS):
        op.drop_table(TOKENS)
    if inspector.has_table(PUBLICACOES):
        op.drop_table(PUBLICACOES)
