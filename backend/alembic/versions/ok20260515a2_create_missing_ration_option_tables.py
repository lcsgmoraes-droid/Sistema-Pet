"""create missing ration option tables

Revision ID: ok20260515a2
Revises: oj20260515a1
Create Date: 2026-05-15 15:45:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "ok20260515a2"
down_revision = "oj20260515a1"
branch_labels = None
depends_on = None


NAMED_OPTION_TABLES = (
    "linhas_racao",
    "portes_animal",
    "fases_publico",
    "tipos_tratamento",
    "sabores_proteina",
)


def _create_named_option_table(table_name: str) -> None:
    op.create_table(
        table_name,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nome", sa.String(length=100), nullable=False),
        sa.Column("descricao", sa.String(length=255), nullable=True),
        sa.Column("ordem", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("ativo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=False), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=False), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def _create_package_weights_table() -> None:
    op.create_table(
        "apresentacoes_peso",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("peso_kg", sa.Float(), nullable=False),
        sa.Column("descricao", sa.String(length=100), nullable=True),
        sa.Column("ordem", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("ativo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=False), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=False), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table_name in NAMED_OPTION_TABLES:
        if not inspector.has_table(table_name):
            _create_named_option_table(table_name)
        op.execute(f"CREATE INDEX IF NOT EXISTS ix_{table_name}_tenant_id ON {table_name} (tenant_id)")
        op.execute(f"CREATE INDEX IF NOT EXISTS ix_{table_name}_nome ON {table_name} (nome)")

    if not inspector.has_table("apresentacoes_peso"):
        _create_package_weights_table()
    op.execute("CREATE INDEX IF NOT EXISTS ix_apresentacoes_peso_tenant_id ON apresentacoes_peso (tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_apresentacoes_peso_peso_kg ON apresentacoes_peso (peso_kg)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS apresentacoes_peso")
    for table_name in reversed(NAMED_OPTION_TABLES):
        op.execute(f"DROP TABLE IF EXISTS {table_name}")
