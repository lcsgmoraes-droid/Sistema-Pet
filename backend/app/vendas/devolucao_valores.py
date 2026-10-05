"""Rateio determinístico do valor pago pelos itens de uma venda devolvida."""

from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP


CENTAVO = Decimal("0.01")


def _decimal(valor) -> Decimal:
    return Decimal(str(valor if valor is not None else 0))


def _moeda(valor) -> Decimal:
    return _decimal(valor).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def ratear_valor_pago_por_item(venda, itens_venda) -> dict[int, Decimal]:
    """Distribui o total pago pelos itens, retirando o frete não estornado.

    O subtotal de cada item é o peso. Assim, descontos já lançados no item
    permanecem nele e o desconto geral é distribuído proporcionalmente.
    Sobras de centavos vão para os maiores restos, com desempate pelo ID.
    """
    itens = sorted(itens_venda, key=lambda item: item.id)
    ids = [item.id for item in itens]
    if not itens or len(set(ids)) != len(ids):
        raise ValueError("Itens da venda ausentes ou duplicados")

    valor_itens = _moeda(venda.total) - _moeda(getattr(venda, "taxa_entrega", 0))
    if valor_itens < 0:
        raise ValueError("Valor pago pelos itens da venda é inválido")

    if any(getattr(item, "subtotal", None) is None for item in itens):
        raise ValueError("Subtotal original de item da venda ausente")
    pesos = [_decimal(item.subtotal) for item in itens]
    if any(peso < 0 for peso in pesos):
        raise ValueError("Subtotal de item da venda é inválido")
    total_pesos = sum(pesos, Decimal("0"))
    if total_pesos <= 0:
        if valor_itens:
            raise ValueError("Itens sem base para ratear o valor pago")
        return {item_id: Decimal("0") for item_id in ids}

    centavos = int(valor_itens / CENTAVO)
    cotas = [Decimal(centavos) * peso / total_pesos for peso in pesos]
    centavos_por_item = [
        int(cota.to_integral_value(rounding=ROUND_FLOOR)) for cota in cotas
    ]
    restos = [cota - piso for cota, piso in zip(cotas, centavos_por_item)]
    sobra = centavos - sum(centavos_por_item)
    for indice in sorted(range(len(itens)), key=lambda i: (-restos[i], ids[i]))[:sobra]:
        centavos_por_item[indice] += 1

    return {
        item_id: Decimal(centavos_item) * CENTAVO
        for item_id, centavos_item in zip(ids, centavos_por_item)
    }


def valor_devolvido_por_quantidade(
    item, valor_item: Decimal, quantidade_anterior: Decimal, quantidade_atual: Decimal
) -> Decimal:
    """Diferença entre cotas cumulativas; a última parcela recebe o centavo final."""
    quantidade_vendida = _decimal(item.quantidade)
    quantidade_anterior = _decimal(quantidade_anterior)
    quantidade_atual = _decimal(quantidade_atual)
    if (
        quantidade_vendida <= 0
        or quantidade_anterior < 0
        or quantidade_atual <= 0
        or quantidade_anterior + quantidade_atual > quantidade_vendida
    ):
        raise ValueError("Quantidade devolvida fora do saldo vendido")

    antes = _moeda(valor_item * quantidade_anterior / quantidade_vendida)
    depois = _moeda(
        valor_item * (quantidade_anterior + quantidade_atual) / quantidade_vendida
    )
    return depois - antes
