"""Schemas de pacotes, creditos e recorrencias do Banho & Tosa."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, Field


class BanhoTosaPacoteServicoInput(BaseModel):
    servico_id: int = Field(..., gt=0)
    quantidade_creditos: Decimal = Field(..., gt=0)


class BanhoTosaPacoteCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=160)
    descricao: Optional[str] = None
    servico_id: Optional[int] = Field(default=None, gt=0)
    quantidade_creditos: Decimal = Field(default=Decimal("1"), gt=0)
    validade_dias: int = Field(default=30, ge=1, le=3650)
    preco: Decimal = Field(default=Decimal("0"), ge=0)
    ativo: bool = True
    servicos: Optional[List[BanhoTosaPacoteServicoInput]] = None


class BanhoTosaPacoteUpdate(BaseModel):
    nome: Optional[str] = Field(default=None, min_length=1, max_length=160)
    descricao: Optional[str] = None
    servico_id: Optional[int] = Field(default=None, gt=0)
    quantidade_creditos: Optional[Decimal] = Field(default=None, gt=0)
    validade_dias: Optional[int] = Field(default=None, ge=1, le=3650)
    preco: Optional[Decimal] = Field(default=None, ge=0)
    ativo: Optional[bool] = None
    servicos: Optional[List[BanhoTosaPacoteServicoInput]] = None


class BanhoTosaPacoteResponse(BaseModel):
    id: int
    nome: str
    descricao: Optional[str] = None
    servico_id: Optional[int] = None
    servico_nome: Optional[str] = None
    quantidade_creditos: Decimal
    validade_dias: int
    preco: Decimal
    ativo: bool
    servicos: List[dict] = Field(default_factory=list)


class BanhoTosaPacoteCreditoCreate(BaseModel):
    pacote_id: int = Field(..., gt=0)
    cliente_id: int = Field(..., gt=0)
    pet_id: int = Field(..., gt=0)
    venda_id: Optional[int] = Field(default=None, gt=0)
    data_inicio: Optional[date] = None
    data_validade: Optional[date] = None
    observacoes: Optional[str] = None


class BanhoTosaPacoteProrrogacaoInput(BaseModel):
    data_validade: date
    motivo: str = Field(..., min_length=3, max_length=1000)


class BanhoTosaPacoteEncerramentoInput(BaseModel):
    motivo: str = Field(..., min_length=3, max_length=1000)


class BanhoTosaPacoteCreditoResponse(BaseModel):
    id: int
    pacote_id: int
    pacote_nome: str
    servico_id: Optional[int] = None
    servico_nome: Optional[str] = None
    cliente_id: int
    cliente_nome: Optional[str] = None
    pet_id: Optional[int] = None
    pet_nome: Optional[str] = None
    venda_id: Optional[int] = None
    status: str
    creditos_total: Decimal
    creditos_usados: Decimal
    creditos_cancelados: Decimal
    creditos_reservados: Decimal = Decimal("0")
    saldo_creditos: Decimal
    saldo_total_creditos: Decimal = Decimal("0")
    servicos: List[dict] = Field(default_factory=list)
    status_pagamento: str = "sem_venda"
    valor_pacote: Decimal = Decimal("0")
    valor_pago: Decimal = Decimal("0")
    valor_restante: Decimal = Decimal("0")
    venda_numero: Optional[str] = None
    pdv_url: Optional[str] = None
    data_inicio: date
    data_validade: date
    vencido: bool
    disponivel: bool
    observacoes: Optional[str] = None


class BanhoTosaPacoteMovimentoResponse(BaseModel):
    id: int
    credito_id: int
    atendimento_id: Optional[int] = None
    agendamento_id: Optional[int] = None
    servico_id: Optional[int] = None
    movimento_origem_id: Optional[int] = None
    tipo: str
    quantidade: Decimal
    saldo_apos: Decimal
    observacoes: Optional[str] = None
    created_at: Optional[datetime] = None
    created_by: Optional[int] = None


class BanhoTosaPacoteConsumoInput(BaseModel):
    atendimento_id: int = Field(..., gt=0)
    quantidade: Decimal = Field(default=Decimal("1"), gt=0)
    observacoes: Optional[str] = None


class BanhoTosaPacoteEstornoInput(BaseModel):
    atendimento_id: Optional[int] = Field(default=None, gt=0)
    movimento_id: Optional[int] = Field(default=None, gt=0)
    observacoes: Optional[str] = None


class BanhoTosaPacoteConsumoResponse(BaseModel):
    credito: BanhoTosaPacoteCreditoResponse
    movimento: BanhoTosaPacoteMovimentoResponse
    ja_existia: bool = False


class BanhoTosaRecorrenciaCreate(BaseModel):
    cliente_id: int = Field(..., gt=0)
    pet_id: int = Field(..., gt=0)
    servico_id: Optional[int] = Field(default=None, gt=0)
    pacote_credito_id: Optional[int] = Field(default=None, gt=0)
    intervalo_dias: int = Field(default=30, ge=1, le=365)
    proxima_execucao: date
    canal_lembrete: str = Field(default="whatsapp", max_length=30)
    observacoes: Optional[str] = None


class BanhoTosaRecorrenciaUpdate(BaseModel):
    servico_id: Optional[int] = Field(default=None, gt=0)
    pacote_credito_id: Optional[int] = Field(default=None, gt=0)
    intervalo_dias: Optional[int] = Field(default=None, ge=1, le=365)
    proxima_execucao: Optional[date] = None
    canal_lembrete: Optional[str] = Field(default=None, max_length=30)
    ativo: Optional[bool] = None
    observacoes: Optional[str] = None


class BanhoTosaRecorrenciaResponse(BaseModel):
    id: int
    cliente_id: int
    cliente_nome: Optional[str] = None
    pet_id: int
    pet_nome: Optional[str] = None
    servico_id: Optional[int] = None
    servico_nome: Optional[str] = None
    pacote_credito_id: Optional[int] = None
    intervalo_dias: int
    proxima_execucao: date
    canal_lembrete: str
    ativo: bool
    observacoes: Optional[str] = None
