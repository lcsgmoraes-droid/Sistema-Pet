"""add appointment reminder configs

Revision ID: zwe20260709a1
Revises: zwd20260708a1
Create Date: 2026-07-09 10:52:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.tenant_rls_migration import TENANT_RLS_GUARD, apply_tenant_rls


revision: str = "zwe20260709a1"
down_revision: Union[str, None] = "zwd20260708a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TENANT_GUARD = TENANT_RLS_GUARD
VET_REMINDER_CONFIG_TABLES = ("vet_lembrete_configuracoes",)


def upgrade() -> None:
    op.add_column(
        "banho_tosa_configuracoes",
        sa.Column(
            "lembretes_agendamento_ativos",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.add_column(
        "banho_tosa_configuracoes",
        sa.Column(
            "lembrete_agendamento_1d_ativo",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.add_column(
        "banho_tosa_configuracoes",
        sa.Column(
            "lembrete_agendamento_horas_ativo",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.add_column(
        "banho_tosa_configuracoes",
        sa.Column(
            "lembrete_agendamento_horas_antes",
            sa.Integer(),
            server_default="1",
            nullable=False,
        ),
    )
    op.add_column(
        "notification_queue", sa.Column("source", sa.String(length=80), nullable=True)
    )
    op.add_column(
        "notification_queue", sa.Column("kind", sa.String(length=80), nullable=True)
    )
    op.add_column(
        "notification_queue",
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_table(
        "vet_lembrete_configuracoes",
        sa.Column(
            "lembretes_agendamento_ativos",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "lembrete_agendamento_1d_ativo",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "lembrete_agendamento_horas_ativo",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "lembrete_agendamento_horas_antes",
            sa.Integer(),
            server_default="1",
            nullable=False,
        ),
        sa.Column("ativo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", name="uq_vet_lembrete_config_tenant"),
    )
    op.create_index(
        "ix_vet_lembrete_configuracoes_tenant_id",
        "vet_lembrete_configuracoes",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_vet_lembrete_config_tenant_ativo",
        "vet_lembrete_configuracoes",
        ["tenant_id", "ativo"],
        unique=False,
    )
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=VET_REMINDER_CONFIG_TABLES,
        enable=True,
    )


def downgrade() -> None:
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=VET_REMINDER_CONFIG_TABLES,
        enable=False,
    )
    op.drop_index(
        "ix_vet_lembrete_config_tenant_ativo",
        table_name="vet_lembrete_configuracoes",
    )
    op.drop_index(
        "ix_vet_lembrete_configuracoes_tenant_id",
        table_name="vet_lembrete_configuracoes",
    )
    op.drop_table("vet_lembrete_configuracoes")
    op.drop_column("notification_queue", "payload")
    op.drop_column("notification_queue", "kind")
    op.drop_column("notification_queue", "source")
    op.drop_column("banho_tosa_configuracoes", "lembrete_agendamento_horas_antes")
    op.drop_column("banho_tosa_configuracoes", "lembrete_agendamento_horas_ativo")
    op.drop_column("banho_tosa_configuracoes", "lembrete_agendamento_1d_ativo")
    op.drop_column("banho_tosa_configuracoes", "lembretes_agendamento_ativos")
