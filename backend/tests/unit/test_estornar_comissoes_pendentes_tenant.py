from decimal import Decimal
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.scripts.estornar_comissoes_pendentes_tenant import (
    identificar_provisoes_orfas,
    validar_plano,
    validar_orfaos_esperados,
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


def test_provisao_orfa_so_e_aceita_sem_conta_ou_periodo_dre():
    item = SimpleNamespace(
        id=169, venda_id=1341101, comissao_provisionada=True, conta_pagar_id=None
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.first.side_effect = [
        None,
        (datetime(2026, 10, 1),),
        None,
    ]
    assert identificar_provisoes_orfas(db, tenant_id="tenant", itens=[item]) == [item]
    validar_orfaos_esperados([item], [169])
    with pytest.raises(ValueError, match="diferem da prévia"):
        validar_orfaos_esperados([item], [])

    db.query.return_value.filter.return_value.first.side_effect = [
        (4998,),
        (datetime(2026, 10, 1),),
        None,
    ]
    with pytest.raises(ValueError, match="revisão manual"):
        identificar_provisoes_orfas(db, tenant_id="tenant", itens=[item])


def test_provisao_orfa_com_periodo_dre_bloqueia_estorno():
    item = SimpleNamespace(
        id=223, venda_id=1341185, comissao_provisionada=True, conta_pagar_id=None
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.first.side_effect = [
        None,
        (datetime(2026, 10, 1),),
        (1,),
    ]
    with pytest.raises(ValueError, match="período DRE"):
        identificar_provisoes_orfas(db, tenant_id="tenant", itens=[item])
