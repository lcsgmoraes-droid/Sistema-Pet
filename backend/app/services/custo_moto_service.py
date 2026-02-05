from decimal import Decimal


def calcular_custo_moto(config, km: Decimal) -> Decimal:
    if not config or not km or km <= 0:
        return Decimal("0")

    # Combustível
    litros = km / config.km_por_litro
    custo_combustivel = litros * config.preco_combustivel

    custo_por_km = Decimal("0")

    def rateio(custo, km_ref):
        if custo and km_ref and km_ref > 0:
            return custo / km_ref
        return Decimal("0")

    custo_por_km += rateio(config.custo_troca_oleo, config.km_troca_oleo)
    custo_por_km += rateio(config.custo_pneu_dianteiro, config.km_troca_pneu_dianteiro)
    custo_por_km += rateio(config.custo_pneu_traseiro, config.km_troca_pneu_traseiro)
    custo_por_km += rateio(config.custo_kit_traseiro, config.km_troca_kit_traseiro)
    custo_por_km += rateio(config.custo_manutencao_geral, config.km_manutencao_geral)

    custo_variavel = custo_por_km * km

    # Custos fixos
    custos_fixos = (
        (config.seguro_mensal or 0)
        + (config.licenciamento_mensal or 0)
        + (config.ipva_mensal or 0)
        + (config.outros_custos_mensais or 0)
    )

    km_base = config.km_medio_mensal or km
    custo_fixo = (custos_fixos / km_base) * km if km_base > 0 else 0

    return custo_combustivel + custo_variavel + custo_fixo
