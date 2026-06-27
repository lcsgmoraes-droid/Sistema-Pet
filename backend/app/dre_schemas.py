"""Schemas de resposta da DRE."""

from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel


class DREResponse(BaseModel):
    # Período
    periodo: str
    mes: int
    ano: int

    # RECEITAS
    receita_bruta: Decimal
    vendas_produtos: Decimal
    vendas_servicos: Decimal
    outras_receitas: Decimal

    # DEDUÇÕES
    deducoes_total: Decimal
    descontos: Decimal
    devolucoes: Decimal

    # RECEITA LÍQUIDA
    receita_liquida: Decimal

    # CUSTOS
    cmv: Decimal  # Custo das Mercadorias Vendidas

    # LUCRO BRUTO
    lucro_bruto: Decimal
    margem_bruta: float

    # DESPESAS OPERACIONAIS
    despesas_operacionais: Decimal
    despesas_pessoal: Decimal
    despesas_administrativas: Decimal
    taxas_cartao: Decimal
    outras_despesas: Decimal

    # RESULTADO OPERACIONAL
    resultado_operacional: Decimal
    margem_operacional: float

    # RESULTADO FINANCEIRO
    resultado_financeiro: Decimal
    receitas_financeiras: Decimal
    despesas_financeiras: Decimal

    # LUCRO LÍQUIDO
    lucro_liquido: Decimal
    margem_liquida: float

    model_config = {"from_attributes": True}


class DREDetalhado(BaseModel):
    """DRE com detalhamento de cada categoria"""

    dre: DREResponse
    detalhes_despesas: List[dict]
    detalhes_receitas: List[dict]
    comparacao_mes_anterior: Optional[dict] = None

    model_config = {"from_attributes": True}


# ==================== FUNÇÕES AUXILIARES ====================
