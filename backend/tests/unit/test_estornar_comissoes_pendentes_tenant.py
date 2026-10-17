from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.scripts.estornar_comissoes_pendentes_tenant import (
    validar_plano,
    valor_total,
)


def _item(valor, *, pago=0, fechamento=None):
    return SimpleNamespace(
        valor_comissao_gerada=Decimal(valor),
        valor_pago=Decimal(pago),
        data_fechamento=fechamento,
    )


def test_plano_exige_quantidade_e_total_exatos():
    itens = [_item("0.01"), _item("0.02")]
    assert valor_total(itens) == Decimal("0.03")
    validar_plano(itens, quantidade_esperada=2, total_esperado=Decimal("0.03"))
    with pytest.raises(ValueError, match="Prévia mudou"):
        validar_plano(itens, quantidade_esperada=3, total_esperado=Decimal("0.03"))


@pytest.mark.parametrize(
    "item",
    [_item("1.00", pago="0.01"), _item("1.00", fechamento="2026-10-01")],
)
def test_plano_bloqueia_pagamento_ou_fechamento_parcial(item):
    with pytest.raises(ValueError, match="revisão manual"):
        validar_plano([item], quantidade_esperada=1, total_esperado=Decimal("1.00"))
