"""Creditos de WhatsApp: franquia mensal da loja + pacotes avulsos comprados.

- Movimentos (por loja, com RLS): compras, ajustes e consumos de creditos.
- Pacotes, tabela de custo em creditos e pedidos de compra: tabelas da PLATAFORMA
  (sem RLS), porque o OPS administra o catalogo e confirma os pagamentos.

Os numeros de custo em creditos sao valores de exemplo ate o tema T.1 do roadmap
(modelo de cobranca) ser fechado; eles sao editaveis no OPS.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.base_models import BaseTenantModel
from app.db import Base

MOVIMENTO_COMPRA = "compra"
MOVIMENTO_CONSUMO = "consumo"
MOVIMENTO_AJUSTE = "ajuste"

FONTE_FRANQUIA = "franquia"
FONTE_AVULSO = "avulso"

COMPRA_PENDENTE = "pendente"
COMPRA_PAGA = "paga"
COMPRA_CANCELADA = "cancelada"


class WhatsAppCreditoMovimento(BaseTenantModel):
    """Entrada (+) ou saida (-) de creditos de uma loja."""

    __tablename__ = "whatsapp_creditos_movimentos"
    __table_args__ = (
        Index("ix_whatsapp_creditos_mov_tenant_mes", "tenant_id", "mes"),
        Index("ix_whatsapp_creditos_mov_tenant_tipo", "tenant_id", "tipo"),
    )

    tipo = Column(String(12), nullable=False)  # compra | consumo | ajuste
    fonte = Column(String(10), nullable=False)  # franquia | avulso
    quantidade = Column(Integer, nullable=False)  # + entra, - sai
    mes = Column(String(7), nullable=False)  # AAAA-MM
    referencia = Column(String(255), nullable=True)  # ID da mensagem na Meta
    compra_id = Column(Integer, nullable=True)
    descricao = Column(String(200), nullable=True)
    criado_por = Column(String(255), nullable=True)


class WhatsAppPacote(Base):
    """Pacote avulso de creditos que a loja pode comprar."""

    __tablename__ = "whatsapp_pacotes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(80), nullable=False)
    creditos = Column(Integer, nullable=False)
    preco = Column(Numeric(10, 2), nullable=False)
    ativo = Column(Boolean, nullable=False, default=True, server_default="true")
    criado_por = Column(String(255), nullable=True)
    criado_em = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class WhatsAppCustoCredito(Base):
    """Quanto cada tipo de envio consome (sobrepoe o padrao do codigo)."""

    __tablename__ = "whatsapp_custos_creditos"

    chave = Column(String(40), primary_key=True)
    creditos = Column(Integer, nullable=False)
    atualizado_por = Column(String(255), nullable=True)
    atualizado_em = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class WhatsAppCompraPacote(Base):
    """Pedido de compra de um pacote. O OPS confirma o pagamento e libera os creditos."""

    __tablename__ = "whatsapp_compras_pacote"
    __table_args__ = (Index("ix_whatsapp_compras_status", "status", "solicitado_em"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    pacote_id = Column(Integer, ForeignKey("whatsapp_pacotes.id"), nullable=False)
    # Copia do pacote no momento do pedido (o catalogo pode mudar depois).
    pacote_nome = Column(String(80), nullable=False)
    creditos = Column(Integer, nullable=False)
    preco = Column(Numeric(10, 2), nullable=False)
    status = Column(String(12), nullable=False, default=COMPRA_PENDENTE)
    solicitado_por = Column(String(255), nullable=False)
    solicitado_em = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    confirmado_por = Column(String(255), nullable=True)
    confirmado_em = Column(DateTime(timezone=True), nullable=True)
    observacao = Column(Text, nullable=True)
