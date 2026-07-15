"""Contratos da API de imobilizado."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator


CategoriaBem = Literal[
    "equipamentos",
    "moveis_utensilios",
    "informatica",
    "veiculos",
    "instalacoes",
    "maquinas",
    "outros",
]
StatusBem = Literal["ativo", "manutencao", "baixado", "vendido"]


class BemImobilizadoBase(BaseModel):
    nome: str = Field(..., min_length=2, max_length=180)
    codigo_patrimonial: str | None = Field(None, max_length=60)
    categoria: CategoriaBem = "outros"
    descricao: str | None = None
    localizacao: str | None = Field(None, max_length=150)
    fornecedor: str | None = Field(None, max_length=180)
    documento: str | None = Field(None, max_length=100)
    documento_url: str | None = Field(None, max_length=500)
    quantidade: int = Field(1, ge=1)
    data_aquisicao: date
    valor_aquisicao: Decimal = Field(..., ge=0)
    valor_residual: Decimal = Field(0, ge=0)
    valor_mercado: Decimal | None = Field(None, ge=0)
    depreciar: bool = True
    vida_util_meses: int | None = Field(60, ge=1, le=1200)
    status: StatusBem = "ativo"
    data_baixa: date | None = None
    motivo_baixa: str | None = None
    observacoes: str | None = None

    @model_validator(mode="after")
    def validar_valores_e_baixa(self):
        if self.valor_residual > self.valor_aquisicao:
            raise ValueError("O valor residual nao pode superar o valor de aquisicao.")
        if self.status in {"baixado", "vendido"} and not self.data_baixa:
            raise ValueError("Informe a data da baixa ou venda do bem.")
        if self.data_baixa and self.data_baixa < self.data_aquisicao:
            raise ValueError("A data da baixa nao pode ser anterior a aquisicao.")
        if self.depreciar and not self.vida_util_meses:
            raise ValueError("Informe a vida util para calcular a depreciacao.")
        return self


class BemImobilizadoCreate(BemImobilizadoBase):
    pass


class BemImobilizadoUpdate(BemImobilizadoBase):
    pass


class BemImobilizadoResponse(BemImobilizadoBase):
    id: int
    meses_depreciados: int
    depreciacao_acumulada: Decimal
    valor_contabil: Decimal
    created_at: datetime
    updated_at: datetime


class ResumoImobilizado(BaseModel):
    total_registros: int
    total_itens: int
    valor_aquisicao: Decimal
    depreciacao_acumulada: Decimal
    valor_contabil: Decimal
    valor_mercado_informado: Decimal
    registros_sem_valor_mercado: int


class ListaImobilizadoResponse(BaseModel):
    items: list[BemImobilizadoResponse]
    resumo: ResumoImobilizado
