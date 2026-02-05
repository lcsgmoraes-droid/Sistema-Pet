"""
Model para Rotas de Entrega - ETAPA 9.3
"""
from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.base_models import BaseTenantModel


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
    entregador_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    
    # Endereço
    endereco_destino = Column(Text, nullable=True)
    
    # ETAPA 9.4+: Pontos inicial e final da rota
    ponto_inicial_rota = Column(Text, nullable=True)  # Origem da rota (configurável)
    ponto_final_rota = Column(Text, nullable=True)  # Destino final (por padrão = ponto_inicial)
    retorna_origem = Column(Boolean, nullable=False, default=True)  # Se volta para origem
    
    # Distância
    distancia_prevista = Column(Numeric(10, 2), nullable=True)
    distancia_real = Column(Numeric(10, 2), nullable=True)
    
    # Custo
    custo_previsto = Column(Numeric(10, 2), nullable=True)
    custo_real = Column(Numeric(10, 2), nullable=True)
    custo_moto = Column(Numeric(10, 2), nullable=True, default=0)  # ETAPA 11.1: custo da moto separado
    
    # Repasse da taxa (ETAPA 7.1 - PDV → Rota → Acerto)
    taxa_entrega_cliente = Column(Numeric(10, 2), nullable=True)  # Valor total da taxa paga pelo cliente
    valor_repasse_entregador = Column(Numeric(10, 2), nullable=True)  # Parte que vai para o entregador
    
    # Controle operacional
    tentativas = Column(Integer, nullable=False, default=1)
    moto_da_loja = Column(Boolean, nullable=False, default=False)
    
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
    paradas = relationship("RotaEntregaParada", back_populates="rota", cascade="all, delete-orphan")


class RotaEntregaParada(BaseTenantModel):
    """
    ETAPA 9.3 - Paradas de uma rota com sequência otimizada
    
    Armazena a ordem otimizada pelo Google Directions API,
    com distância e tempo acumulados para cada parada.
    """
    __tablename__ = "rotas_entrega_paradas"
    
    rota_id = Column(Integer, ForeignKey("rotas_entrega.id"), nullable=False, index=True)
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
    
    # Relacionamentos
    rota = relationship("RotaEntrega", back_populates="paradas")
    
    # created_at herdado de BaseTenantModel
