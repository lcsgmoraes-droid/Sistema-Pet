from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class TransferenciaParceiroEntradaItemRequest(BaseModel):
    """Item recebido de parceiro, com divida opcionalmente entrando no estoque."""

    produto_id: int
    quantidade: float = Field(gt=0)
    custo_unitario: Optional[float] = Field(default=None, ge=0)
    valor_total: Optional[float] = Field(default=None, ge=0)


class TransferenciaParceiroEntradaRequest(BaseModel):
    """Entrada de produto vindo de parceiro, gerando conta a pagar."""

    parceiro_id: int
    data_emissao: Optional[date] = None
    data_vencimento: Optional[date] = None
    documento: Optional[str] = None
    observacao: Optional[str] = None
    entrar_estoque: bool = True
    itens: List[TransferenciaParceiroEntradaItemRequest] = Field(
        default_factory=list, min_items=1
    )


class TransferenciaParceiroEntradaResponse(BaseModel):
    sucesso: bool
    documento: str
    conta_pagar_id: int
    parceiro_id: int
    total_divida: float
    entrar_estoque: bool
    movimentacoes_estoque: List[int] = Field(default_factory=list)


class TransferenciaParceiroEntradaHistoricoItem(BaseModel):
    conta_pagar_id: int
    documento: Optional[str] = None
    parceiro_id: Optional[int] = None
    parceiro_nome: str
    parceiro_codigo: Optional[str] = None
    descricao: str
    data_emissao: Optional[date] = None
    data_vencimento: Optional[date] = None
    data_pagamento: Optional[date] = None
    status: str
    status_label: str
    valor_original: float = 0
    valor_pago: float = 0
    saldo_aberto: float = 0
    estoque_atualizado: bool = False
    observacoes: Optional[str] = None


class TransferenciaParceiroEntradaHistoricoTotais(BaseModel):
    total_registros: int = 0
    valor_total: float = 0
    valor_pago: float = 0
    saldo_aberto: float = 0
    pendentes: int = 0
    pagas: int = 0
    vencidas: int = 0


class TransferenciaParceiroEntradaHistoricoResponse(BaseModel):
    items: List[TransferenciaParceiroEntradaHistoricoItem] = Field(default_factory=list)
    totais: TransferenciaParceiroEntradaHistoricoTotais
    total: int
    page: int
    page_size: int
    pages: int
