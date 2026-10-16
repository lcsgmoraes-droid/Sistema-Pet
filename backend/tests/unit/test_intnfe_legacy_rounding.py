"""Compatibilidade fiscal restrita ao arredondamento demonstravel de vendas antigas."""

from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP

import pytest

from app.intnfe import emission
from tests.unit.test_intnfe_emission import _objects, fiscal_data as fiscal_data


def _sale(rows, *, total, discount="0.00", new_contract=False):
    tenant, connection, sale = _objects()
    template = sale.itens[0]
    sale.itens = []
    for index, (quantity, price, item_discount, subtotal) in enumerate(rows):
        item = deepcopy(template)
        item.id = index + 1
        item.produto.id = index + 10
        item.produto.codigo = f"TESTE-{index + 1}"
        item.quantidade = quantity
        item.preco_unitario = price
        item.desconto_item = item_discount
        item.subtotal = subtotal
        sale.itens.append(item)
    sale.total = total
    sale.subtotal = total
    sale.desconto_valor = discount
    sale.desconto_venda_valor = "0.00" if new_contract else None
    sale.tem_entrega = False
    sale.taxa_entrega = "0.00"
    sale.pagamentos[0].valor = total
    return tenant, connection, sale


def _discounted_sale(**kwargs):
    return _sale(
        [
            ("1.000", "30.50", "1.52", "28.98"),
            ("0.698", "16.90", "0.59", "11.21"),
            ("1.332", "9.90", "0.66", "12.53"),
        ],
        total="52.71",
        discount="2.77",
        **kwargs,
    )


@pytest.mark.parametrize("document_type", ["nfe", "nfce"])
@pytest.mark.parametrize(
    "quantity, price, subtotal",
    [("1.024", "47.87", "49.00"), ("1.062", "178.90", "189.90")],
)
def test_legacy_quantity_from_four_decimals_preserves_saved_subtotal(
    document_type, quantity, price, subtotal
):
    tenant, connection, sale = _sale(
        [(quantity, price, "0.00", subtotal)], total=subtotal
    )
    original = deepcopy(sale)

    payload = emission.build_payload(None, tenant, connection, sale, document_type)

    product = payload["produtos"][0]
    assert Decimal(str(product["valorTotal"])) == Decimal(subtotal)
    assert Decimal(str(product["quantidade"])) == Decimal(quantity)
    assert (
        Decimal(str(product["quantidade"])) * Decimal(str(product["valorUnitario"]))
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) == Decimal(subtotal)
    assert "desconto" not in product
    assert payload["pagamentos"] == [{"formaPagamento": "17", "valor": float(subtotal)}]
    assert sale == original


@pytest.mark.parametrize("document_type", ["nfe", "nfce"])
def test_legacy_raw_aggregate_preserves_recorded_discounts_and_final_tax_base(
    document_type, monkeypatch
):
    tenant, connection, sale = _discounted_sale()
    original = deepcopy(sale)
    bases = []
    original_tax = emission._tax

    def tax_after_final_gross(*args):
        bases.append(args[-1])
        return original_tax(*args)

    monkeypatch.setattr(emission, "_tax", tax_after_final_gross)

    payload = emission.build_payload(None, tenant, connection, sale, document_type)

    products = payload["produtos"]
    assert [p["valorTotal"] for p in products] == [30.50, 11.79, 13.19]
    assert [p["desconto"] for p in products] == [1.52, 0.59, 0.66]
    assert bases == [Decimal("28.98"), Decimal("11.20"), Decimal("12.53")]
    assert sum(bases) == Decimal("52.71")
    assert sum(Decimal(str(p["desconto"])) for p in products) == Decimal("2.77")
    for product in products:
        assert (
            Decimal(str(product["quantidade"])) * Decimal(str(product["valorUnitario"]))
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) == Decimal(
            str(product["valorTotal"])
        )
    assert sale == original


@pytest.mark.parametrize("document_type", ["nfe", "nfce"])
@pytest.mark.parametrize("example", ["quantity_49", "quantity_189_90", "discounts"])
def test_local_document_details_matches_legacy_payload_totals_and_unit_prices(
    document_type, example
):
    if example == "discounts":
        tenant, connection, sale = _discounted_sale()
    else:
        quantity, price, subtotal = (
            ("1.024", "47.87", "49.00")
            if example == "quantity_49"
            else ("1.062", "178.90", "189.90")
        )
        tenant, connection, sale = _sale(
            [(quantity, price, "0.00", subtotal)], total=subtotal
        )
    sale.id = 123
    sale.nfe_tipo = document_type
    sale.nfe_modelo = "55" if document_type == "nfe" else "65"
    sale.nfe_status = "rejeitada"
    for field in (
        "nfe_numero",
        "nfe_serie",
        "nfe_chave",
        "nfe_codigo_erro",
        "nfe_motivo_rejeicao",
        "nfe_protocolo",
        "nfe_ambiente",
        "nfe_data_emissao",
    ):
        setattr(sale, field, None)
    original = deepcopy(sale)

    payload = emission.build_payload(None, tenant, connection, sale, document_type)
    details = emission.local_document_details(None, tenant, sale)

    for product, item in zip(payload["produtos"], details["itens"]):
        assert item["valor_total"] == product["valorTotal"]
        assert item["valor_unitario"] == product["valorUnitario"]
        assert item["desconto"] == product.get("desconto", 0)
    totals = details["totais"]
    assert (
        Decimal(str(totals["valor_produtos"]))
        - Decimal(str(totals["valor_desconto"]))
        + Decimal(str(totals["valor_frete"]))
    ) == Decimal(sale.total)
    assert sale == original


@pytest.mark.parametrize(
    "quantity, price, subtotal, new_contract",
    [
        ("1.024", "47.87", "49.50", False),
        ("1.000", "47.87", "47.85", False),
        ("1.062", "178.90", "189.90", True),
    ],
)
def test_incompatible_quantity_integral_or_new_contract_stays_blocked(
    quantity, price, subtotal, new_contract
):
    tenant, connection, sale = _sale(
        [(quantity, price, "0.00", subtotal)],
        total=subtotal,
        new_contract=new_contract,
    )

    with pytest.raises(emission.DirectEmissionError, match="subtotal salvo"):
        emission.build_payload(None, tenant, connection, sale, "nfe")


def test_legacy_aggregate_requires_exact_raw_sum_proof():
    tenant, connection, sale = _discounted_sale()
    sale.total = "52.70"
    sale.pagamentos[0].valor = "52.70"

    with pytest.raises(emission.DirectEmissionError, match="total fiscal calculado"):
        emission.build_payload(None, tenant, connection, sale, "nfe")


def test_legacy_aggregate_does_not_hide_discrepant_recorded_discounts():
    tenant, connection, sale = _discounted_sale()
    sale.desconto_valor = "2.78"

    with pytest.raises(emission.DirectEmissionError, match="desconto da venda"):
        emission.build_payload(None, tenant, connection, sale, "nfe")


def test_raw_aggregate_compatibility_does_not_apply_to_new_contract():
    tenant, connection, sale = _discounted_sale(new_contract=True)

    with pytest.raises(emission.DirectEmissionError, match="total fiscal calculado"):
        emission.build_payload(None, tenant, connection, sale, "nfe")


def test_legacy_aggregate_does_not_fix_corrupted_item_subtotal():
    tenant, connection, sale = _discounted_sale()
    sale.itens[1].subtotal = "11.18"

    with pytest.raises(emission.DirectEmissionError, match="subtotal salvo"):
        emission.build_payload(None, tenant, connection, sale, "nfe")


@pytest.mark.parametrize("form", ["PIX", "Crédito Cliente", "Cashback"])
def test_legacy_rounding_does_not_clip_excess_payment(form):
    tenant, connection, sale = _sale(
        [("1.167", "29.90", "0.00", "34.89")], total="34.89"
    )
    sale.pagamentos[0].forma_pagamento = form
    sale.pagamentos[0].valor = "34.90"

    with pytest.raises(emission.DirectEmissionError, match="formas de pagamento"):
        emission.build_payload(None, tenant, connection, sale, "nfe")

    assert sale.pagamentos[0].valor == "34.90"
