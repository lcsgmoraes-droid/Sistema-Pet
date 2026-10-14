"""Instrução de cobrança na entrega, independente de recebimentos financeiros."""

from decimal import Decimal, InvalidOperation

from fastapi import HTTPException


FORMAS_ENTREGA = {"dinheiro", "cartao_debito", "cartao_credito", "pix"}


def normalizar_pagamento_entrega_previsto(dados, *, tem_entrega: bool):
    if not tem_entrega or dados is None:
        return None
    if not isinstance(dados, dict):
        raise HTTPException(
            status_code=400,
            detail="Informe uma forma de pagamento válida para a entrega.",
        )

    forma = str(dados.get("forma") or "").strip().lower()
    if forma not in FORMAS_ENTREGA:
        raise HTTPException(
            status_code=400, detail="Forma de pagamento da entrega inválida."
        )

    resultado = {"forma": forma}
    valor_para_troco = dados.get("valor_para_troco")
    if forma == "dinheiro" and valor_para_troco is not None:
        try:
            valor = Decimal(str(valor_para_troco))
        except (InvalidOperation, ValueError):
            valor = Decimal("NaN")
        if not valor.is_finite() or valor < 0 or valor > Decimal("99999999.99"):
            raise HTTPException(status_code=400, detail="Valor para troco inválido.")
        resultado["valor_para_troco"] = float(valor.quantize(Decimal("0.01")))
    return resultado


def validar_valor_para_troco(previsto, *, saldo):
    if not previsto or previsto.get("forma") != "dinheiro":
        return
    valor = previsto.get("valor_para_troco")
    if valor is not None and 0 < Decimal(str(valor)) < Decimal(str(saldo)):
        raise HTTPException(
            status_code=400,
            detail="O valor que o cliente vai usar precisa cobrir o saldo da venda.",
        )
