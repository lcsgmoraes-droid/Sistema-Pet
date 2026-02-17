
def validar_rateio_percentual(rateios):
    """
    rateios: lista de dicts no formato:
    [{ "canal": "mercado_livre", "percentual": 30.0 }, ...]
    """
    if not rateios:
        raise ValueError("NF mista exige rateio por canal")

    total = sum(float(r.get("percentual", 0)) for r in rateios)

    if round(total, 2) != 100.00:
        raise ValueError(f"Rateio inválido: soma {total}% (deve ser 100%)")

    return True
