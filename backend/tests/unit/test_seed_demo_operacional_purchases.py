from datetime import datetime
from decimal import Decimal

from app.notas_entrada.xml_parser import parse_nfe_xml
from app.scripts.seed_demo_operacional_catalog import DEMO_MARGIN_PRODUCTS
from app.scripts.seed_demo_operacional_purchase_data import (
    build_demo_purchase_scenarios,
    demo_xml,
    invoice_key,
    tenant_suffix,
)
from app.scripts.seed_demo_operacional_purchases import _confrontation_status


def test_demo_purchase_scenarios_cover_operational_states():
    scenarios = build_demo_purchase_scenarios()

    assert len(scenarios) == 9
    assert scenarios[-1] == {
        "key": "live_xml",
        "order_status": "confirmado",
        "label": "Pedido reservado para importar e confrontar XML ao vivo",
    }

    assert {scenario["order_status"] for scenario in scenarios} >= {
        "rascunho",
        "enviado",
        "confirmado",
        "recebido_parcial",
        "recebido_total",
        "cancelado",
    }
    assert {
        scenario.get("pending_status")
        for scenario in scenarios
        if scenario.get("pending_status")
    } == {
        "aberta",
        "aguardando_fornecedor",
        "em_tratativa",
        "resolvida",
        "cancelada",
    }


def test_demo_xml_is_parsed_as_homologation_invoice():
    tenant_id = "8f552f1d-2b88-4fc8-8420-000000000001"
    access_key = invoice_key(tenant_id, 900002)
    xml = demo_xml(
        invoice_number=900002,
        access_key=access_key,
        issued_at=datetime(2026, 8, 12, 12, 5),
        supplier_code="BIO-6083",
        product_name="Racao Bionatural Prime 2,5kg",
        ean="7898242030076",
        quantity=Decimal("8"),
        unit_cost=Decimal("33.50"),
    )

    parsed = parse_nfe_xml(xml.encode("utf-8"))

    assert len(access_key) == 44
    assert parsed["numero_nota"] == "900002"
    assert parsed["chave_acesso"] == access_key
    assert parsed["fornecedor_cnpj"] == "11222333000181"
    assert parsed["valor_total"] == 268.0
    assert parsed["itens"][0]["codigo_produto"] == "BIO-6083"
    assert parsed["itens"][0]["quantidade"] == 8.0
    assert parsed["itens"][0]["valor_unitario"] == 33.5
    assert "SEM VALOR FISCAL" in xml


def test_demo_purchase_identifiers_and_confrontation_status_are_deterministic():
    tenant_id = "8f552f1d-2b88-4fc8-8420-000000000001"

    assert tenant_suffix(tenant_id) == "8F552F1D"
    assert invoice_key(tenant_id, 900001) == invoice_key(tenant_id, 900001)
    assert invoice_key(tenant_id, 900001) != invoice_key(tenant_id, 900002)
    assert (
        _confrontation_status(
            Decimal("10"), Decimal("10"), Decimal("30.94"), Decimal("30.94")
        )
        == "sem_divergencia"
    )
    assert (
        _confrontation_status(
            Decimal("10"), Decimal("8"), Decimal("30.94"), Decimal("33.50")
        )
        == "divergencia_mista"
    )


def test_margin_demo_products_cover_green_yellow_and_red_after_card_costs():
    by_code = {product["code"]: product for product in DEMO_MARGIN_PRODUCTS}

    def margin_percent(code: str) -> Decimal:
        product = by_code[code]
        price = product["price"]
        net = (
            price
            - product["cost"]
            - (price * Decimal("0.07"))
            - (price * Decimal("0.0349"))
        )
        return (net / price * Decimal("100")).quantize(Decimal("0.01"))

    assert margin_percent("DEMO-MARGEM-VERDE") >= Decimal("30.00")
    assert Decimal("15.00") <= margin_percent("DEMO-MARGEM-AMARELA") < Decimal("30.00")
    assert margin_percent("DEMO-MARGEM-VERMELHA") < Decimal("15.00")
