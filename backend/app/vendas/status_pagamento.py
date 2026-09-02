"""Resumo financeiro da venda a partir das contas efetivamente recebidas."""

import unicodedata
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable


CENTAVOS = Decimal("0.01")


def _dinheiro(valor: Any) -> Decimal:
    return Decimal(str(valor or 0)).quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def _campo(item: Any, nome: str, padrao: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(nome, padrao)
    return getattr(item, nome, padrao)


def _texto_normalizado(valor: Any) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    return (
        "".join(char for char in texto if not unicodedata.combining(char))
        .strip()
        .lower()
    )


def _eh_pagamento_crediario(pagamento: Any) -> bool:
    forma = _texto_normalizado(_campo(pagamento, "forma_pagamento"))
    return forma == "crediario" or bool(_campo(pagamento, "intervalo_crediario"))


def _contas_do_crediario(
    contas: list[Any], pagamentos_crediario: list[Any], total_pagamentos: int
) -> list[Any]:
    formas_crediario_ids = {
        _campo(pagamento, "forma_pagamento_id")
        for pagamento in pagamentos_crediario
        if _campo(pagamento, "forma_pagamento_id") is not None
    }
    if formas_crediario_ids:
        return [
            conta
            for conta in contas
            if _campo(conta, "forma_pagamento_id") in formas_crediario_ids
        ]

    # Compatibilidade com registros antigos sem forma_pagamento_id: quando a
    # venda inteira e crediario, todas as suas contas representam as parcelas.
    if len(pagamentos_crediario) == total_pagamentos:
        return contas

    return []


def _valor_recebido_contas(contas: Iterable[Any]) -> Decimal:
    return sum(
        (
            max(_dinheiro(_campo(conta, "valor_recebido", 0)), Decimal("0.00"))
            for conta in contas
            if _texto_normalizado(_campo(conta, "status"))
            not in {"cancelado", "cancelada"}
        ),
        Decimal("0.00"),
    )


def calcular_resumo_pagamento_venda(
    *,
    total: Any,
    contas_receber: Iterable[Any] | None = None,
    pagamentos: Iterable[Any] | None = None,
) -> dict[str, Decimal | str]:
    """Resume quanto o cliente pagou, sem confundir com o repasse da operadora.

    Cartao, PIX e dinheiro quitam a obrigacao do cliente no caixa, mesmo quando
    a operadora ainda vai repassar o valor. No crediario, o registro em
    ``VendaPagamento`` representa apenas o plano; somente as baixas das parcelas
    contam como pagamento do cliente.
    """

    total_venda = max(_dinheiro(total), Decimal("0.00"))
    contas = list(contas_receber or [])
    pagamentos_lista = list(pagamentos or [])
    pagamentos_crediario = [
        pagamento
        for pagamento in pagamentos_lista
        if _eh_pagamento_crediario(pagamento)
    ]

    if pagamentos_lista:
        valor_pagamentos_imediatos = sum(
            (
                max(_dinheiro(_campo(pagamento, "valor", 0)), Decimal("0.00"))
                for pagamento in pagamentos_lista
                if not _eh_pagamento_crediario(pagamento)
            ),
            Decimal("0.00"),
        )

        valor_crediario_recebido = Decimal("0.00")
        if pagamentos_crediario:
            contas_crediario = _contas_do_crediario(
                contas, pagamentos_crediario, len(pagamentos_lista)
            )
            total_crediario = sum(
                (
                    max(_dinheiro(_campo(pagamento, "valor", 0)), Decimal("0.00"))
                    for pagamento in pagamentos_crediario
                ),
                Decimal("0.00"),
            )
            valor_crediario_recebido = min(
                _valor_recebido_contas(contas_crediario), total_crediario
            )

        valor_pago = min(
            valor_pagamentos_imediatos + valor_crediario_recebido,
            total_venda,
        )
    elif contas:
        # Compatibilidade com vendas antigas que possuem contas, mas nao tem o
        # registro da forma escolhida no PDV.
        valor_pago = min(_valor_recebido_contas(contas), total_venda)
    else:
        valor_pago = Decimal("0.00")

    if valor_pago >= total_venda - CENTAVOS:
        status = "pago"
    elif valor_pago > CENTAVOS:
        status = "parcial"
    else:
        status = "em_aberto"

    return {
        "valor_pago": valor_pago,
        "valor_restante": max(total_venda - valor_pago, Decimal("0.00")),
        "status_pagamento": status,
    }
