"""
Schemas Pydantic para Segmentação de Clientes
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


class MetricasCliente(BaseModel):
    """Métricas calculadas do cliente"""
    total_compras_90d: float = Field(..., description="Total gasto nos últimos 90 dias")
    compras_90d: int = Field(..., description="Quantidade de compras nos últimos 90 dias")
    ticket_medio: float = Field(..., description="Ticket médio de compras")
    ultima_compra_dias: int = Field(..., description="Dias desde a última compra")
    primeira_compra_dias: int = Field(..., description="Dias desde a primeira compra")
    total_em_aberto: float = Field(..., description="Total de contas em aberto")
    compras_90d_anteriores: int = Field(..., description="Quantidade de compras no período anterior (90-180 dias)")
    total_historico: float = Field(..., description="Total gasto desde sempre")
    total_compras_historico: int = Field(..., description="Total de compras desde sempre")


class SegmentoResponse(BaseModel):
    """Response com dados do segmento do cliente"""
    id: Optional[int] = None
    cliente_id: int
    cliente_nome: Optional[str] = None
    segmento: str = Field(..., description="Segmento principal: VIP, Recorrente, Novo, Inativo, Endividado, Risco, Regular")
    tags: List[str] = Field(default_factory=list, description="Lista de tags/segmentos aplicáveis")
    metricas: MetricasCliente
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "cliente_id": 123,
                "cliente_nome": "João Silva",
                "segmento": "VIP",
                "tags": ["VIP", "Recorrente"],
                "metricas": {
                    "total_compras_90d": 2500.00,
                    "compras_90d": 5,
                    "ticket_medio": 500.00,
                    "ultima_compra_dias": 10,
                    "primeira_compra_dias": 365,
                    "total_em_aberto": 0.00,
                    "compras_90d_anteriores": 3,
                    "total_historico": 8500.00,
                    "total_compras_historico": 15
                },
                "updated_at": "2026-01-23T10:30:00"
            }
        }


class RecalcularSegmentoResponse(BaseModel):
    """Response do recálculo de segmento individual"""
    cliente_id: int
    cliente_nome: str
    segmento: str
    tags: List[str]
    metricas: Dict
    updated_at: str
    mensagem: str = "Segmento recalculado com sucesso"


class RecalcularTodosRequest(BaseModel):
    """Request para recalcular todos os segmentos"""
    limit: Optional[int] = Field(None, description="Limite de clientes a processar (None = todos)", ge=1)


class DetalheProcessamento(BaseModel):
    """Detalhe do processamento de um cliente"""
    cliente_id: int
    nome: str
    segmento: Optional[str] = None
    status: str  # 'ok' ou 'erro'
    mensagem: Optional[str] = None


class RecalcularTodosResponse(BaseModel):
    """Response do recálculo em lote"""
    total_processados: int
    sucessos: int
    erros: int
    detalhes: List[DetalheProcessamento]
    distribuicao_segmentos: Dict[str, int] = Field(
        default_factory=dict,
        description="Contagem de clientes por segmento"
    )
    mensagem: str = "Processamento concluído"


class ListarSegmentosResponse(BaseModel):
    """Response da listagem de segmentos"""
    total: int
    segmentos: List[SegmentoResponse]


class EstatisticasSegmentosResponse(BaseModel):
    """Response com estatísticas dos segmentos"""
    distribuicao: Dict[str, int] = Field(
        ...,
        description="Quantidade de clientes por segmento"
    )
    total_clientes: int
    ultima_atualizacao: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "distribuicao": {
                    "VIP": 45,
                    "Recorrente": 120,
                    "Novo": 30,
                    "Regular": 200,
                    "Inativo": 50,
                    "Endividado": 15,
                    "Risco": 25
                },
                "total_clientes": 485,
                "ultima_atualizacao": "2026-01-23T10:30:00"
            }
        }
