"""livro-razao das mensagens de WhatsApp (base do repasse de custos da Meta)

Revision ID: zzzzp20261026a1
Revises: zzzzo20261026a1
Create Date: 2026-10-26

Uma linha por mensagem enviada ou recebida, por loja, com estado de entrega,
categoria de cobranca, janela de 24 horas e motivo de falha. Isolada por loja (RLS).
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.tenant_rls_migration import apply_tenant_rls


revision = "zzzzp20261026a1"
down_revision = "zzzzo20261026a1"
branch_labels = None
depends_on = None

TABELA = "whatsapp_ledger"


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
        sa.Column("direcao", sa.String(10), nullable=False),
        sa.Column("origem", sa.String(20), nullable=False),
        sa.Column("provedor", sa.String(20), nullable=False),
        sa.Column("session_id", sa.String(64)),
        sa.Column("message_id", sa.String(64)),
        sa.Column("wa_message_id", sa.String(255)),
        sa.Column("telefone", sa.String(40)),
        sa.Column("tipo_conteudo", sa.String(20), nullable=False, server_default="texto"),
        sa.Column("template_nome", sa.String(120)),
        sa.Column("template_categoria", sa.String(20)),
        sa.Column("janela_24h", sa.Boolean()),
        sa.Column("estado", sa.String(12), nullable=False),
        sa.Column(
            "ocorrido_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("enviado_em", sa.DateTime(timezone=True)),
        sa.Column("entregue_em", sa.DateTime(timezone=True)),
        sa.Column("lido_em", sa.DateTime(timezone=True)),
        sa.Column("falhou_em", sa.DateTime(timezone=True)),
        sa.Column("erro_codigo", sa.String(20)),
        sa.Column("erro_mensagem", sa.String(300)),
        sa.Column("cobravel", sa.Boolean()),
        sa.Column("categoria_cobranca", sa.String(30)),
        sa.Column("modelo_de_preco", sa.String(30)),
        sa.Column("custo_estimado_centavos", sa.BigInteger()),
        sa.Column("moeda", sa.String(3)),
        sa.Column("lead_id", sa.Integer()),
        sa.Column("observacao", sa.Text()),
    )
    op.create_index(f"ix_{TABELA}_tenant_id", TABELA, ["tenant_id"])
    op.create_index(
        "ux_whatsapp_ledger_tenant_wa_message",
        TABELA,
        ["tenant_id", "wa_message_id"],
        unique=True,
        postgresql_where=sa.text("wa_message_id IS NOT NULL"),
    )
    op.create_index(
        "ix_whatsapp_ledger_tenant_data", TABELA, ["tenant_id", "ocorrido_em"]
    )
    op.create_index("ix_whatsapp_ledger_sessao", TABELA, ["tenant_id", "session_id"])
    apply_tenant_rls(op_module=op, sa_module=sa, table_names=(TABELA,), enable=True)


def downgrade() -> None:
    op.drop_table(TABELA)
