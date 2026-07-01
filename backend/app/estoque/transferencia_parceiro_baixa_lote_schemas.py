from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class TransferenciaParceiroBaixaLotePreviewRequest(BaseModel):
    parceiro_id: int
    valor_total: float = Field(gt=0)
    ordem: str = Field(default="antiga")
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None


class TransferenciaParceiroBaixaLoteAplicacaoRequest(BaseModel):
    conta_receber_id: int
    valor_baixado: float = Field(gt=0)


class TransferenciaParceiroNovaContaPagarAcertoRequest(BaseModel):
    descricao: Optional[str] = None
    valor: float = Field(gt=0)
    data_vencimento: Optional[date] = None
    documento: Optional[str] = None
    observacao: Optional[str] = None
    categoria_id: Optional[int] = None
    dre_subcategoria_id: Optional[int] = None
    tipo_despesa_id: Optional[int] = None


class TransferenciaParceiroBaixaLoteRequest(BaseModel):
    parceiro_id: int
    modo_baixa: str = Field(default="recebimento")
    data_recebimento: date = Field(default_factory=date.today)
    forma_pagamento_id: Optional[int] = None
    observacao: Optional[str] = None
    devolver_estoque: bool = False
    aplicacoes: List[TransferenciaParceiroBaixaLoteAplicacaoRequest] = Field(
        default_factory=list, min_items=1
    )
    compensacoes: list = Field(default_factory=list)
    nova_conta_pagar_acerto: Optional[
        TransferenciaParceiroNovaContaPagarAcertoRequest
    ] = None


class TransferenciaParceiroBaixaLotePreviewItem(BaseModel):
    conta_receber_id: int
    documento: Optional[str] = None
    data_emissao: Optional[date] = None
    data_vencimento: Optional[date] = None
    valor_original: float = 0
    valor_recebido: float = 0
    saldo_aberto: float = 0
    valor_sugerido: float = 0


class TransferenciaParceiroBaixaLotePreviewResponse(BaseModel):
    items: List[TransferenciaParceiroBaixaLotePreviewItem] = Field(default_factory=list)
    total_aberto: float = 0
    total_sugerido: float = 0
    valor_restante: float = 0


class TransferenciaParceiroBaixaLoteResultadoItem(BaseModel):
    conta_receber_id: int
    documento: Optional[str] = None
    valor_baixado: float = 0
    saldo_restante: float = 0
    status: str
    status_label: str


class TransferenciaParceiroBaixaLoteResponse(BaseModel):
    sucesso: bool
    modo_baixa: str
    total_baixado: float
    total_itens: int
    items: List[TransferenciaParceiroBaixaLoteResultadoItem] = Field(
        default_factory=list
    )
    recebimentos_criados: List[int] = Field(default_factory=list)
    pagamentos_criados: List[int] = Field(default_factory=list)
    contas_pagar_criadas: List[int] = Field(default_factory=list)
    movimentacoes_estoque: List[int] = Field(default_factory=list)
