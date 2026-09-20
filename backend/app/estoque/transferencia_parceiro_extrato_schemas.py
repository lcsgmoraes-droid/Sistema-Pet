"""Schemas do extrato financeiro de transferencias para parceiros."""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class TransferenciaParceiroExtratoProdutoItem(BaseModel):
    produto_id: Optional[int] = None
    produto_nome: str
    codigo: Optional[str] = None
    quantidade: float = 0
    custo_unitario: float = 0
    valor_total: float = 0


class TransferenciaParceiroExtratoItem(BaseModel):
    id: str
    tipo: str
    tipo_label: str
    data: date
    registrado_em: Optional[datetime] = None
    conta_receber_id: int
    documento: Optional[str] = None
    descricao: str
    debito: float = 0
    credito: float = 0
    saldo: float = 0
    saldo_documento: float = 0
    conta_status: str
    conta_status_label: str
    data_vencimento: Optional[date] = None
    forma_pagamento_nome: Optional[str] = None
    observacoes: Optional[str] = None
    itens: List[TransferenciaParceiroExtratoProdutoItem] = Field(default_factory=list)


class TransferenciaParceiroExtratoTotais(BaseModel):
    saldo_anterior: float = 0
    total_debitos: float = 0
    total_creditos: float = 0
    saldo_final: float = 0
    total_lancamentos: int = 0
    total_documentos: int = 0
    documentos_em_aberto: int = 0


class TransferenciaParceiroExtratoResponse(BaseModel):
    parceiro_id: int
    parceiro_nome: Optional[str] = None
    items: List[TransferenciaParceiroExtratoItem] = Field(default_factory=list)
    totais: TransferenciaParceiroExtratoTotais
