"""Schemas da analise avancada de racoes."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class FiltrosAnalise(BaseModel):
    """Filtros dinâmicos para análises"""

    especies: Optional[List[str]] = None  # dog, cat, both
    linhas: Optional[List[int]] = None  # IDs da tabela linhas_racao
    portes: Optional[List[int]] = None  # IDs da tabela portes_animal
    fases: Optional[List[int]] = None  # IDs da tabela fases_publico
    tratamentos: Optional[List[int]] = None  # IDs da tabela tipos_tratamento
    sabores: Optional[List[str]] = None  # Strings de sabor_proteina
    pesos: Optional[List[float]] = None  # Valores em kg
    marca_ids: Optional[List[int]] = None
    categoria_ids: Optional[List[int]] = None
    margem_min: Optional[float] = None
    margem_max: Optional[float] = None
    preco_min: Optional[float] = None
    preco_max: Optional[float] = None
    data_inicio: Optional[str] = None  # Para vendas
    data_fim: Optional[str] = None


class AnaliseMargemSegmento(BaseModel):
    """Resultado de análise de margem por segmento"""

    segmento: str
    tipo_segmento: str  # "porte", "fase", "sabor", etc
    total_produtos: int
    margem_media: float
    margem_minima: float
    margem_maxima: float
    preco_medio_kg: float
    preco_minimo_kg: float
    preco_maximo_kg: float
    total_vendido: Optional[int] = 0
    faturamento: Optional[float] = 0.0


class ComparacaoMarca(BaseModel):
    """Comparação de preços entre marcas"""

    marca_id: int
    marca_nome: str
    total_produtos: int
    preco_medio_kg: float
    margem_media: float
    produto_mais_barato: Dict[str, Any]
    produto_mais_caro: Dict[str, Any]


class RankingProduto(BaseModel):
    """Produto no ranking de vendas"""

    produto_id: int
    nome: str
    marca: str
    categoria: str
    quantidade_vendida: int
    faturamento: float
    margem_media: float
    preco_medio_venda: float


class DashboardResumo(BaseModel):
    """Resumo geral do dashboard"""

    total_racoes: int
    total_classificadas: int
    percentual_classificadas: float
    marcas_cadastradas: int
    faturamento_periodo: float
    margem_media_geral: float
    produto_mais_vendido: Optional[Dict[str, Any]] = None
    segmento_mais_rentavel: Optional[Dict[str, Any]] = None
