"""add global feature rollout metrics

Revision ID: zwv20260822a1
Revises: zwu20260822a1
"""

from alembic import op
import sqlalchemy as sa


revision = "zwv20260822a1"
down_revision = "zwu20260822a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "evolucao_funcionalidade_usos" in tables:
        return

    op.create_table(
        "evolucao_funcionalidade_usos",
        sa.Column("item_id", sa.String(length=120), nullable=False),
        sa.Column("usos_total", sa.Integer(), server_default="0", nullable=False),
        sa.Column("primeiro_uso_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ultimo_uso_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("limiar_teste_atingido_em", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("item_id"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if "evolucao_funcionalidade_usos" in set(sa.inspect(bind).get_table_names()):
        op.drop_table("evolucao_funcionalidade_usos")
