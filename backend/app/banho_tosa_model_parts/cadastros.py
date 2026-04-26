"""Modelos de cadastros e parametrizacoes do Banho & Tosa."""

from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.base_models import BaseTenantModel


class BanhoTosaConfiguracao(BaseTenantModel):
    __tablename__ = "banho_tosa_configuracoes"
    __table_args__ = (Index("ix_bt_config_tenant_ativo", "tenant_id", "ativo"),)

    horario_inicio = Column(String(5), nullable=False, default="08:00")
    horario_fim = Column(String(5), nullable=False, default="18:00")
    dias_funcionamento = Column(JSON, nullable=True)
    intervalo_slot_minutos = Column(Integer, nullable=False, default=30)
    politica_atraso = Column(Text, nullable=True)
    tolerancia_encaixe_minutos = Column(Integer, nullable=False, default=15)
    custo_litro_agua = Column(Numeric(12, 4), nullable=False, default=0)
    vazao_chuveiro_litros_min = Column(Numeric(12, 4), nullable=False, default=0)
    custo_kwh = Column(Numeric(12, 4), nullable=False, default=0)
    custo_toalha_padrao = Column(Numeric(12, 2), nullable=False, default=0)
    custo_higienizacao_padrao = Column(Numeric(12, 2), nullable=False, default=0)
    percentual_taxas_padrao = Column(Numeric(7, 4), nullable=False, default=0)
    custo_rateio_operacional_padrao = Column(Numeric(12, 2), nullable=False, default=0)
    horas_produtivas_mes_padrao = Column(Numeric(8, 2), nullable=False, default=176)
    dre_subcategoria_receita_id = Column(Integer, nullable=True, index=True)
    dre_subcategoria_custo_id = Column(Integer, nullable=True, index=True)
    ativo = Column(Boolean, nullable=False, default=True)


class BanhoTosaRecurso(BaseTenantModel):
    __tablename__ = "banho_tosa_recursos"
    __table_args__ = (Index("ix_bt_recursos_tenant_tipo_ativo", "tenant_id", "tipo", "ativo"),)

    nome = Column(String(120), nullable=False, index=True)
    tipo = Column(String(30), nullable=False, index=True)
    capacidade_simultanea = Column(Integer, nullable=False, default=1)
    potencia_watts = Column(Numeric(12, 2), nullable=True)
    custo_manutencao_hora = Column(Numeric(12, 2), nullable=False, default=0)
    ativo = Column(Boolean, nullable=False, default=True)


class BanhoTosaServico(BaseTenantModel):
    __tablename__ = "banho_tosa_servicos"
    __table_args__ = (
        UniqueConstraint("tenant_id", "nome", name="uq_bt_servicos_tenant_nome"),
        Index("ix_bt_servicos_tenant_categoria", "tenant_id", "categoria", "ativo"),
    )

    nome = Column(String(160), nullable=False, index=True)
    categoria = Column(String(30), nullable=False, default="banho", index=True)
    descricao = Column(Text, nullable=True)
    duracao_padrao_minutos = Column(Integer, nullable=False, default=60)
    requer_banho = Column(Boolean, nullable=False, default=True)
    requer_tosa = Column(Boolean, nullable=False, default=False)
    requer_secagem = Column(Boolean, nullable=False, default=True)
    permite_pacote = Column(Boolean, nullable=False, default=True)
    ativo = Column(Boolean, nullable=False, default=True)

    precos = relationship("BanhoTosaPrecoServico", back_populates="servico", cascade="all, delete-orphan")


class BanhoTosaParametroPorte(BaseTenantModel):
    __tablename__ = "banho_tosa_parametros_porte"
    __table_args__ = (
        UniqueConstraint("tenant_id", "porte", name="uq_bt_parametros_porte_tenant_porte"),
        Index("ix_bt_parametros_porte_tenant_ativo", "tenant_id", "ativo"),
    )

    porte = Column(String(30), nullable=False, index=True)
    peso_min_kg = Column(Numeric(10, 3), nullable=True)
    peso_max_kg = Column(Numeric(10, 3), nullable=True)
    agua_padrao_litros = Column(Numeric(12, 3), nullable=False, default=0)
    energia_padrao_kwh = Column(Numeric(12, 4), nullable=False, default=0)
    tempo_banho_min = Column(Integer, nullable=False, default=0)
    tempo_secagem_min = Column(Integer, nullable=False, default=0)
    tempo_tosa_min = Column(Integer, nullable=False, default=0)
    multiplicador_preco = Column(Numeric(8, 4), nullable=False, default=1)
    ativo = Column(Boolean, nullable=False, default=True)

    precos = relationship("BanhoTosaPrecoServico", back_populates="porte")


class BanhoTosaPrecoServico(BaseTenantModel):
    __tablename__ = "banho_tosa_precos_servico"
    __table_args__ = (
        UniqueConstraint("tenant_id", "servico_id", "porte_id", "tipo_pelagem", name="uq_bt_preco_servico_porte_pelagem"),
        Index("ix_bt_precos_tenant_servico", "tenant_id", "servico_id"),
    )

    servico_id = Column(Integer, ForeignKey("banho_tosa_servicos.id"), nullable=False, index=True)
    porte_id = Column(Integer, ForeignKey("banho_tosa_parametros_porte.id"), nullable=False, index=True)
    tipo_pelagem = Column(String(40), nullable=False, default="padrao")
    preco_base = Column(Numeric(12, 2), nullable=False, default=0)
    tempo_estimado_minutos = Column(Integer, nullable=False, default=0)
    agua_estimada_litros = Column(Numeric(12, 3), nullable=False, default=0)
    energia_estimada_kwh = Column(Numeric(12, 4), nullable=False, default=0)

    servico = relationship("BanhoTosaServico", back_populates="precos")
    porte = relationship("BanhoTosaParametroPorte", back_populates="precos")
