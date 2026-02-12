from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class ConfiguracaoCustoMotoBase(BaseModel):
    preco_combustivel: Decimal
    km_por_litro: Decimal

    km_troca_oleo: Optional[int] = None
    custo_troca_oleo: Optional[Decimal] = None

    km_troca_pneu_dianteiro: Optional[int] = None
    custo_pneu_dianteiro: Optional[Decimal] = None

    km_troca_pneu_traseiro: Optional[int] = None
    custo_pneu_traseiro: Optional[Decimal] = None

    km_troca_kit_traseiro: Optional[int] = None
    custo_kit_traseiro: Optional[Decimal] = None

    km_manutencao_geral: Optional[int] = None
    custo_manutencao_geral: Optional[Decimal] = None

    seguro_mensal: Optional[Decimal] = None
    licenciamento_mensal: Optional[Decimal] = None
    ipva_mensal: Optional[Decimal] = None
    outros_custos_mensais: Optional[Decimal] = None

    km_medio_mensal: Optional[Decimal] = None


class ConfiguracaoCustoMotoUpdate(ConfiguracaoCustoMotoBase):
    pass


class ConfiguracaoCustoMotoResponse(ConfiguracaoCustoMotoBase):
    id: int

    class Config:
        from_attributes = True
