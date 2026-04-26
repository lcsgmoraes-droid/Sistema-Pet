"""Schemas de cadastros e parametrizacoes do Banho & Tosa."""

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class BanhoTosaConfiguracaoUpdate(BaseModel):
    horario_inicio: Optional[str] = Field(default=None, max_length=5)
    horario_fim: Optional[str] = Field(default=None, max_length=5)
    dias_funcionamento: Optional[list[str]] = None
    intervalo_slot_minutos: Optional[int] = Field(default=None, ge=5, le=240)
    politica_atraso: Optional[str] = None
    tolerancia_encaixe_minutos: Optional[int] = Field(default=None, ge=0, le=240)
    custo_litro_agua: Optional[Decimal] = Field(default=None, ge=0)
    vazao_chuveiro_litros_min: Optional[Decimal] = Field(default=None, ge=0)
    custo_kwh: Optional[Decimal] = Field(default=None, ge=0)
    custo_toalha_padrao: Optional[Decimal] = Field(default=None, ge=0)
    custo_higienizacao_padrao: Optional[Decimal] = Field(default=None, ge=0)
    percentual_taxas_padrao: Optional[Decimal] = Field(default=None, ge=0)
    custo_rateio_operacional_padrao: Optional[Decimal] = Field(default=None, ge=0)
    horas_produtivas_mes_padrao: Optional[Decimal] = Field(default=None, ge=1)
    dre_subcategoria_receita_id: Optional[int] = None
    dre_subcategoria_custo_id: Optional[int] = None
    ativo: Optional[bool] = None


class BanhoTosaConfiguracaoResponse(BaseModel):
    id: int
    horario_inicio: str
    horario_fim: str
    dias_funcionamento: Optional[list[str]] = None
    intervalo_slot_minutos: int
    politica_atraso: Optional[str] = None
    tolerancia_encaixe_minutos: int
    custo_litro_agua: Decimal
    vazao_chuveiro_litros_min: Decimal
    custo_kwh: Decimal
    custo_toalha_padrao: Decimal
    custo_higienizacao_padrao: Decimal
    percentual_taxas_padrao: Decimal
    custo_rateio_operacional_padrao: Decimal
    horas_produtivas_mes_padrao: Decimal
    dre_subcategoria_receita_id: Optional[int] = None
    dre_subcategoria_custo_id: Optional[int] = None
    ativo: bool

    class Config:
        from_attributes = True


class BanhoTosaRecursoCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=120)
    tipo: str = Field(..., min_length=1, max_length=30)
    capacidade_simultanea: int = Field(default=1, ge=1, le=50)
    potencia_watts: Optional[Decimal] = Field(default=None, ge=0)
    custo_manutencao_hora: Decimal = Field(default=Decimal("0"), ge=0)
    ativo: bool = True


class BanhoTosaRecursoUpdate(BaseModel):
    nome: Optional[str] = Field(default=None, min_length=1, max_length=120)
    tipo: Optional[str] = Field(default=None, min_length=1, max_length=30)
    capacidade_simultanea: Optional[int] = Field(default=None, ge=1, le=50)
    potencia_watts: Optional[Decimal] = Field(default=None, ge=0)
    custo_manutencao_hora: Optional[Decimal] = Field(default=None, ge=0)
    ativo: Optional[bool] = None


class BanhoTosaRecursoResponse(BaseModel):
    id: int
    nome: str
    tipo: str
    capacidade_simultanea: int
    potencia_watts: Optional[Decimal] = None
    custo_manutencao_hora: Decimal
    ativo: bool

    class Config:
        from_attributes = True


class BanhoTosaPessoaApoioResponse(BaseModel):
    id: int
    nome: str
    tipo_cadastro: str


class BanhoTosaProdutoEstoqueResponse(BaseModel):
    id: int
    codigo: Optional[str] = None
    nome: str
    unidade: Optional[str] = None
    estoque_atual: Decimal
    preco_custo: Decimal


class BanhoTosaServicoCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=160)
    categoria: str = Field(default="banho", max_length=30)
    descricao: Optional[str] = None
    duracao_padrao_minutos: int = Field(default=60, ge=1, le=1440)
    requer_banho: bool = True
    requer_tosa: bool = False
    requer_secagem: bool = True
    permite_pacote: bool = True
    ativo: bool = True


class BanhoTosaServicoUpdate(BaseModel):
    nome: Optional[str] = Field(default=None, min_length=1, max_length=160)
    categoria: Optional[str] = Field(default=None, max_length=30)
    descricao: Optional[str] = None
    duracao_padrao_minutos: Optional[int] = Field(default=None, ge=1, le=1440)
    requer_banho: Optional[bool] = None
    requer_tosa: Optional[bool] = None
    requer_secagem: Optional[bool] = None
    permite_pacote: Optional[bool] = None
    ativo: Optional[bool] = None


class BanhoTosaServicoResponse(BaseModel):
    id: int
    nome: str
    categoria: str
    descricao: Optional[str] = None
    duracao_padrao_minutos: int
    requer_banho: bool
    requer_tosa: bool
    requer_secagem: bool
    permite_pacote: bool
    ativo: bool

    class Config:
        from_attributes = True


class BanhoTosaParametroPorteCreate(BaseModel):
    porte: str = Field(..., min_length=1, max_length=30)
    peso_min_kg: Optional[Decimal] = Field(default=None, ge=0)
    peso_max_kg: Optional[Decimal] = Field(default=None, ge=0)
    agua_padrao_litros: Decimal = Field(default=Decimal("0"), ge=0)
    energia_padrao_kwh: Decimal = Field(default=Decimal("0"), ge=0)
    tempo_banho_min: int = Field(default=0, ge=0)
    tempo_secagem_min: int = Field(default=0, ge=0)
    tempo_tosa_min: int = Field(default=0, ge=0)
    multiplicador_preco: Decimal = Field(default=Decimal("1"), ge=0)
    ativo: bool = True


class BanhoTosaParametroPorteUpdate(BaseModel):
    porte: Optional[str] = Field(default=None, min_length=1, max_length=30)
    peso_min_kg: Optional[Decimal] = Field(default=None, ge=0)
    peso_max_kg: Optional[Decimal] = Field(default=None, ge=0)
    agua_padrao_litros: Optional[Decimal] = Field(default=None, ge=0)
    energia_padrao_kwh: Optional[Decimal] = Field(default=None, ge=0)
    tempo_banho_min: Optional[int] = Field(default=None, ge=0)
    tempo_secagem_min: Optional[int] = Field(default=None, ge=0)
    tempo_tosa_min: Optional[int] = Field(default=None, ge=0)
    multiplicador_preco: Optional[Decimal] = Field(default=None, ge=0)
    ativo: Optional[bool] = None


class BanhoTosaParametroPorteResponse(BaseModel):
    id: int
    porte: str
    peso_min_kg: Optional[Decimal] = None
    peso_max_kg: Optional[Decimal] = None
    agua_padrao_litros: Decimal
    energia_padrao_kwh: Decimal
    tempo_banho_min: int
    tempo_secagem_min: int
    tempo_tosa_min: int
    multiplicador_preco: Decimal
    ativo: bool

    class Config:
        from_attributes = True
