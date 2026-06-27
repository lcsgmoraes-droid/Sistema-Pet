"""Schemas das pendencias de compras."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CriarPendenciaNotaPayload(BaseModel):
    prazo_previsto: Optional[datetime] = None
    observacao: Optional[str] = None
    email_destinatario: Optional[str] = None
    email_assunto: Optional[str] = None
    email_mensagem: Optional[str] = None


class AtualizarPendenciaPayload(BaseModel):
    status: Optional[str] = None
    prazo_previsto: Optional[datetime] = None
    observacao: Optional[str] = None
    resolucao_observacao: Optional[str] = None


class RegistrarEmailPayload(BaseModel):
    email_destinatario: Optional[str] = None
    email_assunto: Optional[str] = None
    email_mensagem: str = Field(min_length=3)
    observacao: Optional[str] = None
