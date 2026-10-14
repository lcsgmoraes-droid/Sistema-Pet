"""Celulares adicionais vinculados ao cadastro principal da pessoa.

Revision ID: zzzj20261006a1
Revises: zzzi20261006a1
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "zzzj20261006a1"
down_revision = "zzzi20261006a1"
branch_labels = None
depends_on = None

TABLE = "cliente_contatos"
TENANT_GUARD = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("id", sa.Integer(), sa.Identity(always=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column("numero", sa.String(50), nullable=False),
        sa.Column("numero_digitos", sa.String(20), nullable=False),
        sa.Column("vinculo", sa.String(60), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "numero_digitos", name="uq_cliente_contatos_tenant_numero"),
    )
    op.create_index("ix_cliente_contatos_tenant_id", TABLE, ["tenant_id"])
    op.create_index("ix_cliente_contatos_cliente_id", TABLE, ["cliente_id"])
    op.create_index("ix_cliente_contatos_numero_digitos", TABLE, ["numero_digitos"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute(f"ALTER TABLE {TABLE} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {TABLE} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {TABLE}_tenant_isolation ON {TABLE} "
            f"USING ({TENANT_GUARD}) WITH CHECK ({TENANT_GUARD})"
        )


def downgrade() -> None:
    op.drop_table(TABLE)
