"""
Schemas Pydantic para Rotas de Entrega - ETAPA 9.3
"""
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel


class ClienteEntregadorResponse(BaseModel):
    """Schema simplificado de Cliente para entregador"""
    id: int
    nome: str
    telefone: Optional[str] = None
    celular: Optional[str] = None
    
    model_config = {"from_attributes": True}


class RotaEntregaBase(BaseModel):
    """Schema base para rotas de entrega"""
    venda_id: Optional[int] = None
    entregador_id: int
    endereco_destino: Optional[str] = None
    
    # ETAPA 9.4+: Pontos inicial e final
    ponto_inicial_rota: Optional[str] = None
    ponto_final_rota: Optional[str] = None
    retorna_origem: Optional[bool] = True  # Por padrão volta para origem
    
    distancia_prevista: Optional[Decimal] = None
    custo_previsto: Optional[Decimal] = None
    
    # Repasse da taxa (ETAPA 7.1)
    taxa_entrega_cliente: Optional[Decimal] = None
    valor_repasse_entregador: Optional[Decimal] = None
    
    moto_da_loja: Optional[bool] = False
    observacoes: Optional[str] = None


class RotaEntregaCreate(RotaEntregaBase):
    """Schema para criação de rota de entrega"""
    # ETAPA 9.3: Criar rota com múltiplas vendas (entregas)
    vendas_ids: Optional[List[int]] = None  # Lista de vendas para entregar


class RotaEntregaUpdate(BaseModel):
    """Schema para atualização de rota de entrega"""
    distancia_real: Optional[Decimal] = None
    tentativas: Optional[int] = None
    observacoes: Optional[str] = None
    status: Optional[str] = None


class RotaEntregaParadaResponse(BaseModel):
    """ETAPA 9.3 - Schema de resposta para parada da rota"""
    id: int
    rota_id: int
    venda_id: int
    ordem: int
    endereco: str
    distancia_acumulada: Optional[Decimal] = None
    tempo_acumulado: Optional[int] = None
    status: str = "pendente"  # ETAPA 9.4: pendente | entregue | tentativa
    data_entrega: Optional[datetime] = None  # ETAPA 9.4
    created_at: datetime
    
    model_config = {"from_attributes": True}


class RotaEntregaResponse(RotaEntregaBase):
    """Schema de resposta para rota de entrega"""
    id: int
    numero: str
    status: str
    
    distancia_real: Optional[Decimal] = None
    custo_real: Optional[Decimal] = None
    tentativas: int
    
    taxa_entrega_cliente: Optional[Decimal] = None
    valor_repasse_entregador: Optional[Decimal] = None
    
    created_at: datetime
    data_inicio: Optional[datetime] = None  # ETAPA 9.4: Quando iniciou
    data_conclusao: Optional[datetime] = None
    
    # ETAPA 9.3: Incluir paradas ordenadas
    paradas: Optional[List[RotaEntregaParadaResponse]] = []
    
    # Incluir dados do entregador
    entregador: Optional[ClienteEntregadorResponse] = None

    model_config = {"from_attributes": True}


class RotaEntregaFechar(BaseModel):
    """Schema para fechamento de rota"""
    distancia_real: Decimal
    tentativas: int = 1
    observacoes: Optional[str] = None
