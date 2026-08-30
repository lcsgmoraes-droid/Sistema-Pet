"""Resumo financeiro da venda a partir das contas efetivamente recebidas."""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable


CENTAVOS = Decimal("0.01")


def _dinheiro(valor: Any) -> Decimal:
    return Decimal(str(valor or 0)).quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def calcular_resumo_pagamento_venda(
    *,
    total: Any,
    contas_receber: Iterable[Any] | None = None,
    pagamentos: Iterable[Any] | None = None,
) -> dict[str, Decimal | str]:
    """Se houver contas, elas sao a fonte da verdade do dinheiro recebido.

    ``VendaPagamento`` registra tambem a escolha do crediario na finalizacao do
    PDV. Por isso, somar esse registro como dinheiro recebido faria uma venda a
    prazo parecer quitada antes da baixa das parcelas.
    """

    total_venda = max(_dinheiro(total), Decimal("0.00"))
    contas = list(contas_receber or [])

    if contas:
        valor_recebido = sum(
            (
                max(_dinheiro(getattr(conta, "valor_recebido", 0)), Decimal("0.00"))
                for conta in contas
            ),
            Decimal("0.00"),
        )
        saldo_contas = sum(
            (
                max(
                    _dinheiro(getattr(conta, "valor_final", 0))
                    - _dinheiro(getattr(conta, "valor_recebido", 0)),
                    Decimal("0.00"),
                )
                for conta in contas
                if str(getattr(conta, "status", "") or "").strip().lower()
                not in {"cancelado", "cancelada"}
            ),
            Decimal("0.00"),
        )
        valor_pago = min(valor_recebido, total_venda)
        if saldo_contas <= CENTAVOS:
            status = "pago"
        elif valor_recebido > CENTAVOS:
            status = "parcial"
        else:
            status = "em_aberto"
    else:
        valor_pago = min(
            sum(
                (
                    _dinheiro(getattr(pagamento, "valor", 0))
                    for pagamento in (pagamentos or [])
                ),
                Decimal("0.00"),
            ),
            total_venda,
        )
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
