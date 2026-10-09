"""Descontos de linha e da venda, com rateio deterministico em centavos."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

CENTAVO = Decimal("0.01")
ZERO = Decimal("0")
MAX_MOEDA = Decimal("99999999.99")
MAX_QUANTIDADE = Decimal("9999999.999")


def _campo(obj: Any, nome: str, default=None):
    return (
        obj.get(nome, default) if isinstance(obj, dict) else getattr(obj, nome, default)
    )


def _quantizar(valor: Any, escala: Decimal, limite: Decimal) -> Decimal:
    try:
        numero = Decimal(str(valor or 0))
        if not numero.is_finite() or abs(numero) > limite:
            raise ValueError("Valor da venda fora do limite permitido.")
        resultado = numero.quantize(escala, rounding=ROUND_HALF_UP)
        if abs(resultado) > limite:
            raise ValueError("Valor da venda fora do limite permitido.")
        return resultado
    except (InvalidOperation, TypeError) as exc:
        raise ValueError("Valor numerico invalido na venda.") from exc


def moeda(valor: Any) -> Decimal:
    return _quantizar(valor, CENTAVO, MAX_MOEDA)


def quantidade_venda(valor: Any) -> Decimal:
    quantidade = _quantizar(valor, Decimal("0.001"), MAX_QUANTIDADE)
    if quantidade <= 0:
        raise ValueError(
            "A quantidade precisa ser positiva com ate tres casas decimais."
        )
    return quantidade


def bruto_item(item: Any) -> Decimal:
    quantidade = quantidade_venda(_campo(item, "quantidade", 0))
    preco = moeda(_campo(item, "preco_unitario", 0))
    if preco < 0:
        raise ValueError("Confira a quantidade e o preco dos itens da venda.")
    return moeda(quantidade * preco)


def liquido_item(item: Any) -> Decimal:
    bruto = bruto_item(item)
    desconto = moeda(_campo(item, "desconto_item", 0))
    if not ZERO <= desconto <= bruto:
        raise ValueError("O desconto do item deve ficar entre zero e o valor da linha.")
    return bruto - desconto


def normalizar_item_venda(item: Any) -> dict:
    """Usar a mesma precisao do registro persistido, antes dos totais/estoque."""
    return {
        "quantidade": float(quantidade_venda(_campo(item, "quantidade", 0))),
        "preco_unitario": float(moeda(_campo(item, "preco_unitario", 0))),
        "desconto_item": float(moeda(_campo(item, "desconto_item", 0))),
        "subtotal": float(liquido_item(item)),
    }


def ratear_centavos(total: Any, pesos: list[Decimal], *, ids=None) -> list[Decimal]:
    """Maior resto; empates seguem a ordem persistida dos itens."""
    total = moeda(total)
    soma = sum(pesos, ZERO)
    if total < 0 or any(peso < 0 for peso in pesos):
        raise ValueError("O desconto nao pode ser negativo.")
    if soma <= 0:
        if total:
            raise ValueError("Nao ha valor de itens para aplicar o desconto.")
        return [ZERO for _ in pesos]
    centavos = int(total / CENTAVO)
    quotas = [Decimal(centavos) * peso / soma for peso in pesos]
    inteiros = [int(quota) for quota in quotas]
    ordem = sorted(
        range(len(pesos)),
        key=lambda i: (-(quotas[i] - inteiros[i]), ids[i] if ids is not None else i),
    )
    for i in ordem[: centavos - sum(inteiros)]:
        inteiros[i] += 1
    return [Decimal(valor) * CENTAVO for valor in inteiros]


def ratear_descontos_venda(venda: Any, *, cupom_desconto=None) -> list[dict]:
    """Di fica em sua linha. Apenas G e C sao distribuidos sobre os liquidos.

    NULL em G identifica o contrato antigo: nao alteramos a origem registrada.
    O rateio legado conserva os descontos de linha conhecidos e o agregado,
    sem chamar de manual a parcela cuja origem historica e ambigua.
    """
    itens = list(_campo(venda, "itens", []) or [])
    ids = [_campo(item, "id", indice) or indice for indice, item in enumerate(itens)]
    brutos = [bruto_item(item) for item in itens]
    individuais = [moeda(_campo(item, "desconto_item", 0)) for item in itens]
    global_valor = _campo(venda, "desconto_venda_valor")
    cupom = moeda(
        cupom_desconto
        if cupom_desconto is not None
        else _campo(venda, "cupom_discount_applied", 0)
    )
    legado = global_valor is None
    if legado:
        agregado = moeda(_campo(venda, "desconto_valor", 0))
        cupom = min(max(cupom, ZERO), agregado)
        # Cupons antigos podiam estar embutidos em desconto_item. Preservar
        # os totais por linha sem afirmar uma autoria manual que nao existe.
        soma_individuais = sum(individuais, ZERO)
        if soma_individuais > agregado:
            individuais = ratear_centavos(agregado, individuais, ids=ids)
        restante = agregado - sum(individuais, ZERO)
        extras = ratear_centavos(
            restante,
            [max(bruto - di, ZERO) for bruto, di in zip(brutos, individuais)],
            ids=ids,
        )
        efetivos = [di + extra for di, extra in zip(individuais, extras)]
        cupons = ratear_centavos(cupom, efetivos, ids=ids)
        return [
            {
                "desconto_item": di,
                "desconto_venda": None,
                "cupom": c,
                "manual": d - c,
                "total": d,
                "legado": True,
            }
            for di, d, c in zip(individuais, efetivos, cupons)
        ]

    global_valor = moeda(global_valor)
    liquidos = [liquido_item(item) for item in itens]
    if global_valor < 0 or cupom < 0 or global_valor + cupom > sum(liquidos, ZERO):
        raise ValueError(
            "O desconto geral e o cupom nao podem exceder o valor dos itens."
        )
    # Ratear o valor pago usa o mesmo desempate da devolucao. Ratear o
    # desconto diretamente daria o centavo residual ao item oposto.
    pagos = ratear_centavos(
        sum(liquidos, ZERO) - global_valor - cupom, liquidos, ids=ids
    )
    compartilhados = [liquido - pago for liquido, pago in zip(liquidos, pagos)]
    globais = ratear_centavos(global_valor, compartilhados, ids=ids)
    return [
        {
            "desconto_item": di,
            "desconto_venda": g,
            "cupom": extra - g,
            "manual": di + g,
            "total": di + extra,
            "legado": False,
        }
        for di, g, extra in zip(individuais, globais, compartilhados)
    ]


def resumo_descontos_venda(venda: Any) -> dict:
    global_valor = _campo(venda, "desconto_venda_valor")
    return {
        "desconto_venda_valor": float(moeda(global_valor))
        if global_valor is not None
        else None,
        "desconto_itens_valor": float(
            sum(
                (
                    moeda(_campo(item, "desconto_item", 0))
                    for item in list(_campo(venda, "itens", []) or [])
                ),
                ZERO,
            )
        ),
        "desconto_origem_legado": global_valor is None,
    }
