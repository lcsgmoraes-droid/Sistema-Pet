"""Adiciona histórico de contatos de aniversários.

Revision ID: zzx20260919a1
Revises: zzw20260919a1
Create Date: 2026-09-19
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "zzx20260919a1"
down_revision = "zzw20260919a1"
branch_labels = None
depends_on = None

TABLE_NAME = "aniversarios_contatos"
POLICY_NAME = f"{TABLE_NAME}_tenant_isolation"
TENANT_GUARD = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def upgrade() -> None:
    op.create_table(
        TABLE_NAME,
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column("pet_id", sa.Integer(), nullable=True),
        sa.Column("aniversario_em", sa.Date(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("notification_queue_id", sa.BigInteger(), nullable=True),
        sa.Column("canal", sa.String(length=20), nullable=False),
        sa.Column("acao", sa.String(length=40), nullable=False),
        sa.Column(
            "status", sa.String(length=30), server_default="registrado", nullable=False
        ),
        sa.Column("mensagem", sa.Text(), nullable=False),
        sa.Column("resultado", sa.String(length=120), nullable=True),
        sa.Column("idempotency_key", sa.String(length=300), nullable=True),
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
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pet_id"], ["pets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["usuario_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["notification_queue_id"],
            ["notification_queue.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "idempotency_key",
            name="uq_aniversarios_contatos_tenant_idempotency",
        ),
    )
    op.create_index("ix_aniversarios_contatos_tenant_id", TABLE_NAME, ["tenant_id"])
    op.create_index(
        "ix_aniversarios_contatos_tenant_evento",
        TABLE_NAME,
        ["tenant_id", "tipo", "aniversario_em", "cliente_id", "pet_id"],
    )
    op.create_index(
        "ix_aniversarios_contatos_tenant_canal_created",
        TABLE_NAME,
        ["tenant_id", "canal", "created_at"],
    )

    if op.get_bind().dialect.name == "postgresql":
        op.execute(f"ALTER TABLE {TABLE_NAME} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {TABLE_NAME} FORCE ROW LEVEL SECURITY")
        op.execute(f"DROP POLICY IF EXISTS {POLICY_NAME} ON {TABLE_NAME}")
        op.execute(
            f"CREATE POLICY {POLICY_NAME} ON {TABLE_NAME} "
            f"USING ({TENANT_GUARD}) WITH CHECK ({TENANT_GUARD})"
        )


def downgrade() -> None:
    op.drop_table(TABLE_NAME)
