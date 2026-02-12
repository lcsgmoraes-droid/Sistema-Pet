"""
Model para Configuração de Custos da Moto
ETAPA 8 - Controle de custos da moto da loja
"""
from sqlalchemy import Column, Integer, Numeric, DateTime
from sqlalchemy.sql import func
from app.base_models import BaseTenantModel


class ConfiguracaoCustoMoto(BaseTenantModel):
    """
    Configuração de custos da moto da loja.
    Um registro por tenant.
    """
    __tablename__ = "configuracoes_custo_moto"
    
    # Combustível
    preco_combustivel = Column(Numeric(10, 2), nullable=False, default=0)
    km_por_litro = Column(Numeric(10, 2), nullable=False, default=0)
    
    # Manutenções preventivas (por KM)
    km_troca_oleo = Column(Integer, nullable=True)
    custo_troca_oleo = Column(Numeric(10, 2), nullable=True)
    
    km_troca_pneu_dianteiro = Column(Integer, nullable=True)
    custo_pneu_dianteiro = Column(Numeric(10, 2), nullable=True)
    
    km_troca_pneu_traseiro = Column(Integer, nullable=True)
    custo_pneu_traseiro = Column(Numeric(10, 2), nullable=True)
    
    km_troca_kit = Column(Integer, nullable=True)  # Kit de transmissão (corrente, coroa, pinhão)
    custo_troca_kit = Column(Numeric(10, 2), nullable=True)
    
    km_manutencao_geral = Column(Integer, nullable=True)
    custo_manutencao_geral = Column(Numeric(10, 2), nullable=True)
    
    # Custos fixos mensais
    seguro_mensal = Column(Numeric(10, 2), nullable=True, default=0)
    ipva_mensal = Column(Numeric(10, 2), nullable=True, default=0)
    licenciamento_anual = Column(Numeric(10, 2), nullable=True, default=0)  # Rateado mensalmente
    inspecao_anual = Column(Numeric(10, 2), nullable=True, default=0)  # Vistoria veicular
    lavagem_mensal = Column(Numeric(10, 2), nullable=True, default=0)  # Limpeza/estética
    outros_custos_mensais = Column(Numeric(10, 2), nullable=True, default=0)
    
    # KM médio mensal (para ratear custos fixos)
    km_medio_mensal = Column(Numeric(10, 2), nullable=True, default=1000)  # Fallback
    
    # created_at e updated_at herdados de BaseTenantModel
