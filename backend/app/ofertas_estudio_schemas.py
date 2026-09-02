"""Contratos HTTP do Estudio de Ofertas."""

import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


Periodicidade = Literal["avulsa", "diaria", "semanal", "mensal"]
TipoArte = Literal["jornal", "individual", "produto"]
FormatoArte = Literal["quadrado", "retrato", "story", "a4"]


class OfertaProdutoSnapshotInput(BaseModel):
    produto_id: int = Field(gt=0)
    preco_arte: float = Field(gt=0, allow_inf_nan=False)
    imagem_url: str | None = Field(default=None, max_length=2048)
    mostrar_validade: bool = False
    lote_id: int | None = Field(default=None, gt=0)


class OfertaPublicacaoCreate(BaseModel):
    titulo: str = Field(min_length=2, max_length=160)
    periodicidade: Periodicidade = "avulsa"
    tipo_arte: TipoArte = "jornal"
    formato: FormatoArte = "quadrado"
    inicio_em: datetime
    fim_em: datetime
    expira_em: datetime
    produtos: list[OfertaProdutoSnapshotInput] = Field(min_length=1, max_length=60)
    configuracao: dict[str, Any] = Field(default_factory=dict)

    @field_validator("titulo")
    @classmethod
    def limpar_titulo(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("inicio_em", "fim_em", "expira_em")
    @classmethod
    def exigir_fuso_horario(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Informe data e hora com fuso horario.")
        return value

    @field_validator("configuracao")
    @classmethod
    def limitar_configuracao(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(json.dumps(value, ensure_ascii=False)) > 16_384:
            raise ValueError("A configuracao da arte excede o limite permitido.")
        return value


class OfertaDesativacaoResponse(BaseModel):
    id: int
    status: str
    desativada_em: datetime
