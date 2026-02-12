from decimal import Decimal, ROUND_HALF_UP


def calcular_fiscal_item_pdv(
    preco_unitario: Decimal,
    quantidade: Decimal,
    fiscal: dict,
    aliquotas_empresa: dict
):
    """
    Calcula os impostos de um item no PDV.
    Retorna valores prontos para exibição e soma.
    """

    base_calculo = (preco_unitario * quantidade).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    # ICMS
    icms_valor = Decimal("0.00")
    if fiscal.get("cst_icms"):
        aliquota_icms = Decimal(str(aliquotas_empresa.get("icms_aliquota_interna", 0)))
        icms_valor = (base_calculo * aliquota_icms / 100).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    # ICMS ST (simplificado)
    icms_st_valor = Decimal("0.00")
    if fiscal.get("icms_st"):
        icms_st_valor = (base_calculo * Decimal("0.10")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    # PIS
    pis_valor = Decimal("0.00")
    if fiscal.get("pis_cst"):
        aliquota_pis = Decimal(str(aliquotas_empresa.get("pis_aliquota", 0)))
        pis_valor = (base_calculo * aliquota_pis / 100).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    # COFINS
    cofins_valor = Decimal("0.00")
    if fiscal.get("cofins_cst"):
        aliquota_cofins = Decimal(str(aliquotas_empresa.get("cofins_aliquota", 0)))
        cofins_valor = (base_calculo * aliquota_cofins / 100).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    total_impostos = (
        icms_valor + icms_st_valor + pis_valor + cofins_valor
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return {
        "base_calculo": base_calculo,
        "icms": icms_valor,
        "icms_st": icms_st_valor,
        "pis": pis_valor,
        "cofins": cofins_valor,
        "total_impostos": total_impostos
    }
