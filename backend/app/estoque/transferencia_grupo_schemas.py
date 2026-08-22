from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class TransferenciaGrupoItemRequest(BaseModel):
    produto_id: int
    quantidade: float = Field(gt=0)
    custo_unitario: float | None = Field(default=None, ge=0)
    valor_total: float | None = Field(default=None, ge=0)


class TransferenciaGrupoPreviaRequest(BaseModel):
    grupo_id: int
    empresa_destino_id: UUID
    itens: list[TransferenciaGrupoItemRequest] = Field(min_length=1)


class TransferenciaGrupoExecutarRequest(TransferenciaGrupoPreviaRequest):
    chave_idempotencia: UUID
    data_vencimento: date | None = None
    documento: str | None = Field(default=None, max_length=100)
    observacao: str | None = Field(default=None, max_length=2000)


class TransferenciaGrupoMapeamentoItem(BaseModel):
    produto_origem_id: int
    produto_origem_nome: str
    produto_destino_id: int | None = None
    produto_destino_nome: str | None = None
    identificador: str | None = None
    status: Literal[
        "mapeado", "sem_codigo_barras", "nao_encontrado", "ambiguo", "invalido"
    ]
    mensagem: str
