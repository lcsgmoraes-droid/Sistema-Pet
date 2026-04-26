"""Modelos de agenda do Banho & Tosa."""

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.base_models import BaseTenantModel


class BanhoTosaAgendamento(BaseTenantModel):
    __tablename__ = "banho_tosa_agendamentos"
    __table_args__ = (
        Index("ix_bt_agendamentos_tenant_inicio", "tenant_id", "data_hora_inicio"),
        Index("ix_bt_agendamentos_tenant_status", "tenant_id", "status"),
        Index("ix_bt_agendamentos_profissional_inicio", "tenant_id", "profissional_principal_id", "data_hora_inicio"),
    )

    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    pet_id = Column(Integer, ForeignKey("pets.id"), nullable=False, index=True)
    responsavel_agendamento_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    profissional_principal_id = Column(Integer, ForeignKey("clientes.id"), nullable=True, index=True)
    banhista_id = Column(Integer, ForeignKey("clientes.id"), nullable=True, index=True)
    tosador_id = Column(Integer, ForeignKey("clientes.id"), nullable=True, index=True)
    recurso_id = Column(Integer, ForeignKey("banho_tosa_recursos.id"), nullable=True, index=True)
    data_hora_inicio = Column(DateTime(timezone=True), nullable=False, index=True)
    data_hora_fim_prevista = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(40), nullable=False, default="agendado", index=True)
    origem = Column(String(30), nullable=False, default="balcao")
    observacoes = Column(Text, nullable=True)
    restricoes_veterinarias_snapshot = Column(JSON, nullable=True)
    perfil_comportamental_snapshot = Column(JSON, nullable=True)
    valor_previsto = Column(Numeric(12, 2), nullable=False, default=0)
    sinal_pago = Column(Numeric(12, 2), nullable=False, default=0)
    taxi_dog_id = Column(Integer, nullable=True, index=True)

    cliente = relationship("Cliente", foreign_keys=[cliente_id])
    pet = relationship("Pet", foreign_keys=[pet_id])
    profissional_principal = relationship("Cliente", foreign_keys=[profissional_principal_id])
    banhista = relationship("Cliente", foreign_keys=[banhista_id])
    tosador = relationship("Cliente", foreign_keys=[tosador_id])
    recurso = relationship("BanhoTosaRecurso", foreign_keys=[recurso_id])
    servicos = relationship("BanhoTosaAgendamentoServico", back_populates="agendamento", cascade="all, delete-orphan")
    atendimento = relationship("BanhoTosaAtendimento", back_populates="agendamento", uselist=False)


class BanhoTosaAgendamentoServico(BaseTenantModel):
    __tablename__ = "banho_tosa_agendamento_servicos"
    __table_args__ = (Index("ix_bt_ag_servicos_agendamento", "tenant_id", "agendamento_id"),)

    agendamento_id = Column(Integer, ForeignKey("banho_tosa_agendamentos.id", ondelete="CASCADE"), nullable=False, index=True)
    servico_id = Column(Integer, ForeignKey("banho_tosa_servicos.id"), nullable=True, index=True)
    nome_servico_snapshot = Column(String(160), nullable=False)
    quantidade = Column(Numeric(12, 3), nullable=False, default=1)
    valor_unitario = Column(Numeric(12, 2), nullable=False, default=0)
    desconto = Column(Numeric(12, 2), nullable=False, default=0)
    tempo_previsto_minutos = Column(Integer, nullable=False, default=0)

    agendamento = relationship("BanhoTosaAgendamento", back_populates="servicos")
    servico = relationship("BanhoTosaServico")
