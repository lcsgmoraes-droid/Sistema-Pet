"""Schemas do fluxo de caixa financeiro."""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel


class FluxoCaixaMovimentacao(BaseModel):
    """Uma movimentação no fluxo de caixa"""

    data: date
    tipo: str  # entrada, saida, projecao_entrada, projecao_saida
    descricao: str
    categoria: str
    valor: float
    origem_tipo: (
        str  # venda, conta_receber, conta_pagar, lancamento_manual, saldo_inicial
    )
    origem_id: Optional[int] = None
    numero_venda: Optional[str] = (
        None  # Número da venda quando origem for venda ou conta_receber de venda
    )
    status: str = "realizado"  # previsto ou realizado


class FluxoCaixaPeriodo(BaseModel):
    """Resumo de um período no fluxo de caixa - Estilo Flua"""

    data: str  # Data ou descrição do período (ex: "15/01/2026" ou "Semana 3")
    data_inicio: date  # Data início do período
    data_fim: date  # Data fim do período

    # PREVISTO
    previsto_entradas: float
    previsto_saidas: float
    previsto_saldo: float

    # REALIZADO
    realizado_entradas: float
    realizado_saidas: float
    realizado_saldo: float

    # SALDO
    saldo_inicial: float
    saldo_final: float


class FluxoCaixaResponse(BaseModel):
    """Resposta completa do fluxo de caixa - Estilo Flua"""

    periodos: List[FluxoCaixaPeriodo]
    movimentacoes: List[FluxoCaixaMovimentacao]

    # Totalizadores PREVISTO
    total_previsto_entradas: float
    total_previsto_saidas: float

    # Totalizadores REALIZADO
    total_realizado_entradas: float
    total_realizado_saidas: float

    # Saldos
    saldo_inicial: float
    saldo_final: float
    saldo_previsto_final: float
