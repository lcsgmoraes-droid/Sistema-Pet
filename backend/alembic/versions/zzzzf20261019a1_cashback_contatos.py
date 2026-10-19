"""Histórico de contatos e status do CRM de cashback, isolado por empresa."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "zzzzf20261019a1"
down_revision = "zzzze20261019a1"
branch_labels = None
depends_on = None

TABLE_NAME = "cashback_contatos"
TENANT_GUARD = "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"


def upgrade():
    op.create_table(
        TABLE_NAME,
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
            "cliente_id", sa.Integer(), sa.ForeignKey("clientes.id"), nullable=False
        ),
        sa.Column(
            "usuario_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")
        ),
        sa.Column("operador_nome", sa.String(200), nullable=False),
        sa.Column("acao", sa.String(40), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("mensagem", sa.Text()),
        sa.Column("observacao", sa.Text()),
        sa.Column("telefone", sa.String(20)),
        sa.Column("proximo_contato_em", sa.Date()),
        sa.Column("saldo_cashback", sa.Numeric(12, 2), nullable=False),
        sa.Column("chave_cliente", sa.String(36), nullable=False),
        sa.UniqueConstraint(
            "tenant_id",
            "cliente_id",
            "acao",
            "chave_cliente",
            name="uq_cashback_contatos_requisicao",
        ),
    )
    op.create_index("ix_cashback_contatos_tenant_id", TABLE_NAME, ["tenant_id"])
    op.create_index(
        "ix_cashback_contatos_tenant_cliente_id",
        TABLE_NAME,
        ["tenant_id", "cliente_id", "id"],
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute(f"ALTER TABLE {TABLE_NAME} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {TABLE_NAME} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {TABLE_NAME}_tenant_isolation ON {TABLE_NAME} USING ({TENANT_GUARD}) WITH CHECK ({TENANT_GUARD})"
        )


def downgrade():
    op.drop_table(TABLE_NAME)
