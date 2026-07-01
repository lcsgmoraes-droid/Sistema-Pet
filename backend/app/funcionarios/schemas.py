"""Schemas das rotas de funcionarios/RH."""

from datetime import date
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class FuncionarioCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    cpf: Optional[str] = None
    cargo_id: int
    ativo: bool = True
    data_fechamento_comissao: Optional[int] = Field(
        None, ge=1, le=31, description="Dia do mês para fechamento de comissão (1-31)"
    )
    salario_base_override: Optional[Decimal] = Field(None, ge=0)
    liquido_combinado: Optional[Decimal] = Field(None, ge=0)
    complemento_modo: str = Field(
        default="automatico", pattern="^(automatico|manual|nenhum)$"
    )
    complemento_fixo_valor: Decimal = Field(default=Decimal("0.00"), ge=0)
    remuneracao_observacoes: Optional[str] = None
    app_access_profiles: Optional[List[str]] = None

    model_config = {"from_attributes": True}


class FuncionarioUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    cpf: Optional[str] = None
    cargo_id: Optional[int] = None
    ativo: Optional[bool] = None
    data_fechamento_comissao: Optional[int] = Field(
        None, ge=1, le=31, description="Dia do mês para fechamento de comissão (1-31)"
    )
    salario_base_override: Optional[Decimal] = Field(None, ge=0)
    liquido_combinado: Optional[Decimal] = Field(None, ge=0)
    complemento_modo: Optional[str] = Field(
        None, pattern="^(automatico|manual|nenhum)$"
    )
    complemento_fixo_valor: Optional[Decimal] = Field(None, ge=0)
    remuneracao_observacoes: Optional[str] = None
    app_access_profiles: Optional[List[str]] = None

    model_config = {"from_attributes": True}


class CargoSimples(BaseModel):
    id: int
    nome: str
    salario_base: Decimal
    regime_remuneracao: str = "clt"

    model_config = {"from_attributes": True}


class RemuneracaoResponse(BaseModel):
    regime_remuneracao: str
    usa_encargos: bool
    salario_base: Decimal
    inss_funcionario: Decimal
    desconto_transporte: Decimal
    outros_descontos: Decimal
    descontos_funcionario_total: Decimal
    liquido_holerite: Decimal
    liquido_combinado: Decimal
    complemento_modo: str
    complemento_interno: Decimal
    inss_patronal: Decimal
    fgts_empresa: Decimal
    encargos_empresa_total: Decimal
    provisao_ferias: Decimal
    provisao_terco_ferias: Decimal
    provisao_13: Decimal
    provisoes_total: Decimal
    custo_total_empresa: Decimal

    model_config = {"from_attributes": True}


class FuncionarioResponse(BaseModel):
    id: int
    codigo: Optional[str]
    nome: str
    email: Optional[str]
    telefone: Optional[str]
    cpf: Optional[str]
    cargo: Optional[CargoSimples]
    ativo: bool
    data_fechamento_comissao: Optional[int]
    salario_base_override: Optional[Decimal]
    liquido_combinado: Optional[Decimal]
    complemento_modo: str
    complemento_fixo_valor: Decimal
    remuneracao_observacoes: Optional[str]
    app_access_profiles: List[str] = Field(default_factory=list)
    remuneracao: Optional[RemuneracaoResponse] = None

    model_config = {"from_attributes": True}


class ConcederFeriasRequest(BaseModel):
    mes: int = Field(..., ge=1, le=12, description="Mês de competência (1-12)")
    ano: int = Field(..., ge=2020, le=2030, description="Ano de competência")
    dias_ferias: int = Field(30, ge=1, le=30, description="Dias de férias")
    data_pagamento: Optional[date] = Field(
        None, description="Data de vencimento da conta a pagar"
    )

    model_config = {"from_attributes": True}


class PagarDecimoTerceiroRequest(BaseModel):
    mes: int = Field(..., ge=1, le=12, description="Mês de competência (1-12)")
    ano: int = Field(..., ge=2020, le=2030, description="Ano de competência")
    percentual: float = Field(
        ...,
        ge=0,
        le=100,
        description="Percentual do 13º (50 para 1ª parcela, 100 para total)",
    )
    descricao_parcela: Optional[str] = Field(
        None, description="Descrição da parcela (ex: '1ª Parcela')"
    )
    data_pagamento: Optional[date] = Field(
        None, description="Data de vencimento da conta a pagar"
    )

    model_config = {"from_attributes": True}


class ProvisoesResponse(BaseModel):
    funcionario_id: int
    funcionario_nome: str
    cargo_nome: str
    salario_base: Decimal
    provisao_ferias: Decimal
    provisao_terco_ferias: Decimal
    provisao_13_salario: Decimal
    total_provisoes: Decimal

    model_config = {"from_attributes": True}
