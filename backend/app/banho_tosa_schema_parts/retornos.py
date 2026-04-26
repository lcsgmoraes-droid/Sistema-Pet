"""Schemas da central de retornos do Banho & Tosa."""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class BanhoTosaRetornoSugestaoResponse(BaseModel):
    id: str
    tipo: str
    prioridade: str
    cliente_id: int
    cliente_nome: Optional[str] = None
    pet_id: Optional[int] = None
    pet_nome: Optional[str] = None
    servico_id: Optional[int] = None
    servico_nome: Optional[str] = None
    pacote_credito_id: Optional[int] = None
    pacote_nome: Optional[str] = None
    recorrencia_id: Optional[int] = None
    referencia_id: Optional[int] = None
    data_referencia: Optional[date] = None
    dias_para_acao: Optional[int] = None
    titulo: str
    mensagem: str
    acao_sugerida: str
    canal_sugerido: str = "app"
    notificavel_app: bool = True


class BanhoTosaRetornosResponse(BaseModel):
    total: int
    itens: List[BanhoTosaRetornoSugestaoResponse] = Field(default_factory=list)


class BanhoTosaRecorrenciaAvancarInput(BaseModel):
    data_base: Optional[date] = None
    observacoes: Optional[str] = None


class BanhoTosaNotificarRetornosInput(BaseModel):
    tipos: List[str] = Field(default_factory=list)
    dias_antecedencia: int = Field(default=7, ge=-365, le=365)
    limit: int = Field(default=100, ge=1, le=300)
    canal: str = Field(default="app", max_length=30)
    template_id: Optional[int] = Field(default=None, gt=0)


class BanhoTosaNotificarRetornosResponse(BaseModel):
    processados: int
    enfileirados: int
    ignorados: int
    sem_destino: int = 0


class BanhoTosaRetornoTemplateCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=120)
    tipo_retorno: str = Field(default="todos", max_length=40)
    canal: str = Field(default="app", max_length=30)
    assunto: str = Field(..., min_length=1, max_length=180)
    mensagem: str = Field(..., min_length=1)
    ativo: bool = True


class BanhoTosaRetornoTemplateUpdate(BaseModel):
    nome: Optional[str] = Field(default=None, min_length=1, max_length=120)
    tipo_retorno: Optional[str] = Field(default=None, max_length=40)
    canal: Optional[str] = Field(default=None, max_length=30)
    assunto: Optional[str] = Field(default=None, min_length=1, max_length=180)
    mensagem: Optional[str] = Field(default=None, min_length=1)
    ativo: Optional[bool] = None


class BanhoTosaRetornoTemplateResponse(BaseModel):
    id: int
    nome: str
    tipo_retorno: str
    canal: str
    assunto: str
    mensagem: str
    ativo: bool
