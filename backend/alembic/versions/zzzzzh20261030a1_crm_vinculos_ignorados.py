"""CRM: pessoas que o usuario pediu para nao sugerir como vinculo de um card

Revision ID: zzzzzh20261030a1
Revises: zzzzzg20261029a1
Create Date: 2026-10-30
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.tenant_rls_migration import apply_tenant_rls


revision = "zzzzzh20261030a1"
down_revision = "zzzzzg20261029a1"
branch_labels = None
depends_on = None

TABELA = "crm_vinculos_ignorados"


def upgrade() -> None:
    op.create_table(
        TABELA,
        sa.Column("id", sa.Integer(), sa.Identity(always=True), primary_key=True),
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
        sa.Column(
            "lead_id", sa.Integer(), sa.ForeignKey("crm_leads.id"), nullable=False
        ),
        sa.Column(
            "cliente_id", sa.Integer(), sa.ForeignKey("clientes.id"), nullable=False
        ),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
    )
    op.create_index(f"ix_{TABELA}_tenant_id", TABELA, ["tenant_id"])
    op.create_index(
        "uq_crm_vinculos_ignorados",
        TABELA,
        ["tenant_id", "lead_id", "cliente_id"],
        unique=True,
    )
    apply_tenant_rls(op_module=op, sa_module=sa, table_names=(TABELA,), enable=True)


def downgrade() -> None:
    op.drop_table(TABELA)
