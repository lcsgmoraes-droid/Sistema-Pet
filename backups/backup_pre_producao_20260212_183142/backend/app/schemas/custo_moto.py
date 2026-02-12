"""
Schemas para Configuração de Custos da Moto
"""
from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal


class ConfiguracaoCustoMotoBase(BaseModel):
    """Schema base para configuração de custos da moto"""
    
    # Combustível
    preco_combustivel: Decimal = Field(default=0, description="Preço do combustível por litro")
    km_por_litro: Decimal = Field(default=0, description="Média de KM por litro")
    
    # Manutenções (por KM)
    km_troca_oleo: Optional[int] = Field(None, description="KM para troca de óleo")
    custo_troca_oleo: Optional[Decimal] = Field(None, description="Custo da troca de óleo")
    
    km_troca_pneu_dianteiro: Optional[int] = None
    custo_pneu_dianteiro: Optional[Decimal] = None
    
    km_troca_pneu_traseiro: Optional[int] = None
    custo_pneu_traseiro: Optional[Decimal] = None
    
    km_troca_kit: Optional[int] = Field(None, description="KM para troca do kit (corrente, coroa, pinhão)")
    custo_troca_kit: Optional[Decimal] = Field(None, description="Custo da troca do kit de transmissão")
    
    km_manutencao_geral: Optional[int] = None
    custo_manutencao_geral: Optional[Decimal] = None
    
    # Custos fixos mensais
    seguro_mensal: Optional[Decimal] = Field(default=0, description="Seguro mensal")
    ipva_mensal: Optional[Decimal] = Field(default=0, description="IPVA rateado mensalmente")
    licenciamento_anual: Optional[Decimal] = Field(default=0, description="Licenciamento anual")
    inspecao_anual: Optional[Decimal] = Field(default=0, description="Inspeção veicular anual")
    lavagem_mensal: Optional[Decimal] = Field(default=0, description="Lavagem/limpeza mensal")
    outros_custos_mensais: Optional[Decimal] = Field(default=0, description="Outros custos fixos mensais")
    
    # KM médio mensal
    km_medio_mensal: Optional[Decimal] = Field(default=1000, description="KM médio mensal para ratear custos fixos")


class ConfiguracaoCustoMotoCreate(ConfiguracaoCustoMotoBase):
    """Schema para criação de configuração"""
    pass


class ConfiguracaoCustoMotoUpdate(ConfiguracaoCustoMotoBase):
    """Schema para atualização de configuração"""
    pass


class ConfiguracaoCustoMotoResponse(ConfiguracaoCustoMotoBase):
    """Schema de resposta com dados completos"""
    id: int
    tenant_id: str
    
    model_config = {"from_attributes": True}


class SimulacaoCustoResponse(BaseModel):
    """Schema de resposta para simulação de custos"""
    custo_por_km: float
    breakdown: dict
    exemplos: dict
