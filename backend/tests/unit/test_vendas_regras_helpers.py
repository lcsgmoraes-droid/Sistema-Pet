from types import SimpleNamespace

import pytest

from app.vendas.regras import (
    _resolver_status_entrega_atualizacao,
    calcular_totais_venda,
    validar_consistencia_desconto_cupom,
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


def test_valida_cupom_quando_desconto_real_cobre_o_valor_aplicado():
    validar_consistencia_desconto_cupom(
        cupom_code="FIEL-ABC123",
        cupom_discount_applied=25,
        desconto_total=25,
    )


def test_valida_cupom_com_desconto_manual_adicional():
    validar_consistencia_desconto_cupom(
        cupom_code="FIEL-ABC123",
        cupom_discount_applied=25,
        desconto_total=30,
    )


def test_rejeita_cupom_maior_que_o_desconto_real_da_venda():
    with pytest.raises(ValueError, match="carrinho mudou"):
        validar_consistencia_desconto_cupom(
            cupom_code="FIEL-GT1B49",
            cupom_discount_applied=25,
            desconto_total=6.98,
        )
