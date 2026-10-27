"""Tarifas da Meta e fechamento mensal do consumo de WhatsApp por loja.

Tabelas da PLATAFORMA (sem isolamento por loja): quem le e escreve e a equipe do
OPS, que precisa ver todas as lojas de uma vez. Os valores das tarifas sao
cadastrados por quem opera o OPS a partir da tabela de precos oficial da Meta.
"""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db import Base

CATEGORIAS_DE_TARIFA = (
    "marketing",
    "utility",
    "authentication",
    "authentication_international",
    "service",
)


class WhatsAppTarifa(Base):
    """Preco por mensagem (em reais) de uma categoria, valido a partir de uma data."""

    __tablename__ = "whatsapp_tarifas"
    __table_args__ = (
        UniqueConstraint(
            "categoria", "vigente_desde", name="uq_whatsapp_tarifas_categoria_data"
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    categoria = Column(String(30), nullable=False)
    moeda = Column(String(3), nullable=False, default="BRL", server_default="BRL")
    # Em reais, com casas decimais (a Meta cobra frações de centavo por mensagem).
    valor = Column(Numeric(12, 6), nullable=False)
    vigente_desde = Column(Date, nullable=False)
    criado_por = Column(String(255), nullable=True)
    criado_em = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class WhatsAppFechamento(Base):
    """Fotografia do consumo de uma loja em um mes, para repasse e conferencia."""

    __tablename__ = "whatsapp_fechamentos"
    __table_args__ = (
        UniqueConstraint("tenant_id", "mes", name="uq_whatsapp_fechamentos_tenant_mes"),
        Index("ix_whatsapp_fechamentos_mes", "mes"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    mes = Column(String(7), nullable=False)  # AAAA-MM
    enviadas = Column(Integer, nullable=False, default=0)
    recebidas = Column(Integer, nullable=False, default=0)
    falhas = Column(Integer, nullable=False, default=0)
    cobraveis = Column(Integer, nullable=False, default=0)
    cobraveis_sem_tarifa = Column(Integer, nullable=False, default=0)
    por_categoria = Column(Text, nullable=True)  # JSON {categoria: quantidade}
    custo_estimado = Column(Numeric(14, 2), nullable=False, default=0)
    margem_percentual = Column(Numeric(6, 2), nullable=False, default=0)
    valor_repasse = Column(Numeric(14, 2), nullable=False, default=0)
    # Informado depois, quando a fatura da Meta chega para a loja.
    fatura_meta = Column(Numeric(14, 2), nullable=True)
    divergencia = Column(Numeric(14, 2), nullable=True)  # fatura - custo estimado
    observacao = Column(Text, nullable=True)
    conferido = Column(Boolean, nullable=False, default=False)
    fechado_por = Column(String(255), nullable=False)
    fechado_em = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
