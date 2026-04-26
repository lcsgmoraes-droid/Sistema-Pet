"""Schemas de fechamento comercial do Banho & Tosa."""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


class BanhoTosaVendaAtendimentoResponse(BaseModel):
    atendimento_id: int
    venda_id: int
    numero_venda: str
    status_venda: str
    total: Decimal
    pdv_url: str
    ja_existia: bool = False
    mensagem: Optional[str] = None


class BanhoTosaFechamentoSyncResponse(BaseModel):
    atendimento_id: int
    venda_id: Optional[int] = None
    conta_receber_id: Optional[int] = None
    venda_status: Optional[str] = None
    status_pagamento: str
    total: Decimal
    total_pago: Decimal
    valor_restante: Decimal
    contas_receber_total: int = 0
    contas_receber_pendentes: int = 0
    contas_receber_recebidas: int = 0
    sincronizado: bool = False
    alertas: List[str] = Field(default_factory=list)


class BanhoTosaFechamentoPendenciaItem(BanhoTosaFechamentoSyncResponse):
    cliente_id: int
    cliente_nome: Optional[str] = None
    pet_id: int
    pet_nome: Optional[str] = None
    status_atendimento: str
    checkin_em: Optional[datetime] = None
    fim_em: Optional[datetime] = None
    entregue_em: Optional[datetime] = None
    venda_numero: Optional[str] = None
    pdv_url: Optional[str] = None


class BanhoTosaFechamentoPendenciasResponse(BaseModel):
    total: int
    itens: List[BanhoTosaFechamentoPendenciaItem] = Field(default_factory=list)


class BanhoTosaFechamentoSincronizacaoLoteResponse(BaseModel):
    total_processados: int
    sincronizados: int
    sem_venda: int
    pendentes_restantes: int


class BanhoTosaCancelamentoInput(BaseModel):
    motivo: str = Field(..., min_length=3, max_length=500)


class BanhoTosaCancelamentoResponse(BaseModel):
    atendimento_id: int
    status_atendimento: str
    agendamento_id: Optional[int] = None
    status_agendamento: Optional[str] = None
    venda_ids: List[int] = Field(default_factory=list)
    vendas_canceladas: int = 0
    vendas_ja_canceladas: int = 0
    pacote_estornado: bool = False
    mensagem: str
