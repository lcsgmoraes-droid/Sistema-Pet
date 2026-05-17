from types import SimpleNamespace

import pytest

from app.vendas.regras import (
    _resolver_status_entrega_atualizacao,
    calcular_totais_venda,
)


def test_calcular_totais_venda_nao_duplica_desconto_rateado_no_item():
    itens = [
        SimpleNamespace(subtotal=80, desconto_item=20),
        SimpleNamespace(subtotal=50, desconto_item=0),
    ]

    totais = calcular_totais_venda(
        itens=itens,
        desconto_valor=20,
        desconto_percentual=0,
        taxa_entrega=10,
    )

    assert totais["subtotal"] == pytest.approx(130)
    assert totais["desconto_valor"] == pytest.approx(20)
    assert totais["total"] == pytest.approx(140)


def test_calcular_totais_venda_aplica_desconto_percentual_quando_nao_ha_rateio():
    itens = [
        SimpleNamespace(subtotal=100, desconto_item=0),
        SimpleNamespace(subtotal=50, desconto_item=0),
    ]

    totais = calcular_totais_venda(
        itens=itens,
        desconto_valor=0,
        desconto_percentual=10,
        taxa_entrega=5,
    )

    assert totais["subtotal"] == pytest.approx(150)
    assert totais["desconto_valor"] == pytest.approx(15)
    assert totais["total"] == pytest.approx(140)


def test_resolver_status_entrega_preserva_status_existente():
    assert _resolver_status_entrega_atualizacao(True, "em_rota") == "em_rota"
    assert _resolver_status_entrega_atualizacao(True, "entregue") == "entregue"
    assert _resolver_status_entrega_atualizacao(True, None) == "pendente"
    assert _resolver_status_entrega_atualizacao(False, "entregue") is None
