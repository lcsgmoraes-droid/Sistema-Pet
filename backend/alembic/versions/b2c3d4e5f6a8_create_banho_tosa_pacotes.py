"""create banho tosa pacotes

Revision ID: b2c3d4e5f6a8
Revises: a1b2c3d4e5f7
Create Date: 2026-04-26 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID


revision: str = "b2c3d4e5f6a8"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tenant_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "banho_tosa_pacotes",
        *_tenant_columns(),
        sa.Column("nome", sa.String(160), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("servico_id", sa.Integer(), sa.ForeignKey("banho_tosa_servicos.id"), nullable=True),
        sa.Column("quantidade_creditos", sa.Numeric(12, 3), nullable=False, server_default="1"),
        sa.Column("validade_dias", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("preco", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "nome", name="uq_bt_pacotes_tenant_nome"),
    )
    op.create_index("ix_banho_tosa_pacotes_tenant_id", "banho_tosa_pacotes", ["tenant_id"])
    op.create_index("ix_bt_pacotes_nome", "banho_tosa_pacotes", ["nome"])
    op.create_index("ix_bt_pacotes_servico_id", "banho_tosa_pacotes", ["servico_id"])
    op.create_index("ix_bt_pacotes_tenant_ativo", "banho_tosa_pacotes", ["tenant_id", "ativo"])

    op.create_table(
        "banho_tosa_pacote_creditos",
        *_tenant_columns(),
        sa.Column("pacote_id", sa.Integer(), sa.ForeignKey("banho_tosa_pacotes.id"), nullable=False),
        sa.Column("cliente_id", sa.Integer(), sa.ForeignKey("clientes.id"), nullable=False),
        sa.Column("pet_id", sa.Integer(), sa.ForeignKey("pets.id"), nullable=True),
        sa.Column("venda_id", sa.Integer(), sa.ForeignKey("vendas.id"), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="ativo"),
        sa.Column("creditos_total", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("creditos_usados", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("creditos_cancelados", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("data_inicio", sa.Date(), nullable=False),
        sa.Column("data_validade", sa.Date(), nullable=False),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_banho_tosa_pacote_creditos_tenant_id", "banho_tosa_pacote_creditos", ["tenant_id"])
    op.create_index("ix_bt_creditos_pacote_id", "banho_tosa_pacote_creditos", ["pacote_id"])
    op.create_index("ix_bt_creditos_cliente_id", "banho_tosa_pacote_creditos", ["cliente_id"])
    op.create_index("ix_bt_creditos_pet_id", "banho_tosa_pacote_creditos", ["pet_id"])
    op.create_index("ix_bt_creditos_venda_id", "banho_tosa_pacote_creditos", ["venda_id"])
    op.create_index("ix_bt_creditos_status", "banho_tosa_pacote_creditos", ["status"])
    op.create_index("ix_bt_creditos_validade", "banho_tosa_pacote_creditos", ["data_validade"])
    op.create_index("ix_bt_creditos_cliente_pet", "banho_tosa_pacote_creditos", ["tenant_id", "cliente_id", "pet_id"])
    op.create_index("ix_bt_creditos_status_validade", "banho_tosa_pacote_creditos", ["tenant_id", "status", "data_validade"])

    op.create_table(
        "banho_tosa_pacote_movimentos",
        *_tenant_columns(),
        sa.Column("credito_id", sa.Integer(), sa.ForeignKey("banho_tosa_pacote_creditos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("atendimento_id", sa.Integer(), sa.ForeignKey("banho_tosa_atendimentos.id"), nullable=True),
        sa.Column("movimento_origem_id", sa.Integer(), sa.ForeignKey("banho_tosa_pacote_movimentos.id"), nullable=True),
        sa.Column("tipo", sa.String(30), nullable=False),
        sa.Column("quantidade", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("saldo_apos", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_banho_tosa_pacote_movimentos_tenant_id", "banho_tosa_pacote_movimentos", ["tenant_id"])
    op.create_index("ix_bt_movimentos_credito_id", "banho_tosa_pacote_movimentos", ["credito_id"])
    op.create_index("ix_bt_movimentos_atendimento_id", "banho_tosa_pacote_movimentos", ["atendimento_id"])
    op.create_index("ix_bt_movimentos_origem_id", "banho_tosa_pacote_movimentos", ["movimento_origem_id"])
    op.create_index("ix_bt_movimentos_tipo", "banho_tosa_pacote_movimentos", ["tipo"])
    op.create_index("ix_bt_movimentos_credito", "banho_tosa_pacote_movimentos", ["tenant_id", "credito_id"])
    op.create_index("ix_bt_movimentos_atendimento", "banho_tosa_pacote_movimentos", ["tenant_id", "atendimento_id"])

    op.create_table(
        "banho_tosa_recorrencias",
        *_tenant_columns(),
        sa.Column("cliente_id", sa.Integer(), sa.ForeignKey("clientes.id"), nullable=False),
        sa.Column("pet_id", sa.Integer(), sa.ForeignKey("pets.id"), nullable=False),
        sa.Column("servico_id", sa.Integer(), sa.ForeignKey("banho_tosa_servicos.id"), nullable=True),
        sa.Column("pacote_credito_id", sa.Integer(), sa.ForeignKey("banho_tosa_pacote_creditos.id"), nullable=True),
        sa.Column("intervalo_dias", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("proxima_execucao", sa.Date(), nullable=False),
        sa.Column("canal_lembrete", sa.String(30), nullable=False, server_default="whatsapp"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_banho_tosa_recorrencias_tenant_id", "banho_tosa_recorrencias", ["tenant_id"])
    op.create_index("ix_bt_recorrencias_cliente_id", "banho_tosa_recorrencias", ["cliente_id"])
    op.create_index("ix_bt_recorrencias_pet_id", "banho_tosa_recorrencias", ["pet_id"])
    op.create_index("ix_bt_recorrencias_servico_id", "banho_tosa_recorrencias", ["servico_id"])
    op.create_index("ix_bt_recorrencias_credito_id", "banho_tosa_recorrencias", ["pacote_credito_id"])
    op.create_index("ix_bt_recorrencias_proxima_execucao", "banho_tosa_recorrencias", ["proxima_execucao"])
    op.create_index("ix_bt_recorrencias_proxima", "banho_tosa_recorrencias", ["tenant_id", "ativo", "proxima_execucao"])

    op.add_column("banho_tosa_atendimentos", sa.Column("pacote_credito_id", sa.Integer(), nullable=True))
    op.add_column("banho_tosa_atendimentos", sa.Column("pacote_movimento_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_bt_at_pacote_credito", "banho_tosa_atendimentos", "banho_tosa_pacote_creditos", ["pacote_credito_id"], ["id"])
    op.create_foreign_key("fk_bt_at_pacote_movimento", "banho_tosa_atendimentos", "banho_tosa_pacote_movimentos", ["pacote_movimento_id"], ["id"])
    op.create_index("ix_bt_at_pacote_credito_id", "banho_tosa_atendimentos", ["pacote_credito_id"])
    op.create_index("ix_bt_at_pacote_movimento_id", "banho_tosa_atendimentos", ["pacote_movimento_id"])


def downgrade() -> None:
    op.drop_index("ix_bt_at_pacote_movimento_id", table_name="banho_tosa_atendimentos")
    op.drop_index("ix_bt_at_pacote_credito_id", table_name="banho_tosa_atendimentos")
    op.drop_constraint("fk_bt_at_pacote_movimento", "banho_tosa_atendimentos", type_="foreignkey")
    op.drop_constraint("fk_bt_at_pacote_credito", "banho_tosa_atendimentos", type_="foreignkey")
    op.drop_column("banho_tosa_atendimentos", "pacote_movimento_id")
    op.drop_column("banho_tosa_atendimentos", "pacote_credito_id")
    op.drop_table("banho_tosa_recorrencias")
    op.drop_table("banho_tosa_pacote_movimentos")
    op.drop_table("banho_tosa_pacote_creditos")
    op.drop_table("banho_tosa_pacotes")
