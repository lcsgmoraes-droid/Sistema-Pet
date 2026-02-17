
def validar_rateio_item(
    rateios,
    quantidade_total_item,
    preco_unitario
):
    """
    rateios: lista de dicts:
    [{ "canal": "mercado_livre", "quantidade": 7 }, ...]
    """

    if not rateios:
        raise ValueError("Rateio do item é obrigatório")

    canais = [r["canal"] for r in rateios]

    # Regra Online x Marketplaces
    if "online" in canais:
        for c in ["mercado_livre", "shopee", "amazon"]:
            if c in canais:
                raise ValueError(
                    "Canal 'online' não pode coexistir com marketplaces específicos"
                )

    # Quantidades
    soma_qtd = 0
    for r in rateios:
        qtd = int(r.get("quantidade", 0))
        if qtd <= 0:
            raise ValueError("Quantidade deve ser maior que zero")
        soma_qtd += qtd

    if soma_qtd != quantidade_total_item:
        raise ValueError(
            f"Soma das quantidades ({soma_qtd}) "
            f"difere da quantidade do item ({quantidade_total_item})"
        )

    # Cálculo automático
    resultado = []
    for r in rateios:
        qtd = r["quantidade"]
        valor = round(qtd * preco_unitario, 2)
        percentual = round((qtd / quantidade_total_item) * 100, 2)

        resultado.append({
            "canal": r["canal"],
            "quantidade": qtd,
            "valor_calculado": valor,
            "percentual_calculado": percentual
        })

    return resultado
