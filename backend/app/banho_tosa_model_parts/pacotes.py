"""Modelos de pacotes, creditos e recorrencias do Banho & Tosa."""

from sqlalchemy import Boolean, Column, Date, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.base_models import BaseTenantModel


class BanhoTosaPacote(BaseTenantModel):
    __tablename__ = "banho_tosa_pacotes"
    __table_args__ = (
        UniqueConstraint("tenant_id", "nome", name="uq_bt_pacotes_tenant_nome"),
        Index("ix_bt_pacotes_tenant_ativo", "tenant_id", "ativo"),
    )

    nome = Column(String(160), nullable=False, index=True)
    descricao = Column(Text, nullable=True)
    servico_id = Column(Integer, ForeignKey("banho_tosa_servicos.id"), nullable=True, index=True)
    quantidade_creditos = Column(Numeric(12, 3), nullable=False, default=1)
    validade_dias = Column(Integer, nullable=False, default=30)
    preco = Column(Numeric(12, 2), nullable=False, default=0)
    ativo = Column(Boolean, nullable=False, default=True)

    servico = relationship("BanhoTosaServico")
    creditos = relationship("BanhoTosaPacoteCredito", back_populates="pacote")


class BanhoTosaPacoteCredito(BaseTenantModel):
    __tablename__ = "banho_tosa_pacote_creditos"
    __table_args__ = (
        Index("ix_bt_creditos_cliente_pet", "tenant_id", "cliente_id", "pet_id"),
        Index("ix_bt_creditos_status_validade", "tenant_id", "status", "data_validade"),
    )

    pacote_id = Column(Integer, ForeignKey("banho_tosa_pacotes.id"), nullable=False, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    pet_id = Column(Integer, ForeignKey("pets.id"), nullable=True, index=True)
    venda_id = Column(Integer, ForeignKey("vendas.id"), nullable=True, index=True)
    status = Column(String(30), nullable=False, default="ativo", index=True)
    creditos_total = Column(Numeric(12, 3), nullable=False, default=0)
    creditos_usados = Column(Numeric(12, 3), nullable=False, default=0)
    creditos_cancelados = Column(Numeric(12, 3), nullable=False, default=0)
    data_inicio = Column(Date, nullable=False)
    data_validade = Column(Date, nullable=False, index=True)
    observacoes = Column(Text, nullable=True)

    pacote = relationship("BanhoTosaPacote", back_populates="creditos")
    cliente = relationship("Cliente", foreign_keys=[cliente_id])
    pet = relationship("Pet", foreign_keys=[pet_id])
    movimentos = relationship("BanhoTosaPacoteMovimento", back_populates="credito", cascade="all, delete-orphan")


class BanhoTosaPacoteMovimento(BaseTenantModel):
    __tablename__ = "banho_tosa_pacote_movimentos"
    __table_args__ = (
        Index("ix_bt_movimentos_credito", "tenant_id", "credito_id"),
        Index("ix_bt_movimentos_atendimento", "tenant_id", "atendimento_id"),
    )

    credito_id = Column(Integer, ForeignKey("banho_tosa_pacote_creditos.id", ondelete="CASCADE"), nullable=False, index=True)
    atendimento_id = Column(Integer, ForeignKey("banho_tosa_atendimentos.id"), nullable=True, index=True)
    movimento_origem_id = Column(Integer, ForeignKey("banho_tosa_pacote_movimentos.id"), nullable=True, index=True)
    tipo = Column(String(30), nullable=False, index=True)
    quantidade = Column(Numeric(12, 3), nullable=False, default=0)
    saldo_apos = Column(Numeric(12, 3), nullable=False, default=0)
    observacoes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    credito = relationship("BanhoTosaPacoteCredito", back_populates="movimentos")


class BanhoTosaRecorrencia(BaseTenantModel):
    __tablename__ = "banho_tosa_recorrencias"
    __table_args__ = (Index("ix_bt_recorrencias_proxima", "tenant_id", "ativo", "proxima_execucao"),)

    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    pet_id = Column(Integer, ForeignKey("pets.id"), nullable=False, index=True)
    servico_id = Column(Integer, ForeignKey("banho_tosa_servicos.id"), nullable=True, index=True)
    pacote_credito_id = Column(Integer, ForeignKey("banho_tosa_pacote_creditos.id"), nullable=True, index=True)
    intervalo_dias = Column(Integer, nullable=False, default=30)
    proxima_execucao = Column(Date, nullable=False, index=True)
    canal_lembrete = Column(String(30), nullable=False, default="whatsapp")
    ativo = Column(Boolean, nullable=False, default=True)
    observacoes = Column(Text, nullable=True)

    cliente = relationship("Cliente", foreign_keys=[cliente_id])
    pet = relationship("Pet", foreign_keys=[pet_id])
    servico = relationship("BanhoTosaServico")
    pacote_credito = relationship("BanhoTosaPacoteCredito")
