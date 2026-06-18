"""add vet consultorios and agendamento room

Revision ID: g8h9i0j1k2l3
Revises: f7g8h9i0j1k2
Create Date: 2026-04-20 16:55:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "g8h9i0j1k2l3"
down_revision = "f7g8h9i0j1k2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vet_consultorios",
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("id", sa.Integer(), sa.Identity(always=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_vet_consultorios_tenant_id", "vet_consultorios", ["tenant_id"])
    op.create_index("ix_vet_consultorios_nome", "vet_consultorios", ["nome"])

    op.add_column("vet_agendamentos", sa.Column("consultorio_id", sa.Integer(), nullable=True))
    op.create_index("ix_vet_agendamentos_consultorio_id", "vet_agendamentos", ["consultorio_id"])
    op.create_foreign_key(
        "fk_vet_agendamentos_consultorio_id",
        "vet_agendamentos",
        "vet_consultorios",
        ["consultorio_id"],
        ["id"],
    )

    op.alter_column("vet_consultorios", "ordem", server_default=None)
    op.alter_column("vet_consultorios", "ativo", server_default=None)


def downgrade() -> None:
    op.drop_constraint("fk_vet_agendamentos_consultorio_id", "vet_agendamentos", type_="foreignkey")
    op.drop_index("ix_vet_agendamentos_consultorio_id", table_name="vet_agendamentos")
    op.drop_column("vet_agendamentos", "consultorio_id")

    op.drop_index("ix_vet_consultorios_nome", table_name="vet_consultorios")
    op.drop_index("ix_vet_consultorios_tenant_id", table_name="vet_consultorios")
    op.drop_table("vet_consultorios")
