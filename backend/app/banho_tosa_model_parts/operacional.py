"""Modelos operacionais do Banho & Tosa."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.base_models import BaseTenantModel


class BanhoTosaAtendimento(BaseTenantModel):
    __tablename__ = "banho_tosa_atendimentos"
    __table_args__ = (
        Index("ix_bt_atendimentos_tenant_status", "tenant_id", "status"),
        Index("ix_bt_atendimentos_tenant_pet", "tenant_id", "pet_id"),
    )

    agendamento_id = Column(Integer, ForeignKey("banho_tosa_agendamentos.id"), nullable=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    pet_id = Column(Integer, ForeignKey("pets.id"), nullable=False, index=True)
    status = Column(String(40), nullable=False, default="chegou", index=True)
    checkin_em = Column(DateTime(timezone=True), nullable=True)
    inicio_em = Column(DateTime(timezone=True), nullable=True)
    fim_em = Column(DateTime(timezone=True), nullable=True)
    entregue_em = Column(DateTime(timezone=True), nullable=True)
    peso_informado_kg = Column(Numeric(10, 3), nullable=True)
    porte_snapshot = Column(String(30), nullable=True)
    pelagem_snapshot = Column(String(40), nullable=True)
    observacoes_entrada = Column(Text, nullable=True)
    observacoes_saida = Column(Text, nullable=True)
    ocorrencias = Column(JSON, nullable=True)
    venda_id = Column(Integer, ForeignKey("vendas.id"), nullable=True, index=True)
    conta_receber_id = Column(Integer, ForeignKey("contas_receber.id"), nullable=True, index=True)
    pacote_credito_id = Column(Integer, ForeignKey("banho_tosa_pacote_creditos.id"), nullable=True, index=True)
    pacote_movimento_id = Column(Integer, ForeignKey("banho_tosa_pacote_movimentos.id"), nullable=True, index=True)
    custo_snapshot_id = Column(Integer, nullable=True, index=True)

    agendamento = relationship("BanhoTosaAgendamento", back_populates="atendimento")
    cliente = relationship("Cliente", foreign_keys=[cliente_id])
    pet = relationship("Pet", foreign_keys=[pet_id])
    venda = relationship("Venda", foreign_keys=[venda_id])
    pacote_credito = relationship("BanhoTosaPacoteCredito", foreign_keys=[pacote_credito_id])
    pacote_movimento = relationship("BanhoTosaPacoteMovimento", foreign_keys=[pacote_movimento_id])
    avaliacoes = relationship("BanhoTosaAvaliacao", back_populates="atendimento", cascade="all, delete-orphan")
    etapas = relationship("BanhoTosaEtapa", back_populates="atendimento", cascade="all, delete-orphan")
    insumos_usados = relationship("BanhoTosaInsumoUsado", back_populates="atendimento", cascade="all, delete-orphan")


class BanhoTosaEtapa(BaseTenantModel):
    __tablename__ = "banho_tosa_etapas"
    __table_args__ = (Index("ix_bt_etapas_atendimento_tipo", "tenant_id", "atendimento_id", "tipo"),)

    atendimento_id = Column(Integer, ForeignKey("banho_tosa_atendimentos.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo = Column(String(40), nullable=False, index=True)
    responsavel_id = Column(Integer, ForeignKey("clientes.id"), nullable=True, index=True)
    recurso_id = Column(Integer, ForeignKey("banho_tosa_recursos.id"), nullable=True, index=True)
    inicio_em = Column(DateTime(timezone=True), nullable=True)
    fim_em = Column(DateTime(timezone=True), nullable=True)
    duracao_minutos = Column(Integer, nullable=True)
    observacoes = Column(Text, nullable=True)

    atendimento = relationship("BanhoTosaAtendimento", back_populates="etapas")
    responsavel = relationship("Cliente", foreign_keys=[responsavel_id])
    recurso = relationship("BanhoTosaRecurso")


class BanhoTosaFoto(BaseTenantModel):
    __tablename__ = "banho_tosa_fotos"
    __table_args__ = (Index("ix_bt_fotos_atendimento", "tenant_id", "atendimento_id"),)

    atendimento_id = Column(Integer, ForeignKey("banho_tosa_atendimentos.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo = Column(String(30), nullable=False, default="entrada")
    url = Column(String(500), nullable=False)
    descricao = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)


class BanhoTosaInsumoPrevisto(BaseTenantModel):
    __tablename__ = "banho_tosa_insumos_previstos"
    __table_args__ = (
        UniqueConstraint("tenant_id", "servico_id", "porte_id", "produto_id", name="uq_bt_insumo_previsto"),
        Index("ix_bt_insumos_previstos_servico_porte", "tenant_id", "servico_id", "porte_id"),
    )

    servico_id = Column(Integer, ForeignKey("banho_tosa_servicos.id", ondelete="CASCADE"), nullable=False, index=True)
    porte_id = Column(Integer, ForeignKey("banho_tosa_parametros_porte.id"), nullable=False, index=True)
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False, index=True)
    quantidade_padrao = Column(Numeric(12, 4), nullable=False, default=0)
    unidade = Column(String(20), nullable=False, default="UN")
    baixar_estoque = Column(Boolean, nullable=False, default=True)

    servico = relationship("BanhoTosaServico")
    porte = relationship("BanhoTosaParametroPorte")
    produto = relationship("Produto")


class BanhoTosaInsumoUsado(BaseTenantModel):
    __tablename__ = "banho_tosa_insumos_usados"
    __table_args__ = (
        UniqueConstraint("tenant_id", "atendimento_id", "produto_id", name="uq_bt_insumo_usado_atendimento_produto"),
        Index("ix_bt_insumos_usados_atendimento", "tenant_id", "atendimento_id"),
    )

    atendimento_id = Column(Integer, ForeignKey("banho_tosa_atendimentos.id", ondelete="CASCADE"), nullable=False, index=True)
    produto_id = Column(Integer, ForeignKey("produtos.id"), nullable=False, index=True)
    quantidade_prevista = Column(Numeric(12, 4), nullable=False, default=0)
    quantidade_usada = Column(Numeric(12, 4), nullable=False, default=0)
    quantidade_desperdicio = Column(Numeric(12, 4), nullable=False, default=0)
    custo_unitario_snapshot = Column(Numeric(12, 4), nullable=False, default=0)
    movimentacao_estoque_id = Column(Integer, nullable=True, index=True)
    movimentacao_estorno_id = Column(Integer, nullable=True, index=True)
    estoque_estornado_em = Column(DateTime(timezone=True), nullable=True)
    responsavel_id = Column(Integer, ForeignKey("clientes.id"), nullable=True, index=True)

    atendimento = relationship("BanhoTosaAtendimento", back_populates="insumos_usados")
    produto = relationship("Produto")
    responsavel = relationship("Cliente", foreign_keys=[responsavel_id])
