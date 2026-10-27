"""WhatsApp: tarifas da Meta, custo estimado por mensagem e fechamento mensal

Revision ID: zzzzq20261026a1
Revises: zzzzp20261026a1
Create Date: 2026-10-26

- `whatsapp_ledger.custo_estimado` (reais, com fracao de centavo) substitui
  `custo_estimado_centavos` (a Meta cobra frações de centavo por mensagem).
- `whatsapp_tarifas` e `whatsapp_fechamentos` sao tabelas da plataforma (OPS).
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "zzzzq20261026a1"
down_revision = "zzzzp20261026a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("whatsapp_ledger", "custo_estimado_centavos")
    op.add_column("whatsapp_ledger", sa.Column("custo_estimado", sa.Numeric(14, 6)))

    op.create_table(
        "whatsapp_tarifas",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("categoria", sa.String(30), nullable=False),
        sa.Column("moeda", sa.String(3), nullable=False, server_default="BRL"),
        sa.Column("valor", sa.Numeric(12, 6), nullable=False),
        sa.Column("vigente_desde", sa.Date(), nullable=False),
        sa.Column("criado_por", sa.String(255)),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "categoria", "vigente_desde", name="uq_whatsapp_tarifas_categoria_data"
        ),
    )
    op.create_table(
        "whatsapp_fechamentos",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mes", sa.String(7), nullable=False),
        sa.Column("enviadas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recebidas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("falhas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cobraveis", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cobraveis_sem_tarifa", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("por_categoria", sa.Text()),
        sa.Column("custo_estimado", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("margem_percentual", sa.Numeric(6, 2), nullable=False, server_default="0"),
        sa.Column("valor_repasse", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("fatura_meta", sa.Numeric(14, 2)),
        sa.Column("divergencia", sa.Numeric(14, 2)),
        sa.Column("observacao", sa.Text()),
        sa.Column("conferido", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("fechado_por", sa.String(255), nullable=False),
        sa.Column(
            "fechado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("tenant_id", "mes", name="uq_whatsapp_fechamentos_tenant_mes"),
    )
    op.create_index("ix_whatsapp_fechamentos_mes", "whatsapp_fechamentos", ["mes"])


def downgrade() -> None:
    op.drop_table("whatsapp_fechamentos")
    op.drop_table("whatsapp_tarifas")
    op.drop_column("whatsapp_ledger", "custo_estimado")
    op.add_column("whatsapp_ledger", sa.Column("custo_estimado_centavos", sa.BigInteger()))
