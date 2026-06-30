from datetime import date
from typing import List, Optional

from pydantic import BaseModel


class DREResumo(BaseModel):
    id: int
    data_inicio: date
    data_fim: date
    mes: Optional[int]
    ano: Optional[int]
    receita_liquida: float
    lucro_liquido: float
    margem_liquida_percent: float
    status: str
    score_saude: int

    model_config = {"from_attributes": True}


class DRECompleto(BaseModel):
    id: int
    data_inicio: date
    data_fim: date

    # Receitas
    receita_bruta: float
    deducoes_receita: float
    receita_liquida: float

    # Custos
    custo_produtos_vendidos: float
    lucro_bruto: float
    margem_bruta_percent: float

    # Despesas
    despesas_vendas: float
    despesas_administrativas: float
    despesas_financeiras: float
    outras_despesas: float
    total_despesas_operacionais: float

    # Resultados
    lucro_operacional: float
    margem_operacional_percent: float
    lucro_liquido: float
    margem_liquida_percent: float

    # Análises
    status: str
    score_saude: int

    model_config = {"from_attributes": True}


class ProdutoRentabilidade(BaseModel):
    id: int
    produto_id: int
    produto_nome: str
    categoria: str
    quantidade_vendida: int
    receita_total: float
    custo_total: float
    lucro_total: float
    margem_percent: float
    ranking_rentabilidade: int
    eh_lucrativo: bool
    recomendacao: Optional[str]

    model_config = {"from_attributes": True}


class CategoriaRentabilidade(BaseModel):
    id: int
    categoria_nome: str
    quantidade_vendida: int
    receita_total: float
    custo_total: float
    lucro_total: float
    margem_percent: float
    participacao_receita_percent: float
    eh_categoria_principal: bool

    model_config = {"from_attributes": True}


class InsightDRE(BaseModel):
    id: int
    tipo: str
    categoria: str
    titulo: str
    descricao: str
    impacto: str
    acao_sugerida: Optional[str]
    impacto_estimado: Optional[float]
    foi_lido: bool

    model_config = {"from_attributes": True}


class CalcularDRERequest(BaseModel):
    data_inicio: date
    data_fim: date


class CalcularDRECanalRequest(BaseModel):
    data_inicio: date
    data_fim: date
    canal: str  # 'loja_fisica', 'mercado_livre', etc

    model_config = {
        "json_schema_extra": {
            "example": {
                "data_inicio": "2026-01-01",
                "data_fim": "2026-01-31",
                "canal": "mercado_livre",
            }
        }
    }


class CalcularDREConsolidadoRequest(BaseModel):
    data_inicio: date
    data_fim: date
    canais: List[str]  # ['loja_fisica', 'mercado_livre', 'shopee']

    model_config = {
        "json_schema_extra": {
            "example": {
                "data_inicio": "2026-01-01",
                "data_fim": "2026-01-31",
                "canais": ["mercado_livre", "shopee"],
            }
        }
    }


class CalcularDREDetalhadadRequest(BaseModel):
    data_inicio: date
    data_fim: date
    canal: str  # 'loja_fisica', 'mercado_livre', etc


class DREDetalheResponse(BaseModel):
    """Uma linha de DRE (um canal específico)"""

    id: int
    canal: str
    receita_bruta: float
    receita_liquida: float
    custo_produtos_vendidos: float
    lucro_bruto: float
    total_despesas_operacionais: float
    lucro_operacional: float
    impostos: float
    lucro_liquido: float
    margem_liquida_percent: float
    status: str
    score_saude: float

    model_config = {"from_attributes": True}


class AlocarDespesaRequest(BaseModel):
    data_inicio: date
    data_fim: date
    categoria: str  # 'aluguel', 'salário', 'internet', etc
    valor_total: float
    modo: str  # 'proporcional' ou 'manual'
    canais: List[str]
    usar_faturamento: bool = True
    alocacao_manual: Optional[dict] = None  # Se modo='manual'
