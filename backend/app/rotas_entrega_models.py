"""
Model para Rotas de Entrega - ETAPA 9.3
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.base_models import BaseTenantModel
from app.db import Base

# Import necessário para resolver relacionamento com Venda
# Colocado depois dos imports base para evitar circular dependency
import app.vendas_models  # noqa: F401 - import necessário para SQLAlchemy resolver relationship("Venda")


class RotaEntrega(BaseTenantModel):
    """
    Tabela de rotas de entrega.
    Registra cada entrega realizada, custos e status.
    """

    __tablename__ = "rotas_entrega"

    # ID herdado de BaseTenantModel com Identity(always=True)
    # tenant_id herdado de BaseTenantModel

    numero = Column(String(20), nullable=False, unique=True, index=True)

    # Vinculações
    venda_id = Column(Integer, ForeignKey("vendas.id"), nullable=True, index=True)
    entregador_id = Column(
        Integer, ForeignKey("clientes.id"), nullable=False, index=True
    )

    # Endereço
    endereco_destino = Column(Text, nullable=True)

    # ETAPA 9.4+: Pontos inicial e final da rota
    ponto_inicial_rota = Column(Text, nullable=True)  # Origem da rota (configurável)
    ponto_final_rota = Column(
        Text, nullable=True
    )  # Destino final (por padrão = ponto_inicial)
    retorna_origem = Column(
        Boolean, nullable=False, default=True
    )  # Se volta para origem

    # Distância
    distancia_prevista = Column(Numeric(10, 2), nullable=True)
    distancia_real = Column(Numeric(10, 2), nullable=True)

    # Custo
    custo_previsto = Column(Numeric(10, 2), nullable=True)
    custo_real = Column(Numeric(10, 2), nullable=True)
    custo_moto = Column(
        Numeric(10, 2), nullable=True, default=0
    )  # ETAPA 11.1: custo da moto separado

    # Repasse da taxa (ETAPA 7.1 - PDV → Rota → Acerto)
    taxa_entrega_cliente = Column(
        Numeric(10, 2), nullable=True
    )  # Valor total da taxa paga pelo cliente
    valor_repasse_entregador = Column(
        Numeric(10, 2), nullable=True
    )  # Parte que vai para o entregador

    # Controle operacional
    tentativas = Column(Integer, nullable=False, default=1)
    moto_da_loja = Column(Boolean, nullable=False, default=False)

    # Controle de KM da moto (opcional)
    km_inicial = Column(Numeric(10, 2), nullable=True)  # KM ao iniciar rota
    km_final = Column(Numeric(10, 2), nullable=True)  # KM ao finalizar rota

    # Status
    status = Column(String(20), nullable=False, default="pendente", index=True)
    # pendente | em_rota | concluida | cancelada

    # Auditoria
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    data_inicio = Column(DateTime, nullable=True)  # ETAPA 9.4: Quando iniciou a rota
    data_conclusao = Column(DateTime, nullable=True)
    observacoes = Column(Text, nullable=True)

    # created_at e updated_at herdados de BaseTenantModel

    # ETAPA 9.3: Relacionamento com paradas (ordem otimizada)
    paradas = relationship(
        "RotaEntregaParada", back_populates="rota", cascade="all, delete-orphan"
    )

    # Relacionamento com entregador
    entregador = relationship("Cliente", foreign_keys=[entregador_id], lazy="joined")


class RotaEntregaRastreioToken(Base):
    """Indice global minimo para resolver um token publico antes do tenant."""

    __tablename__ = "rotas_entrega_rastreio_tokens"

    token = Column(String(64), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    rota_id = Column(
        Integer,
        ForeignKey("rotas_entrega.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RotaEntregaParada(BaseTenantModel):
    """
    ETAPA 9.3 - Paradas de uma rota com sequência otimizada

    Armazena a ordem otimizada pelo Google Directions API,
    com distância e tempo acumulados para cada parada.
    """

    __tablename__ = "rotas_entrega_paradas"

    rota_id = Column(
        Integer, ForeignKey("rotas_entrega.id"), nullable=False, index=True
    )
    venda_id = Column(Integer, ForeignKey("vendas.id"), nullable=False, index=True)

    ordem = Column(Integer, nullable=False)  # 1, 2, 3... (ordem de entrega)
    endereco = Column(Text, nullable=False)

    # Métricas acumuladas até esta parada
    distancia_acumulada = Column(Numeric(10, 2), nullable=True)  # km
    tempo_acumulado = Column(Integer, nullable=True)  # segundos

    # ETAPA 9.4: Controle de entrega
    status = Column(String(20), nullable=False, default="pendente", index=True)
    # pendente | entregue | tentativa
    data_entrega = Column(DateTime, nullable=True)
    observacoes = Column(Text, nullable=True)  # Observações sobre a entrega
    km_entrega = Column(
        Numeric(10, 2), nullable=True
    )  # KM da moto ao entregar (opcional)

    # Snapshot do custo operacional da entrega. O valor-base/modelo ficam
    # congelados ao iniciar a rota; o valor final por KM e fechado ao concluir.
    tentativas = Column(Integer, nullable=False, default=1)
    modelo_custo_operacional = Column(String(24), nullable=True)
    valor_base_custo_operacional = Column(Numeric(12, 4), nullable=True)
    distancia_custo_km = Column(Numeric(10, 3), nullable=True)
    custo_operacional = Column(Numeric(12, 2), nullable=True)
    custo_moto_rateado = Column(Numeric(12, 2), nullable=True, default=0)
    custo_calculado_em = Column(DateTime, nullable=True)

    # Relacionamentos
    rota = relationship("RotaEntrega", back_populates="paradas")
    # Usando lazy='select' para evitar problemas de inicialização de mapper
    venda = relationship("Venda", backref="paradas_rota", lazy="select")

    # created_at herdado de BaseTenantModel
