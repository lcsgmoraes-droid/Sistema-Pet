from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_card_sales_query_does_not_distinct_full_json_entity():
    source = (ROOT / "backend/app/conciliacao_aba1_routes.py").read_text(
        encoding="utf-8"
    )

    assert "query.distinct().offset" not in source
    assert "query.distinct(Venda.id).count()" not in source
    assert "query.with_entities(Venda.id).distinct()" in source
    assert "VendaPagamento.tenant_id == tenant_id" in source
    assert 'VendaPagamento.forma_pagamento.ilike("%credito%")' in source


def test_demo_card_payments_are_tied_to_operator_and_left_pending():
    source = (
        ROOT / "backend/app/scripts/seed_demo_operacional_sales_core.py"
    ).read_text(encoding="utf-8")

    assert 'is_card_payment = scenario.payment_key in {"debito", "credito"}' in source
    assert 'support["card_operator_id"] if is_card_payment else None' in source
    assert '"conciliation_status": "nao_conciliado"' in source


def test_demo_seed_includes_operator_side_reconciliation_rows():
    source = (
        ROOT / "backend/app/scripts/seed_demo_operacional_conciliation.py"
    ).read_text(encoding="utf-8")

    assert "DEMO-NSU-ORFAO-001" in source
    assert '"demo_operacional": True' in source
    assert "conciliacao_importacoes" in source


def test_match_processing_uses_only_card_payments_from_selected_operator():
    source = (ROOT / "backend/app/conciliacao_services_stone.py").read_text(
        encoding="utf-8"
    )

    assert "db.query(Venda).join(VendaPagamento).filter" in source
    assert "VendaPagamento.tenant_id == tenant_id" in source
    assert 'VendaPagamento.forma_pagamento.ilike("%credito%")' in source
    assert "VendaPagamento.operadora_id == operadora_id" in source
    assert "VendaPagamento.operadora_id.is_(None)" not in source
