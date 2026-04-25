"""add vet internacao agenda config

Revision ID: i0j1k2l3m4n5
Revises: h9i0j1k2l3m4
Create Date: 2026-04-24 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "i0j1k2l3m4n5"
down_revision = "h9i0j1k2l3m4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vet_internacao_configuracoes",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("total_baias", sa.Integer(), nullable=False, server_default=sa.text("12")),
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vet_internacao_configuracoes_tenant_id", "vet_internacao_configuracoes", ["tenant_id"])
    op.create_index("ix_vet_internacao_configuracoes_user_id", "vet_internacao_configuracoes", ["user_id"])
    op.create_index("ux_vet_internacao_config_tenant", "vet_internacao_configuracoes", ["tenant_id"], unique=True)

    op.create_table(
        "vet_internacao_procedimentos_agenda",
        sa.Column("internacao_id", sa.Integer(), nullable=False),
        sa.Column("pet_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("procedimento_evolucao_id", sa.Integer(), nullable=True),
        sa.Column("horario_agendado", sa.DateTime(timezone=True), nullable=False),
        sa.Column("medicamento", sa.String(length=255), nullable=False),
        sa.Column("dose", sa.String(length=255), nullable=True),
        sa.Column("via", sa.String(length=100), nullable=True),
        sa.Column("quantidade_prevista", sa.Float(), nullable=True),
        sa.Column("quantidade_executada", sa.Float(), nullable=True),
        sa.Column("quantidade_desperdicio", sa.Float(), nullable=True),
        sa.Column("unidade_quantidade", sa.String(length=50), nullable=True),
        sa.Column("lembrete_minutos", sa.Integer(), nullable=False, server_default=sa.text("30")),
        sa.Column("observacoes_agenda", sa.Text(), nullable=True),
        sa.Column("executado_por", sa.String(length=255), nullable=True),
        sa.Column("horario_execucao", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observacao_execucao", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="agendado"),
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["internacao_id"], ["vet_internacoes.id"]),
        sa.ForeignKeyConstraint(["pet_id"], ["pets.id"]),
        sa.ForeignKeyConstraint(["procedimento_evolucao_id"], ["vet_evolucoes_internacao.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_vet_internacao_procedimentos_agenda_horario_agendado",
        "vet_internacao_procedimentos_agenda",
        ["horario_agendado"],
    )
    op.create_index("ix_vet_internacao_procedimentos_agenda_internacao_id", "vet_internacao_procedimentos_agenda", ["internacao_id"])
    op.create_index("ix_vet_internacao_procedimentos_agenda_pet_id", "vet_internacao_procedimentos_agenda", ["pet_id"])
    op.create_index(
        "ix_vet_internacao_procedimentos_agenda_procedimento_evolucao_id",
        "vet_internacao_procedimentos_agenda",
        ["procedimento_evolucao_id"],
    )
    op.create_index("ix_vet_internacao_procedimentos_agenda_status", "vet_internacao_procedimentos_agenda", ["status"])
    op.create_index("ix_vet_internacao_procedimentos_agenda_tenant_id", "vet_internacao_procedimentos_agenda", ["tenant_id"])
    op.create_index("ix_vet_internacao_procedimentos_agenda_user_id", "vet_internacao_procedimentos_agenda", ["user_id"])

    op.alter_column("vet_internacao_configuracoes", "total_baias", server_default=None)
    op.alter_column("vet_internacao_procedimentos_agenda", "lembrete_minutos", server_default=None)
    op.alter_column("vet_internacao_procedimentos_agenda", "status", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_vet_internacao_procedimentos_agenda_user_id", table_name="vet_internacao_procedimentos_agenda")
    op.drop_index("ix_vet_internacao_procedimentos_agenda_tenant_id", table_name="vet_internacao_procedimentos_agenda")
    op.drop_index("ix_vet_internacao_procedimentos_agenda_status", table_name="vet_internacao_procedimentos_agenda")
    op.drop_index(
        "ix_vet_internacao_procedimentos_agenda_procedimento_evolucao_id",
        table_name="vet_internacao_procedimentos_agenda",
    )
    op.drop_index("ix_vet_internacao_procedimentos_agenda_pet_id", table_name="vet_internacao_procedimentos_agenda")
    op.drop_index("ix_vet_internacao_procedimentos_agenda_internacao_id", table_name="vet_internacao_procedimentos_agenda")
    op.drop_index(
        "ix_vet_internacao_procedimentos_agenda_horario_agendado",
        table_name="vet_internacao_procedimentos_agenda",
    )
    op.drop_table("vet_internacao_procedimentos_agenda")

    op.drop_index("ux_vet_internacao_config_tenant", table_name="vet_internacao_configuracoes")
    op.drop_index("ix_vet_internacao_configuracoes_user_id", table_name="vet_internacao_configuracoes")
    op.drop_index("ix_vet_internacao_configuracoes_tenant_id", table_name="vet_internacao_configuracoes")
    op.drop_table("vet_internacao_configuracoes")
