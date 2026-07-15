"""Contratos da API de avaliacao da empresa."""

from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class ValorEmpresaConfiguracaoPayload(BaseModel):
    periodo_dias: int = Field(60, ge=30, le=730)
    canais: str = Field("loja_fisica", max_length=300)
    fornecedor_ids_excluidos: list[int] = Field(default_factory=list)
    folha_mensal_override: Decimal | None = Field(None, ge=0)
    despesas_fixas_mensais_override: Decimal | None = Field(None, ge=0)
    margem_contribuicao_override: Decimal | None = Field(None, ge=0, le=100)
    imobilizado_override: Decimal | None = Field(None, ge=0)
    outros_ativos: Decimal = Field(0, ge=0)
    incluir_dividas: bool = False
    percentual_dividas_assumidas: Decimal = Field(100, ge=0, le=100)
    desconto_estoque_conservador: Decimal = Field(45, ge=0, le=100)
    desconto_estoque_provavel: Decimal = Field(25, ge=0, le=100)
    desconto_estoque_otimista: Decimal = Field(10, ge=0, le=100)
    multiplo_lucro_conservador: Decimal = Field(18, ge=0, le=120)
    multiplo_lucro_provavel: Decimal = Field(24, ge=0, le=120)
    multiplo_lucro_otimista: Decimal = Field(30, ge=0, le=120)
    dias_estoque_lento: int = Field(365, ge=30, le=3650)
    observacoes: str | None = Field(None, max_length=4000)

    @field_validator("fornecedor_ids_excluidos")
    @classmethod
    def normalizar_fornecedores(cls, valor: list[int]) -> list[int]:
        return list(dict.fromkeys(item for item in valor if item > 0))


class SimulacaoValorEmpresaPayload(BaseModel):
    faturamento_mensal: Decimal = Field(..., ge=0)


class ValorEmpresaConfiguracaoResponse(ValorEmpresaConfiguracaoPayload):
    id: int | None = None
    fornecedores_excluidos: list[dict] = Field(default_factory=list)


class ValorEmpresaResponse(BaseModel):
    configuracao: ValorEmpresaConfiguracaoResponse
    periodo: dict
    operacao: dict
    ativos: dict
    dividas: dict
    cenarios: list[dict]
    simulacao: dict
    confianca: dict
    fontes: list[dict]
