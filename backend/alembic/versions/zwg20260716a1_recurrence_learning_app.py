"""add recurrence learning metadata and app reminders

Revision ID: zwg20260716a1
Revises: zwf20260715b1
Create Date: 2026-07-16
"""

from alembic import op
import sqlalchemy as sa


revision = "zwg20260716a1"
down_revision = "zwf20260715b1"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "lembretes",
        "pet_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.add_column(
        "lembretes", sa.Column("origem_intervalo", sa.String(length=30), nullable=True)
    )
    op.add_column(
        "lembretes", sa.Column("intervalo_estimado_dias", sa.Integer(), nullable=True)
    )
    op.add_column(
        "lembretes", sa.Column("confianca_recorrencia", sa.Float(), nullable=True)
    )
    op.add_column(
        "lembretes",
        sa.Column(
            "amostras_recorrencia",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.execute(
        "UPDATE lembretes SET metodo_notificacao = 'app' "
        "WHERE metodo_notificacao IS NULL OR metodo_notificacao <> 'app'"
    )
    op.alter_column(
        "lembretes",
        "metodo_notificacao",
        existing_type=sa.String(length=50),
        server_default="app",
        existing_nullable=True,
    )
    op.create_index(
        "ix_lembretes_tenant_status_notificacao",
        "lembretes",
        ["tenant_id", "status", "notificacao_enviada", "data_notificacao_7_dias"],
        unique=False,
    )
    op.create_index(
        "ix_lembretes_tenant_cliente_produto_status",
        "lembretes",
        ["tenant_id", "cliente_id", "produto_id", "status"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_lembretes_tenant_cliente_produto_status", table_name="lembretes"
    )
    op.drop_index("ix_lembretes_tenant_status_notificacao", table_name="lembretes")
    op.alter_column(
        "lembretes",
        "metodo_notificacao",
        existing_type=sa.String(length=50),
        server_default=None,
        existing_nullable=True,
    )
    op.drop_column("lembretes", "amostras_recorrencia")
    op.drop_column("lembretes", "confianca_recorrencia")
    op.drop_column("lembretes", "intervalo_estimado_dias")
    op.drop_column("lembretes", "origem_intervalo")
    # Lembretes aprendidos sem pet nao existiam antes desta versao.
    op.execute("DELETE FROM lembretes WHERE pet_id IS NULL")
    op.alter_column(
        "lembretes",
        "pet_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
