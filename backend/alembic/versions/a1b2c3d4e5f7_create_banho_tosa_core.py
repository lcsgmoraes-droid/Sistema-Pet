"""create banho tosa core

Revision ID: a1b2c3d4e5f7
Revises: i0j1k2l3m4n5
Create Date: 2026-04-26 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID


revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, Sequence[str], None] = "i0j1k2l3m4n5"
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
        "banho_tosa_configuracoes",
        *_tenant_columns(),
        sa.Column("horario_inicio", sa.String(5), nullable=False, server_default="08:00"),
        sa.Column("horario_fim", sa.String(5), nullable=False, server_default="18:00"),
        sa.Column("dias_funcionamento", sa.JSON(), nullable=True),
        sa.Column("intervalo_slot_minutos", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("politica_atraso", sa.Text(), nullable=True),
        sa.Column("tolerancia_encaixe_minutos", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("custo_litro_agua", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("vazao_chuveiro_litros_min", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("custo_kwh", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("custo_toalha_padrao", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("custo_higienizacao_padrao", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("percentual_taxas_padrao", sa.Numeric(7, 4), nullable=False, server_default="0"),
        sa.Column("custo_rateio_operacional_padrao", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("horas_produtivas_mes_padrao", sa.Numeric(8, 2), nullable=False, server_default="176"),
        sa.Column("dre_subcategoria_receita_id", sa.Integer(), nullable=True),
        sa.Column("dre_subcategoria_custo_id", sa.Integer(), nullable=True),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_banho_tosa_configuracoes_tenant_id", "banho_tosa_configuracoes", ["tenant_id"])
    op.create_index("ix_bt_config_tenant_ativo", "banho_tosa_configuracoes", ["tenant_id", "ativo"])
    op.create_index("ix_bt_config_receita_id", "banho_tosa_configuracoes", ["dre_subcategoria_receita_id"])
    op.create_index("ix_bt_config_custo_id", "banho_tosa_configuracoes", ["dre_subcategoria_custo_id"])

    op.create_table(
        "banho_tosa_recursos",
        *_tenant_columns(),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("tipo", sa.String(30), nullable=False),
        sa.Column("capacidade_simultanea", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("potencia_watts", sa.Numeric(12, 2), nullable=True),
        sa.Column("custo_manutencao_hora", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_banho_tosa_recursos_tenant_id", "banho_tosa_recursos", ["tenant_id"])
    op.create_index("ix_bt_recursos_nome", "banho_tosa_recursos", ["nome"])
    op.create_index("ix_bt_recursos_tenant_tipo_ativo", "banho_tosa_recursos", ["tenant_id", "tipo", "ativo"])

    op.create_table(
        "banho_tosa_servicos",
        *_tenant_columns(),
        sa.Column("nome", sa.String(160), nullable=False),
        sa.Column("categoria", sa.String(30), nullable=False, server_default="banho"),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("duracao_padrao_minutos", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("requer_banho", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("requer_tosa", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("requer_secagem", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("permite_pacote", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "nome", name="uq_bt_servicos_tenant_nome"),
    )
    op.create_index("ix_banho_tosa_servicos_tenant_id", "banho_tosa_servicos", ["tenant_id"])
    op.create_index("ix_bt_servicos_nome", "banho_tosa_servicos", ["nome"])
    op.create_index("ix_bt_servicos_categoria", "banho_tosa_servicos", ["categoria"])
    op.create_index("ix_bt_servicos_tenant_categoria", "banho_tosa_servicos", ["tenant_id", "categoria", "ativo"])

    op.create_table(
        "banho_tosa_parametros_porte",
        *_tenant_columns(),
        sa.Column("porte", sa.String(30), nullable=False),
        sa.Column("peso_min_kg", sa.Numeric(10, 3), nullable=True),
        sa.Column("peso_max_kg", sa.Numeric(10, 3), nullable=True),
        sa.Column("agua_padrao_litros", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("energia_padrao_kwh", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("tempo_banho_min", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tempo_secagem_min", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tempo_tosa_min", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("multiplicador_preco", sa.Numeric(8, 4), nullable=False, server_default="1"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "porte", name="uq_bt_parametros_porte_tenant_porte"),
    )
    op.create_index("ix_banho_tosa_parametros_porte_tenant_id", "banho_tosa_parametros_porte", ["tenant_id"])
    op.create_index("ix_bt_parametros_porte", "banho_tosa_parametros_porte", ["porte"])
    op.create_index("ix_bt_parametros_porte_tenant_ativo", "banho_tosa_parametros_porte", ["tenant_id", "ativo"])

    op.create_table(
        "banho_tosa_precos_servico",
        *_tenant_columns(),
        sa.Column("servico_id", sa.Integer(), sa.ForeignKey("banho_tosa_servicos.id"), nullable=False),
        sa.Column("porte_id", sa.Integer(), sa.ForeignKey("banho_tosa_parametros_porte.id"), nullable=False),
        sa.Column("tipo_pelagem", sa.String(40), nullable=False, server_default="padrao"),
        sa.Column("preco_base", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("tempo_estimado_minutos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("agua_estimada_litros", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("energia_estimada_kwh", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "servico_id", "porte_id", "tipo_pelagem", name="uq_bt_preco_servico_porte_pelagem"),
    )
    op.create_index("ix_banho_tosa_precos_servico_tenant_id", "banho_tosa_precos_servico", ["tenant_id"])
    op.create_index("ix_bt_precos_servico_id", "banho_tosa_precos_servico", ["servico_id"])
    op.create_index("ix_bt_precos_porte_id", "banho_tosa_precos_servico", ["porte_id"])
    op.create_index("ix_bt_precos_tenant_servico", "banho_tosa_precos_servico", ["tenant_id", "servico_id"])

    op.create_table(
        "banho_tosa_agendamentos",
        *_tenant_columns(),
        sa.Column("cliente_id", sa.Integer(), sa.ForeignKey("clientes.id"), nullable=False),
        sa.Column("pet_id", sa.Integer(), sa.ForeignKey("pets.id"), nullable=False),
        sa.Column("responsavel_agendamento_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("profissional_principal_id", sa.Integer(), sa.ForeignKey("clientes.id"), nullable=True),
        sa.Column("banhista_id", sa.Integer(), sa.ForeignKey("clientes.id"), nullable=True),
        sa.Column("tosador_id", sa.Integer(), sa.ForeignKey("clientes.id"), nullable=True),
        sa.Column("recurso_id", sa.Integer(), sa.ForeignKey("banho_tosa_recursos.id"), nullable=True),
        sa.Column("data_hora_inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_hora_fim_prevista", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(40), nullable=False, server_default="agendado"),
        sa.Column("origem", sa.String(30), nullable=False, server_default="balcao"),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("restricoes_veterinarias_snapshot", sa.JSON(), nullable=True),
        sa.Column("perfil_comportamental_snapshot", sa.JSON(), nullable=True),
        sa.Column("valor_previsto", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("sinal_pago", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("taxi_dog_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_banho_tosa_agendamentos_tenant_id", "banho_tosa_agendamentos", ["tenant_id"])
    op.create_index("ix_bt_ag_cliente_id", "banho_tosa_agendamentos", ["cliente_id"])
    op.create_index("ix_bt_ag_pet_id", "banho_tosa_agendamentos", ["pet_id"])
    op.create_index("ix_bt_ag_responsavel_id", "banho_tosa_agendamentos", ["responsavel_agendamento_user_id"])
    op.create_index("ix_bt_ag_profissional_id", "banho_tosa_agendamentos", ["profissional_principal_id"])
    op.create_index("ix_bt_ag_banhista_id", "banho_tosa_agendamentos", ["banhista_id"])
    op.create_index("ix_bt_ag_tosador_id", "banho_tosa_agendamentos", ["tosador_id"])
    op.create_index("ix_bt_ag_recurso_id", "banho_tosa_agendamentos", ["recurso_id"])
    op.create_index("ix_bt_ag_taxi_dog_id", "banho_tosa_agendamentos", ["taxi_dog_id"])
    op.create_index("ix_bt_ag_data_inicio", "banho_tosa_agendamentos", ["data_hora_inicio"])
    op.create_index("ix_bt_ag_status", "banho_tosa_agendamentos", ["status"])
    op.create_index("ix_bt_agendamentos_tenant_inicio", "banho_tosa_agendamentos", ["tenant_id", "data_hora_inicio"])
    op.create_index("ix_bt_agendamentos_tenant_status", "banho_tosa_agendamentos", ["tenant_id", "status"])
    op.create_index(
        "ix_bt_agendamentos_profissional_inicio",
        "banho_tosa_agendamentos",
        ["tenant_id", "profissional_principal_id", "data_hora_inicio"],
    )

    op.create_table(
        "banho_tosa_agendamento_servicos",
        *_tenant_columns(),
        sa.Column("agendamento_id", sa.Integer(), sa.ForeignKey("banho_tosa_agendamentos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("servico_id", sa.Integer(), sa.ForeignKey("banho_tosa_servicos.id"), nullable=True),
        sa.Column("nome_servico_snapshot", sa.String(160), nullable=False),
        sa.Column("quantidade", sa.Numeric(12, 3), nullable=False, server_default="1"),
        sa.Column("valor_unitario", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("desconto", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("tempo_previsto_minutos", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_banho_tosa_agendamento_servicos_tenant_id", "banho_tosa_agendamento_servicos", ["tenant_id"])
    op.create_index("ix_bt_ag_servicos_agendamento_id", "banho_tosa_agendamento_servicos", ["agendamento_id"])
    op.create_index("ix_bt_ag_servicos_servico_id", "banho_tosa_agendamento_servicos", ["servico_id"])
    op.create_index("ix_bt_ag_servicos_agendamento", "banho_tosa_agendamento_servicos", ["tenant_id", "agendamento_id"])

    op.create_table(
        "banho_tosa_atendimentos",
        *_tenant_columns(),
        sa.Column("agendamento_id", sa.Integer(), sa.ForeignKey("banho_tosa_agendamentos.id"), nullable=True),
        sa.Column("cliente_id", sa.Integer(), sa.ForeignKey("clientes.id"), nullable=False),
        sa.Column("pet_id", sa.Integer(), sa.ForeignKey("pets.id"), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="chegou"),
        sa.Column("checkin_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("inicio_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fim_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("entregue_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("peso_informado_kg", sa.Numeric(10, 3), nullable=True),
        sa.Column("porte_snapshot", sa.String(30), nullable=True),
        sa.Column("pelagem_snapshot", sa.String(40), nullable=True),
        sa.Column("observacoes_entrada", sa.Text(), nullable=True),
        sa.Column("observacoes_saida", sa.Text(), nullable=True),
        sa.Column("ocorrencias", sa.JSON(), nullable=True),
        sa.Column("venda_id", sa.Integer(), sa.ForeignKey("vendas.id"), nullable=True),
        sa.Column("conta_receber_id", sa.Integer(), sa.ForeignKey("contas_receber.id"), nullable=True),
        sa.Column("custo_snapshot_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_banho_tosa_atendimentos_tenant_id", "banho_tosa_atendimentos", ["tenant_id"])
    op.create_index("ix_bt_at_agendamento_id", "banho_tosa_atendimentos", ["agendamento_id"])
    op.create_index("ix_bt_at_cliente_id", "banho_tosa_atendimentos", ["cliente_id"])
    op.create_index("ix_bt_at_pet_id", "banho_tosa_atendimentos", ["pet_id"])
    op.create_index("ix_bt_at_status", "banho_tosa_atendimentos", ["status"])
    op.create_index("ix_bt_at_venda_id", "banho_tosa_atendimentos", ["venda_id"])
    op.create_index("ix_bt_at_conta_receber_id", "banho_tosa_atendimentos", ["conta_receber_id"])
    op.create_index("ix_bt_at_custo_snapshot_id", "banho_tosa_atendimentos", ["custo_snapshot_id"])
    op.create_index("ix_bt_atendimentos_tenant_status", "banho_tosa_atendimentos", ["tenant_id", "status"])
    op.create_index("ix_bt_atendimentos_tenant_pet", "banho_tosa_atendimentos", ["tenant_id", "pet_id"])

    op.create_table(
        "banho_tosa_etapas",
        *_tenant_columns(),
        sa.Column("atendimento_id", sa.Integer(), sa.ForeignKey("banho_tosa_atendimentos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tipo", sa.String(40), nullable=False),
        sa.Column("responsavel_id", sa.Integer(), sa.ForeignKey("clientes.id"), nullable=True),
        sa.Column("recurso_id", sa.Integer(), sa.ForeignKey("banho_tosa_recursos.id"), nullable=True),
        sa.Column("inicio_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fim_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duracao_minutos", sa.Integer(), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_banho_tosa_etapas_tenant_id", "banho_tosa_etapas", ["tenant_id"])
    op.create_index("ix_bt_etapas_atendimento_id", "banho_tosa_etapas", ["atendimento_id"])
    op.create_index("ix_bt_etapas_tipo", "banho_tosa_etapas", ["tipo"])
    op.create_index("ix_bt_etapas_responsavel_id", "banho_tosa_etapas", ["responsavel_id"])
    op.create_index("ix_bt_etapas_recurso_id", "banho_tosa_etapas", ["recurso_id"])
    op.create_index("ix_bt_etapas_atendimento_tipo", "banho_tosa_etapas", ["tenant_id", "atendimento_id", "tipo"])

    op.create_table(
        "banho_tosa_fotos",
        *_tenant_columns(),
        sa.Column("atendimento_id", sa.Integer(), sa.ForeignKey("banho_tosa_atendimentos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tipo", sa.String(30), nullable=False, server_default="entrada"),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_banho_tosa_fotos_tenant_id", "banho_tosa_fotos", ["tenant_id"])
    op.create_index("ix_bt_fotos_atendimento_id", "banho_tosa_fotos", ["atendimento_id"])
    op.create_index("ix_bt_fotos_atendimento", "banho_tosa_fotos", ["tenant_id", "atendimento_id"])

    op.create_table(
        "banho_tosa_insumos_previstos",
        *_tenant_columns(),
        sa.Column("servico_id", sa.Integer(), sa.ForeignKey("banho_tosa_servicos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("porte_id", sa.Integer(), sa.ForeignKey("banho_tosa_parametros_porte.id"), nullable=False),
        sa.Column("produto_id", sa.Integer(), sa.ForeignKey("produtos.id"), nullable=False),
        sa.Column("quantidade_padrao", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("unidade", sa.String(20), nullable=False, server_default="UN"),
        sa.Column("baixar_estoque", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "servico_id", "porte_id", "produto_id", name="uq_bt_insumo_previsto"),
    )
    op.create_index("ix_banho_tosa_insumos_previstos_tenant_id", "banho_tosa_insumos_previstos", ["tenant_id"])
    op.create_index("ix_bt_insumos_previstos_servico_id", "banho_tosa_insumos_previstos", ["servico_id"])
    op.create_index("ix_bt_insumos_previstos_porte_id", "banho_tosa_insumos_previstos", ["porte_id"])
    op.create_index("ix_bt_insumos_previstos_produto_id", "banho_tosa_insumos_previstos", ["produto_id"])
    op.create_index("ix_bt_insumos_previstos_servico_porte", "banho_tosa_insumos_previstos", ["tenant_id", "servico_id", "porte_id"])

    op.create_table(
        "banho_tosa_insumos_usados",
        *_tenant_columns(),
        sa.Column("atendimento_id", sa.Integer(), sa.ForeignKey("banho_tosa_atendimentos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("produto_id", sa.Integer(), sa.ForeignKey("produtos.id"), nullable=False),
        sa.Column("quantidade_prevista", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("quantidade_usada", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("quantidade_desperdicio", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("custo_unitario_snapshot", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("movimentacao_estoque_id", sa.Integer(), nullable=True),
        sa.Column("movimentacao_estorno_id", sa.Integer(), nullable=True),
        sa.Column("estoque_estornado_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responsavel_id", sa.Integer(), sa.ForeignKey("clientes.id"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "atendimento_id", "produto_id", name="uq_bt_insumo_usado_atendimento_produto"),
    )
    op.create_index("ix_banho_tosa_insumos_usados_tenant_id", "banho_tosa_insumos_usados", ["tenant_id"])
    op.create_index("ix_bt_insumos_usados_atendimento_id", "banho_tosa_insumos_usados", ["atendimento_id"])
    op.create_index("ix_bt_insumos_usados_produto_id", "banho_tosa_insumos_usados", ["produto_id"])
    op.create_index("ix_bt_insumos_usados_movimentacao_id", "banho_tosa_insumos_usados", ["movimentacao_estoque_id"])
    op.create_index("ix_bt_insumos_usados_estorno_id", "banho_tosa_insumos_usados", ["movimentacao_estorno_id"])
    op.create_index("ix_bt_insumos_usados_responsavel_id", "banho_tosa_insumos_usados", ["responsavel_id"])
    op.create_index("ix_bt_insumos_usados_atendimento", "banho_tosa_insumos_usados", ["tenant_id", "atendimento_id"])

    op.create_table(
        "banho_tosa_custos_snapshot",
        *_tenant_columns(),
        sa.Column("atendimento_id", sa.Integer(), sa.ForeignKey("banho_tosa_atendimentos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("valor_cobrado", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("custo_insumos", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("custo_agua", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("custo_energia", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("custo_mao_obra", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("custo_comissao", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("custo_taxi_dog", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("custo_taxas_pagamento", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("custo_rateio_operacional", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("custo_total", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("margem_valor", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("margem_percentual", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column("detalhes_json", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "atendimento_id", name="uq_bt_custo_snapshot_atendimento"),
    )
    op.create_index("ix_banho_tosa_custos_snapshot_tenant_id", "banho_tosa_custos_snapshot", ["tenant_id"])
    op.create_index("ix_bt_custos_atendimento_id", "banho_tosa_custos_snapshot", ["atendimento_id"])
    op.create_index("ix_bt_custos_tenant_atendimento", "banho_tosa_custos_snapshot", ["tenant_id", "atendimento_id"])

    op.create_table(
        "banho_tosa_taxi_dog",
        *_tenant_columns(),
        sa.Column("cliente_id", sa.Integer(), sa.ForeignKey("clientes.id"), nullable=False),
        sa.Column("pet_id", sa.Integer(), sa.ForeignKey("pets.id"), nullable=False),
        sa.Column("agendamento_id", sa.Integer(), sa.ForeignKey("banho_tosa_agendamentos.id"), nullable=True),
        sa.Column("tipo", sa.String(20), nullable=False, server_default="ida_volta"),
        sa.Column("status", sa.String(40), nullable=False, server_default="agendado"),
        sa.Column("motorista_id", sa.Integer(), sa.ForeignKey("clientes.id"), nullable=True),
        sa.Column("endereco_origem", sa.Text(), nullable=True),
        sa.Column("endereco_destino", sa.Text(), nullable=True),
        sa.Column("janela_inicio", sa.DateTime(timezone=True), nullable=True),
        sa.Column("janela_fim", sa.DateTime(timezone=True), nullable=True),
        sa.Column("km_estimado", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("km_real", sa.Numeric(12, 3), nullable=False, server_default="0"),
        sa.Column("valor_cobrado", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("custo_estimado", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("custo_real", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("rota_entrega_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_banho_tosa_taxi_dog_tenant_id", "banho_tosa_taxi_dog", ["tenant_id"])
    op.create_index("ix_bt_taxi_cliente_id", "banho_tosa_taxi_dog", ["cliente_id"])
    op.create_index("ix_bt_taxi_pet_id", "banho_tosa_taxi_dog", ["pet_id"])
    op.create_index("ix_bt_taxi_agendamento_id", "banho_tosa_taxi_dog", ["agendamento_id"])
    op.create_index("ix_bt_taxi_status", "banho_tosa_taxi_dog", ["status"])
    op.create_index("ix_bt_taxi_motorista_id", "banho_tosa_taxi_dog", ["motorista_id"])
    op.create_index("ix_bt_taxi_rota_entrega_id", "banho_tosa_taxi_dog", ["rota_entrega_id"])
    op.create_index("ix_bt_taxi_tenant_status", "banho_tosa_taxi_dog", ["tenant_id", "status"])
    op.create_index("ix_bt_taxi_tenant_janela", "banho_tosa_taxi_dog", ["tenant_id", "janela_inicio", "janela_fim"])


def downgrade() -> None:
    op.drop_table("banho_tosa_taxi_dog")
    op.drop_table("banho_tosa_custos_snapshot")
    op.drop_table("banho_tosa_insumos_usados")
    op.drop_table("banho_tosa_insumos_previstos")
    op.drop_table("banho_tosa_fotos")
    op.drop_table("banho_tosa_etapas")
    op.drop_table("banho_tosa_atendimentos")
    op.drop_table("banho_tosa_agendamento_servicos")
    op.drop_table("banho_tosa_agendamentos")
    op.drop_table("banho_tosa_precos_servico")
    op.drop_table("banho_tosa_parametros_porte")
    op.drop_table("banho_tosa_servicos")
    op.drop_table("banho_tosa_recursos")
    op.drop_table("banho_tosa_configuracoes")
