"""Contratos HTTP dos orcamentos de empresas do grupo."""

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class OrcamentoGrupoConfiguracaoUpdate(BaseModel):
    percentual_minimo: Decimal = Field(ge=0, le=500)
    percentual_maximo: Decimal = Field(ge=0, le=500)
    quantidade_empresas: int = Field(ge=1, le=5)
    validade_dias: int = Field(ge=1, le=365)
    observacoes_padrao: Optional[str] = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validar_faixa(self):
        if self.percentual_maximo < self.percentual_minimo:
            raise ValueError("O percentual maximo deve ser maior ou igual ao minimo")
        return self


class OrcamentoGrupoEmpresaCreate(BaseModel):
    cliente_id: int = Field(gt=0)
    fixada_padrao: bool = False
    observacoes: Optional[str] = Field(default=None, max_length=1000)


class OrcamentoGrupoEmpresaUpdate(BaseModel):
    ativo: Optional[bool] = None
    fixada_padrao: Optional[bool] = None
    observacoes: Optional[str] = Field(default=None, max_length=1000)


class OrcamentoGrupoItemCreate(BaseModel):
    descricao: str = Field(min_length=1, max_length=500)
    quantidade: Decimal = Field(gt=0, le=999999)
    unidade: Optional[str] = Field(default=None, max_length=30)
    preco_unitario_base: Decimal = Field(ge=0, le=9999999999)

    @field_validator("descricao")
    @classmethod
    def limpar_descricao(cls, value: str) -> str:
        return value.strip()


class OrcamentoGrupoEmpresaSelecionada(BaseModel):
    empresa_id: int = Field(gt=0)
    fixada: bool = False


class OrcamentoGrupoCreate(BaseModel):
    titulo: str = Field(default="Orcamento", min_length=1, max_length=255)
    destinatario: Optional[str] = Field(default=None, max_length=255)
    data_emissao: date = Field(default_factory=date.today)
    validade_dias: Optional[int] = Field(default=None, ge=1, le=365)
    observacoes: Optional[str] = Field(default=None, max_length=4000)
    itens: list[OrcamentoGrupoItemCreate] = Field(min_length=1, max_length=100)
    empresas: list[OrcamentoGrupoEmpresaSelecionada] = Field(min_length=1, max_length=5)

    @field_validator("titulo")
    @classmethod
    def limpar_titulo(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def validar_empresas_unicas(self):
        ids = [item.empresa_id for item in self.empresas]
        if len(ids) != len(set(ids)):
            raise ValueError("Selecione empresas diferentes para cada orcamento")
        return self
