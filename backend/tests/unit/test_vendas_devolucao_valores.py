from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.vendas.devolucao_valores import (
    ratear_valor_pago_por_item,
    validar_itens_devolucao,
    valor_devolvido_por_quantidade,
)


def _item(item_id, subtotal, quantidade=1, preco_unitario=50):
    return SimpleNamespace(
        id=item_id,
        subtotal=Decimal(subtotal),
        quantidade=Decimal(str(quantidade)),
        preco_unitario=Decimal(str(preco_unitario)),
    )


def test_rateio_respeita_desconto_geral_e_desconto_ja_aplicado_ao_item():
    primeiro = _item(1, "40.00")
    segundo = _item(2, "50.00")
    venda = SimpleNamespace(total=Decimal("81.00"), taxa_entrega=0)

    assert ratear_valor_pago_por_item(venda, [segundo, primeiro]) == {
        1: Decimal("36.00"),
        2: Decimal("45.00"),
    }


def test_rateio_centavos_e_independente_da_ordem_e_preserva_total_pago():
    itens = [_item(3, "1.00"), _item(1, "1.00"), _item(2, "1.00")]
    venda = SimpleNamespace(total=Decimal("1.00"), taxa_entrega=0)

    assert ratear_valor_pago_por_item(venda, itens) == {
        1: Decimal("0.34"),
        2: Decimal("0.33"),
        3: Decimal("0.33"),
    }
    assert ratear_valor_pago_por_item(venda, list(reversed(itens))) == (
        ratear_valor_pago_por_item(venda, itens)
    )


def test_frete_nao_e_rateado_nas_devolucoes_de_itens():
    venda = SimpleNamespace(total=Decimal("100.00"), taxa_entrega=Decimal("10.00"))

    assert ratear_valor_pago_por_item(
        venda, [_item(1, "50.00"), _item(2, "50.00")]
    ) == {1: Decimal("45.00"), 2: Decimal("45.00")}


def test_devolucoes_parciais_sucessivas_fecham_centavos_da_ultima_parcela():
    item = _item(1, "100.00", quantidade=3, preco_unitario=Decimal("33.33"))
    valor_item = Decimal("100.00")

    parcelas = [
        valor_devolvido_por_quantidade(item, valor_item, Decimal(indice), Decimal("1"))
        for indice in range(3)
    ]

    assert parcelas == [Decimal("33.33"), Decimal("33.34"), Decimal("33.33")]
    assert sum(parcelas) == valor_item


def test_duas_devolucoes_parciais_de_venda_com_desconto_somam_liquido_pago():
    item = _item(1, "100.00", quantidade=2)
    venda = SimpleNamespace(total=Decimal("90.00"), taxa_entrega=0)
    valor_item = ratear_valor_pago_por_item(venda, [item])[item.id]

    assert valor_devolvido_por_quantidade(item, valor_item, 0, 1) == Decimal("45.00")
    assert valor_devolvido_por_quantidade(item, valor_item, 1, 1) == Decimal("45.00")


@pytest.mark.parametrize(
    "itens",
    [
        {"item_id": 1, "quantidade": 1},
        ["item inválido"],
        [{"item_id": 1, "quantidade": "NaN"}],
        [{"item_id": 1, "quantidade": "Infinity"}],
        [{"item_id": 1, "quantidade": "valor"}],
        [{"item_id": True, "quantidade": 1}],
    ],
)
def test_corpo_malformado_nao_chega_ao_reembolso(itens):
    with pytest.raises(ValueError):
        validar_itens_devolucao(itens)
