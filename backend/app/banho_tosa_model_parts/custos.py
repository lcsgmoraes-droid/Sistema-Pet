"""Modelos de custos e taxi dog do Banho & Tosa."""

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.base_models import BaseTenantModel


class BanhoTosaCustoSnapshot(BaseTenantModel):
    __tablename__ = "banho_tosa_custos_snapshot"
    __table_args__ = (
        UniqueConstraint("tenant_id", "atendimento_id", name="uq_bt_custo_snapshot_atendimento"),
        Index("ix_bt_custos_tenant_atendimento", "tenant_id", "atendimento_id"),
    )

    atendimento_id = Column(Integer, ForeignKey("banho_tosa_atendimentos.id", ondelete="CASCADE"), nullable=False, index=True)
    valor_cobrado = Column(Numeric(12, 2), nullable=False, default=0)
    custo_insumos = Column(Numeric(12, 2), nullable=False, default=0)
    custo_agua = Column(Numeric(12, 2), nullable=False, default=0)
    custo_energia = Column(Numeric(12, 2), nullable=False, default=0)
    custo_mao_obra = Column(Numeric(12, 2), nullable=False, default=0)
    custo_comissao = Column(Numeric(12, 2), nullable=False, default=0)
    custo_taxi_dog = Column(Numeric(12, 2), nullable=False, default=0)
    custo_taxas_pagamento = Column(Numeric(12, 2), nullable=False, default=0)
    custo_rateio_operacional = Column(Numeric(12, 2), nullable=False, default=0)
    custo_total = Column(Numeric(12, 2), nullable=False, default=0)
    margem_valor = Column(Numeric(12, 2), nullable=False, default=0)
    margem_percentual = Column(Numeric(8, 4), nullable=False, default=0)
    detalhes_json = Column(JSON, nullable=True)

    atendimento = relationship("BanhoTosaAtendimento")


class BanhoTosaTaxiDog(BaseTenantModel):
    __tablename__ = "banho_tosa_taxi_dog"
    __table_args__ = (
        Index("ix_bt_taxi_tenant_status", "tenant_id", "status"),
        Index("ix_bt_taxi_tenant_janela", "tenant_id", "janela_inicio", "janela_fim"),
    )

    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    pet_id = Column(Integer, ForeignKey("pets.id"), nullable=False, index=True)
    agendamento_id = Column(Integer, ForeignKey("banho_tosa_agendamentos.id"), nullable=True, index=True)
    tipo = Column(String(20), nullable=False, default="ida_volta")
    status = Column(String(40), nullable=False, default="agendado", index=True)
    motorista_id = Column(Integer, ForeignKey("clientes.id"), nullable=True, index=True)
    endereco_origem = Column(Text, nullable=True)
    endereco_destino = Column(Text, nullable=True)
    janela_inicio = Column(DateTime(timezone=True), nullable=True)
    janela_fim = Column(DateTime(timezone=True), nullable=True)
    km_estimado = Column(Numeric(12, 3), nullable=False, default=0)
    km_real = Column(Numeric(12, 3), nullable=False, default=0)
    valor_cobrado = Column(Numeric(12, 2), nullable=False, default=0)
    custo_estimado = Column(Numeric(12, 2), nullable=False, default=0)
    custo_real = Column(Numeric(12, 2), nullable=False, default=0)
    rota_entrega_id = Column(Integer, nullable=True, index=True)

    cliente = relationship("Cliente", foreign_keys=[cliente_id])
    pet = relationship("Pet", foreign_keys=[pet_id])
    motorista = relationship("Cliente", foreign_keys=[motorista_id])
    agendamento = relationship("BanhoTosaAgendamento", foreign_keys=[agendamento_id])
