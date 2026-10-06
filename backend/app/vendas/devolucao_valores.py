"""Rateio determinístico do valor pago pelos itens de uma venda devolvida."""

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_FLOOR, ROUND_HALF_UP


CENTAVO = Decimal("0.01")


def _decimal(valor) -> Decimal:
    try:
        numero = Decimal(str(valor if valor is not None else 0))
    except (InvalidOperation, ValueError, TypeError) as erro:
        raise ValueError("Valor numerico invalido na devolucao") from erro
    if not numero.is_finite():
        raise ValueError("Valor numerico invalido na devolucao")
    return numero


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


@dataclass(frozen=True)
class CotacaoDevolucao:
    valor_total: Decimal
    valor_ja_devolvido: Decimal
    valores_itens: tuple[Decimal, ...]

    @property
    def valor_acumulado(self) -> Decimal:
        return self.valor_ja_devolvido + self.valor_total


def validar_itens_devolucao(itens_solicitados) -> None:
    """Rejeita corpo malformado antes de qualquer conversao ou escrita."""
    if not isinstance(itens_solicitados, list) or not itens_solicitados:
        raise ValueError("Selecione ao menos um item para devolução")
    if any(not isinstance(item, dict) for item in itens_solicitados):
        raise ValueError("Itens da devolução inválidos")
    if any(item.get("is_componente_kit") for item in itens_solicitados):
        raise ValueError(
            "Devolução por componente de KIT indisponível: a venda não registra "
            "o preço original de cada componente. Devolva o KIT inteiro."
        )
    if any(
        not isinstance(item.get("item_id"), int)
        or isinstance(item.get("item_id"), bool)
        or _decimal(item.get("quantidade")) <= 0
        for item in itens_solicitados
    ):
        raise ValueError("Item ou quantidade da devolução inválido")


def cotar_devolucao(venda, itens_venda, eventos_anteriores, itens_solicitados):
    """Fonte única do valor mostrado na prévia e gravado no reembolso."""
    validar_itens_devolucao(itens_solicitados)
    status = str(getattr(venda, "status", "") or "").lower()
    if status not in {
        "finalizada",
        "pago_nf",
        "baixa_parcial",
        "finalizada_devolucao",
        "finalizada_devolucao_parcial",
    }:
        raise ValueError("A venda não está em situação que permita devolução")
    if status in {"finalizada_devolucao", "finalizada_devolucao_parcial"} and not (
        eventos_anteriores
    ):
        raise ValueError(
            "Esta venda tem devolução anterior sem valor rastreável. "
            "Concilie manualmente o histórico antes de nova devolução."
        )

    itens_por_id = {item.id: item for item in itens_venda}
    valor_pago_por_item = ratear_valor_pago_por_item(venda, itens_venda)
    quantidade_anterior = defaultdict(Decimal)
    for evento in eventos_anteriores:
        for devolvido in evento.itens or []:
            if devolvido.get("is_componente_kit"):
                continue
            item_id = devolvido.get("venda_item_id")
            quantidade_anterior[item_id] += _decimal(devolvido.get("quantidade"))

    quantidade_atual = defaultdict(Decimal)
    valores_itens = []
    for solicitado in itens_solicitados:
        item_id = solicitado.get("item_id")
        item = itens_por_id.get(item_id)
        if item is None:
            raise ValueError(f"Item {item_id} não encontrado na venda")
        quantidade = _decimal(solicitado.get("quantidade"))
        valor = valor_devolvido_por_quantidade(
            item,
            valor_pago_por_item[item_id],
            quantidade_anterior[item_id] + quantidade_atual[item_id],
            quantidade,
        )
        quantidade_atual[item_id] += quantidade
        valores_itens.append(valor)

    valor_total = sum(valores_itens, Decimal("0"))
    if valor_total <= 0:
        raise ValueError("A devolução precisa ter valor positivo")
    valor_ja_devolvido = sum(
        (_decimal(evento.valor_devolvido) for evento in eventos_anteriores),
        Decimal("0"),
    )
    if valor_ja_devolvido + valor_total > _moeda(venda.total):
        raise ValueError("Valor acumulado das devoluções excede o total pago na venda")

    return CotacaoDevolucao(valor_total, valor_ja_devolvido, tuple(valores_itens))
