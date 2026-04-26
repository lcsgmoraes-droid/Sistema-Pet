"""Schemas do fluxo de taxi dog do Banho & Tosa."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class BanhoTosaTaxiDogCreate(BaseModel):
    agendamento_id: Optional[int] = Field(default=None, gt=0)
    cliente_id: Optional[int] = Field(default=None, gt=0)
    pet_id: Optional[int] = Field(default=None, gt=0)
    tipo: str = Field(default="ida_volta", min_length=1, max_length=20)
    status: str = Field(default="agendado", min_length=1, max_length=40)
    motorista_id: Optional[int] = Field(default=None, gt=0)
    endereco_origem: Optional[str] = None
    endereco_destino: Optional[str] = None
    janela_inicio: Optional[datetime] = None
    janela_fim: Optional[datetime] = None
    km_estimado: Decimal = Field(default=Decimal("0"), ge=0)
    km_real: Decimal = Field(default=Decimal("0"), ge=0)
    valor_cobrado: Decimal = Field(default=Decimal("0"), ge=0)
    custo_estimado: Decimal = Field(default=Decimal("0"), ge=0)
    custo_real: Decimal = Field(default=Decimal("0"), ge=0)
    rota_entrega_id: Optional[int] = None


class BanhoTosaTaxiDogUpdate(BaseModel):
    tipo: Optional[str] = Field(default=None, min_length=1, max_length=20)
    status: Optional[str] = Field(default=None, min_length=1, max_length=40)
    motorista_id: Optional[int] = Field(default=None, gt=0)
    endereco_origem: Optional[str] = None
    endereco_destino: Optional[str] = None
    janela_inicio: Optional[datetime] = None
    janela_fim: Optional[datetime] = None
    km_estimado: Optional[Decimal] = Field(default=None, ge=0)
    km_real: Optional[Decimal] = Field(default=None, ge=0)
    valor_cobrado: Optional[Decimal] = Field(default=None, ge=0)
    custo_estimado: Optional[Decimal] = Field(default=None, ge=0)
    custo_real: Optional[Decimal] = Field(default=None, ge=0)
    rota_entrega_id: Optional[int] = None


class BanhoTosaTaxiDogStatusUpdate(BaseModel):
    status: str = Field(..., min_length=1, max_length=40)


class BanhoTosaTaxiDogResponse(BaseModel):
    id: int
    cliente_id: int
    cliente_nome: Optional[str] = None
    pet_id: int
    pet_nome: Optional[str] = None
    agendamento_id: Optional[int] = None
    agendamento_inicio: Optional[datetime] = None
    tipo: str
    status: str
    motorista_id: Optional[int] = None
    motorista_nome: Optional[str] = None
    endereco_origem: Optional[str] = None
    endereco_destino: Optional[str] = None
    janela_inicio: Optional[datetime] = None
    janela_fim: Optional[datetime] = None
    km_estimado: Decimal
    km_real: Decimal
    valor_cobrado: Decimal
    custo_estimado: Decimal
    custo_real: Decimal
    rota_entrega_id: Optional[int] = None
    data_referencia: Optional[date] = None
