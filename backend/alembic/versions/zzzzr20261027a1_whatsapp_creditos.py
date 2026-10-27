"""WhatsApp: creditos (franquia mensal + pacotes avulsos) com bloqueio ao esgotar

Revision ID: zzzzr20261027a1
Revises: zzzzq20261026a1
Create Date: 2026-10-27

- `tenant_whatsapp_config`: liga o controle por loja e define a franquia mensal.
  O controle nasce DESLIGADO: nenhuma loja existente passa a ser bloqueada sozinha.
- Movimentos de credito por loja (RLS); pacotes, custos e compras na plataforma.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.tenant_rls_migration import apply_tenant_rls


revision = "zzzzr20261027a1"
down_revision = "zzzzq20261026a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenant_whatsapp_config",
        sa.Column(
            "creditos_controle_ativo",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "tenant_whatsapp_config",
        sa.Column(
            "creditos_franquia_mensal",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    op.create_table(
        "whatsapp_creditos_movimentos",
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
        sa.Column("tipo", sa.String(12), nullable=False),
        sa.Column("fonte", sa.String(10), nullable=False),
        sa.Column("quantidade", sa.Integer(), nullable=False),
        sa.Column("mes", sa.String(7), nullable=False),
        sa.Column("referencia", sa.String(255)),
        sa.Column("compra_id", sa.Integer()),
        sa.Column("descricao", sa.String(200)),
        sa.Column("criado_por", sa.String(255)),
    )
    op.create_index(
        "ix_whatsapp_creditos_movimentos_tenant_id",
        "whatsapp_creditos_movimentos",
        ["tenant_id"],
    )
    op.create_index(
        "ix_whatsapp_creditos_mov_tenant_mes",
        "whatsapp_creditos_movimentos",
        ["tenant_id", "mes"],
    )
    op.create_index(
        "ix_whatsapp_creditos_mov_tenant_tipo",
        "whatsapp_creditos_movimentos",
        ["tenant_id", "tipo"],
    )
    apply_tenant_rls(
        op_module=op,
        sa_module=sa,
        table_names=("whatsapp_creditos_movimentos",),
        enable=True,
    )

    op.create_table(
        "whatsapp_pacotes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("nome", sa.String(80), nullable=False),
        sa.Column("creditos", sa.Integer(), nullable=False),
        sa.Column("preco", sa.Numeric(10, 2), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("criado_por", sa.String(255)),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_table(
        "whatsapp_custos_creditos",
        sa.Column("chave", sa.String(40), primary_key=True),
        sa.Column("creditos", sa.Integer(), nullable=False),
        sa.Column("atualizado_por", sa.String(255)),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_table(
        "whatsapp_compras_pacote",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "pacote_id",
            sa.Integer(),
            sa.ForeignKey("whatsapp_pacotes.id"),
            nullable=False,
        ),
        sa.Column("pacote_nome", sa.String(80), nullable=False),
        sa.Column("creditos", sa.Integer(), nullable=False),
        sa.Column("preco", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.String(12), nullable=False, server_default="pendente"),
        sa.Column("solicitado_por", sa.String(255), nullable=False),
        sa.Column(
            "solicitado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("confirmado_por", sa.String(255)),
        sa.Column("confirmado_em", sa.DateTime(timezone=True)),
        sa.Column("observacao", sa.Text()),
    )
    op.create_index(
        "ix_whatsapp_compras_pacote_tenant_id", "whatsapp_compras_pacote", ["tenant_id"]
    )
    op.create_index(
        "ix_whatsapp_compras_status",
        "whatsapp_compras_pacote",
        ["status", "solicitado_em"],
    )


def downgrade() -> None:
    op.drop_table("whatsapp_compras_pacote")
    op.drop_table("whatsapp_custos_creditos")
    op.drop_table("whatsapp_pacotes")
    op.drop_table("whatsapp_creditos_movimentos")
    op.drop_column("tenant_whatsapp_config", "creditos_franquia_mensal")
    op.drop_column("tenant_whatsapp_config", "creditos_controle_ativo")
