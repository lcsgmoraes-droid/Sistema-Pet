from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.estoque.transferencia_parceiro_entrada_schemas import (
    TransferenciaParceiroEntradaHistoricoItem as TransferenciaParceiroEntradaHistoricoItem,
    TransferenciaParceiroEntradaHistoricoResponse as TransferenciaParceiroEntradaHistoricoResponse,
    TransferenciaParceiroEntradaHistoricoTotais as TransferenciaParceiroEntradaHistoricoTotais,
    TransferenciaParceiroEntradaItemRequest as TransferenciaParceiroEntradaItemRequest,
    TransferenciaParceiroEntradaRequest as TransferenciaParceiroEntradaRequest,
    TransferenciaParceiroEntradaResponse as TransferenciaParceiroEntradaResponse,
)


class TransferenciaParceiroItemRequest(BaseModel):
    """Item da transferencia de estoque para parceiro."""

    produto_id: int
    quantidade: float = Field(gt=0)
    custo_unitario: Optional[float] = Field(default=None, ge=0)
    valor_total: Optional[float] = Field(default=None, ge=0)


class TransferenciaParceiroRequest(BaseModel):
    """Transferencia de estoque para parceiro com ressarcimento pelo custo."""

    parceiro_id: int
    data_vencimento: Optional[date] = None
    documento: Optional[str] = None
    observacao: Optional[str] = None
    itens: List[TransferenciaParceiroItemRequest] = Field(
        default_factory=list, min_items=1
    )


class TransferenciaParceiroEnviarEmailRequest(BaseModel):
    email: Optional[str] = None
    assunto: Optional[str] = None
    mensagem: Optional[str] = None
    mostrar_codigo: bool = True
    mostrar_descricao: bool = True
    mostrar_quantidade: bool = True
    mostrar_custo_unitario: bool = True
    mostrar_total_item: bool = True
    mostrar_totais: bool = True


class TransferenciaParceiroCompensacaoContaRequest(BaseModel):
    conta_pagar_id: int
    valor_compensado: float = Field(gt=0)


class TransferenciaParceiroRecebimentoRequest(BaseModel):
    valor_recebido: float = Field(gt=0)
    data_recebimento: date = Field(default_factory=date.today)
    modo_baixa: str = Field(default="recebimento")
    forma_pagamento_id: Optional[int] = None
    devolver_estoque: bool = False
    compensacoes: List[TransferenciaParceiroCompensacaoContaRequest] = Field(
        default_factory=list
    )
    observacao: Optional[str] = None


class TransferenciaParceiroHistoricoMovItem(BaseModel):
    produto_id: int
    produto_nome: str
    codigo: Optional[str] = None
    codigo_barras: Optional[str] = None
    estoque_atual: float = 0
    quantidade: float = 0
    custo_unitario: float = 0
    valor_total: float = 0
    created_at: Optional[datetime] = None


class TransferenciaParceiroContaPagarCompensacaoItem(BaseModel):
    conta_pagar_id: int
    descricao: str
    documento: Optional[str] = None
    canal: Optional[str] = None
    origem_acerto: str = "financeiro"
    origem_label: str = "Financeiro"
    data_emissao: Optional[date] = None
    data_vencimento: Optional[date] = None
    status: str
    status_label: str
    valor_original: float = 0
    valor_pago: float = 0
    saldo_aberto: float = 0
    observacoes: Optional[str] = None


class TransferenciaParceiroContaPagarCompensacaoResponse(BaseModel):
    items: List[TransferenciaParceiroContaPagarCompensacaoItem] = Field(
        default_factory=list
    )
    total: int = 0
    total_disponivel: float = 0


class TransferenciaParceiroPdfConsolidadoRequest(BaseModel):
    conta_receber_ids: List[int] = Field(default_factory=list)
    parceiro_id: Optional[int] = None
    status_filtro: Optional[str] = None
    busca: Optional[str] = None
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    mostrar_codigo: bool = True
    mostrar_descricao: bool = True
    mostrar_quantidade: bool = True
    mostrar_custo_unitario: bool = True
    mostrar_total_item: bool = True
    mostrar_totais: bool = True


class TransferenciaParceiroHistoricoItem(BaseModel):
    conta_receber_id: int
    documento: Optional[str] = None
    parceiro_id: Optional[int] = None
    parceiro_nome: str
    parceiro_codigo: Optional[str] = None
    parceiro_email: Optional[str] = None
    data_emissao: Optional[date] = None
    data_vencimento: Optional[date] = None
    data_recebimento: Optional[date] = None
    status: str
    status_label: str
    valor_original: float = 0
    valor_recebido: float = 0
    saldo_aberto: float = 0
    modo_baixa: Optional[str] = None
    modo_baixa_label: Optional[str] = None
    forma_pagamento_id: Optional[int] = None
    forma_pagamento_nome: Optional[str] = None
    observacoes: Optional[str] = None
    itens: List[TransferenciaParceiroHistoricoMovItem] = Field(default_factory=list)


class TransferenciaParceiroHistoricoTotais(BaseModel):
    total_registros: int = 0
    valor_total: float = 0
    valor_recebido: float = 0
    saldo_aberto: float = 0
    pendentes: int = 0
    recebidas: int = 0
    vencidas: int = 0


class TransferenciaParceiroHistoricoResponse(BaseModel):
    items: List[TransferenciaParceiroHistoricoItem] = Field(default_factory=list)
    totais: TransferenciaParceiroHistoricoTotais
    total: int
    page: int
    page_size: int
    pages: int
