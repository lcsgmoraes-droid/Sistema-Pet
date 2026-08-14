from decimal import Decimal

import pytest

from app.scripts.seed_demo_operacional import (
    assert_safe_environment,
    build_demo_scenarios,
    build_demo_showcase_sales_scenarios,
    build_fixed_payables,
    money,
)


def test_demo_operacional_scenarios_cover_sales_story():
    scenarios = build_demo_scenarios()

    assert len(scenarios) == 54
    assert len({scenario.number for scenario in scenarios}) == len(scenarios)

    assert {scenario.channel for scenario in scenarios} >= {
        "loja_fisica",
        "app",
        "ecommerce",
    }
    assert any(scenario.delivery for scenario in scenarios)
    assert any(scenario.route_status == "concluida" for scenario in scenarios)
    assert any(scenario.route_status == "em_rota" for scenario in scenarios)
    assert any(scenario.route_status == "pendente" for scenario in scenarios)
    assert any(scenario.coupon for scenario in scenarios)
    assert any(scenario.discount_value > 0 for scenario in scenarios)
    assert any(scenario.discount_percent > 0 for scenario in scenarios)
    assert any(
        Decimal("0") < scenario.received_ratio < Decimal("1") for scenario in scenarios
    )
    assert any(scenario.received_ratio == Decimal("0") for scenario in scenarios)
    assert any(
        scenario.payment_key == "credito" and scenario.installments > 1
        for scenario in scenarios
    )
    assert any(scenario.order_origin == "app" for scenario in scenarios)
    assert any(scenario.order_origin == "web" for scenario in scenarios)
    recent_online = [
        scenario
        for scenario in scenarios[:6]
        if scenario.days_ago == 0 and scenario.channel in {"app", "ecommerce"}
    ]
    assert {scenario.channel for scenario in recent_online} == {"app", "ecommerce"}
    assert any(scenario.delivery for scenario in recent_online)
    assert any(scenario.pickup_type == "app_loja" for scenario in recent_online)
    assert any(getattr(scenario, "commissioned", False) for scenario in scenarios)
    historical_days = {scenario.days_ago for scenario in scenarios[6:]}
    assert all(1 <= day <= 88 for day in historical_days)
    assert len(historical_days) == 48
    assert max(historical_days) - min(historical_days) >= 80
    assert any(day <= 7 for day in historical_days)


def test_demo_showcase_product_has_six_multichannel_sales():
    scenarios = build_demo_showcase_sales_scenarios()

    assert [scenario.number for scenario in scenarios] == [
        "DEMO-VEN-201",
        "DEMO-VEN-202",
        "DEMO-VEN-203",
        "DEMO-VEN-204",
        "DEMO-VEN-205",
        "DEMO-VEN-206",
    ]
    assert {scenario.channel for scenario in scenarios} == {
        "app",
        "ecommerce",
        "loja_fisica",
        "shopee",
        "mercado_livre",
        "amazon",
    }
    assert sum(
        (scenario.items[0][1] for scenario in scenarios), Decimal("0")
    ) == Decimal("9")
    assert all(
        scenario.order_id for scenario in scenarios if scenario.channel != "loja_fisica"
    )


def test_demo_operacional_fixed_payables_cover_finance_and_break_even():
    payables = build_fixed_payables()
    category_keys = {payable.category_key for payable in payables}

    assert category_keys >= {
        "compra_mercadorias",
        "comissoes_vendas",
        "folha_operacional",
        "aluguel_loja",
        "energia",
        "impostos",
        "marketing",
    }
    assert any(payable.paid for payable in payables)
    assert any(not payable.paid for payable in payables)
    assert not next(
        payable for payable in payables if payable.category_key == "compra_mercadorias"
    ).affects_dre
    assert not next(
        payable for payable in payables if payable.category_key == "impostos"
    ).affects_dre


def test_demo_operacional_has_tax_and_commission_defaults():
    from app.scripts.seed_demo_operacional import (
        DEFAULT_COMMISSION_PERCENT,
        DEFAULT_TAX_PERCENT,
        _PAYMENT_PROFILES,
    )

    assert DEFAULT_TAX_PERCENT == Decimal("6.25")
    assert DEFAULT_COMMISSION_PERCENT == Decimal("4.00")
    assert _PAYMENT_PROFILES["credito"]["label"] == "Cartao de credito"
    assert _PAYMENT_PROFILES["debito"]["label"] == "Cartao de debito"


def test_product_pool_ignores_demo_fallback_when_real_catalog_exists(monkeypatch):
    from app.scripts import seed_demo_operacional_catalog

    executed_queries = []

    class FakeDb:
        def execute(self, *args, **kwargs):
            return None

    def fake_scalar(db, sql, params):
        if "codigo NOT ILIKE 'DEMO-%'" in sql:
            return 4
        return 4

    def fake_all_mappings(db, sql, params):
        executed_queries.append(sql)
        return []

    monkeypatch.setattr(seed_demo_operacional_catalog, "_scalar", fake_scalar)
    monkeypatch.setattr(
        seed_demo_operacional_catalog, "_all_mappings", fake_all_mappings
    )

    seed_demo_operacional_catalog._product_pool(
        FakeDb(), tenant_id="tenant-demo", user_id=10
    )

    assert executed_queries
    assert "codigo NOT ILIKE 'DEMO-%'" in executed_queries[0]


def test_product_pool_deactivates_demo_fallback_when_real_catalog_exists(monkeypatch):
    from app.scripts import seed_demo_operacional_catalog

    executed_queries = []

    class FakeDb:
        def execute(self, query, params=None):
            executed_queries.append(str(query))
            return None

    monkeypatch.setattr(
        seed_demo_operacional_catalog, "_ensure_fallback_products", lambda *a, **k: None
    )
    monkeypatch.setattr(
        seed_demo_operacional_catalog, "_has_enough_real_products", lambda *a, **k: True
    )
    monkeypatch.setattr(
        seed_demo_operacional_catalog, "_all_mappings", lambda *a, **k: []
    )

    seed_demo_operacional_catalog._product_pool(
        FakeDb(), tenant_id="tenant-demo", user_id=10
    )

    assert any(
        "DEMO-RACAO-10KG" in sql
        and "DEMO-MARGEM-VERDE" not in sql
        and "ativo = false" in sql
        for sql in executed_queries
    )


def test_product_pool_assigns_curated_prices_to_real_catalog(monkeypatch):
    from app.scripts import seed_demo_operacional_catalog

    updates = []

    class FakeDb:
        def execute(self, query, params=None):
            updates.append(params or {})
            return None

    products = [
        {
            "id": idx + 1,
            "codigo": f"REAL-{idx + 1}",
            "nome": f"Racao Real {idx + 1}",
            "preco_venda": Decimal("49.90"),
            "preco_custo": Decimal("24.90"),
            "estoque_atual": Decimal("0"),
        }
        for idx in range(8)
    ]

    monkeypatch.setattr(
        seed_demo_operacional_catalog, "_ensure_fallback_products", lambda *a, **k: None
    )
    monkeypatch.setattr(
        seed_demo_operacional_catalog, "_has_enough_real_products", lambda *a, **k: True
    )
    monkeypatch.setattr(
        seed_demo_operacional_catalog, "_all_mappings", lambda *a, **k: products
    )

    pool = seed_demo_operacional_catalog._product_pool(
        FakeDb(), tenant_id="tenant-demo", user_id=10
    )

    assert len({product["preco_venda"] for product in pool}) >= 6
    assert Decimal("49.90") not in {product["preco_venda"] for product in pool[:6]}


def test_product_pool_normalizes_demo_catalog_page_size(monkeypatch):
    from app.scripts import seed_demo_operacional_catalog

    executed_queries = []

    class FakeDb:
        def execute(self, *args, **kwargs):
            return None

    monkeypatch.setattr(
        seed_demo_operacional_catalog, "_ensure_fallback_products", lambda *a, **k: None
    )
    monkeypatch.setattr(
        seed_demo_operacional_catalog, "_has_enough_real_products", lambda *a, **k: True
    )

    def fake_all_mappings(db, sql, params):
        executed_queries.append(sql)
        return []

    monkeypatch.setattr(
        seed_demo_operacional_catalog, "_all_mappings", fake_all_mappings
    )

    seed_demo_operacional_catalog._product_pool(
        FakeDb(), tenant_id="tenant-demo", user_id=10
    )

    assert executed_queries
    assert "LIMIT 50" in executed_queries[0]


def test_demo_price_profile_respects_ration_package_size():
    from app.scripts.seed_demo_operacional_catalog import (
        _demo_price_profile_for_product,
    )

    cost_20kg, price_20kg = _demo_price_profile_for_product(
        {"nome": "Racao Special Dog Junior 20kg"}, 0
    )
    cost_15kg, price_15kg = _demo_price_profile_for_product(
        {"nome": "Racao Bionatural Prime Adultos 15kg"}, 1
    )
    cost_2kg, price_2kg = _demo_price_profile_for_product(
        {"nome": "Racao Senior Racas Pequenas 2,5kg"}, 2
    )
    _cost_snack, price_snack = _demo_price_profile_for_product(
        {"nome": "Petisco Natural 250g"}, 3
    )

    assert price_20kg >= Decimal("199.90")
    assert price_15kg >= Decimal("169.90")
    assert price_2kg < price_15kg
    assert price_snack < Decimal("70.00")
    assert cost_20kg < price_20kg
    assert cost_15kg < price_15kg


def test_ensure_person_can_activate_commission_partner(monkeypatch):
    from app.scripts import seed_demo_operacional_support

    executed = []

    class FakeDb:
        def execute(self, query, params=None):
            executed.append((str(query), params or {}))

    def fake_scalar(db, sql, params):
        if "SELECT id FROM clientes" in sql:
            return 44
        raise AssertionError(sql)

    monkeypatch.setattr(seed_demo_operacional_support, "_scalar", fake_scalar)

    person_id = seed_demo_operacional_support._ensure_person(
        FakeDb(),
        tenant_id="tenant-demo",
        user_id=10,
        code="DEMO-FUNC-001",
        name="Beatriz Vendedora Demo",
        kind="funcionario",
        email="beatriz@demo.corepet.com.br",
        phone="(11) 90000-0000",
        address="Rua Demo",
        number="10",
        district="Centro",
        city="Sao Paulo",
        state="SP",
        controla_rh=True,
        commission_partner=True,
    )

    assert person_id == 44
    assert executed
    sql, params = executed[0]
    assert "parceiro_ativo = :commission_partner" in sql
    assert params["commission_partner"] is True


def test_ensure_person_persists_supplier_legal_identity(monkeypatch):
    from app.scripts import seed_demo_operacional_support

    executed = []

    class FakeDb:
        def execute(self, query, params=None):
            executed.append((str(query), params or {}))

    monkeypatch.setattr(
        seed_demo_operacional_support,
        "_scalar",
        lambda db, sql, params: 55 if "SELECT id FROM clientes" in sql else None,
    )

    person_id = seed_demo_operacional_support._ensure_person(
        FakeDb(),
        tenant_id="tenant-demo",
        user_id=10,
        code="DEMO-FOR-001",
        name="Distribuidora Pet Brasil",
        kind="fornecedor",
        email="compras.demo@corepet.com.br",
        phone="(11) 3333-0101",
        address="Rua Demo",
        number="10",
        district="Centro",
        city="Sao Paulo",
        state="SP",
        cnpj="11.222.333/0001-81",
        razao_social="Distribuidora Pet Brasil Demo LTDA",
        nome_fantasia="Distribuidora Pet Brasil",
        responsavel="Marina Compras Demo",
        inscricao_estadual="ISENTO",
    )

    assert person_id == 55
    sql, params = executed[0]
    assert "cnpj = :cnpj" in sql
    assert params["tipo_pessoa"] == "PJ"
    assert params["cnpj"] == "11.222.333/0001-81"
    assert params["responsavel"] == "Marina Compras Demo"


def test_demo_operacional_blocks_production_apply_without_override():
    with pytest.raises(ValueError, match="production/prod"):
        assert_safe_environment(
            apply=True,
            environment="production",
            allow_production_apply=False,
        )

    assert_safe_environment(
        apply=True,
        environment="development",
        allow_production_apply=False,
    )


def test_demo_operacional_money_rounds_to_cents():
    assert money("10.005") == Decimal("10.01")
    assert money(Decimal("10")) == Decimal("10.00")


def test_demo_online_pickup_uses_checkout_keyword_generator(monkeypatch):
    from app.routes import ecommerce_checkout_support
    from app.scripts.seed_demo_operacional_sales_core import _online_pickup_details

    scenario = next(
        scenario
        for scenario in build_demo_scenarios()
        if scenario.pickup_type == "app_loja"
    )
    monkeypatch.setattr(
        ecommerce_checkout_support,
        "_gerar_palavra_chave_retirada",
        lambda: "patinha",
    )

    assert _online_pickup_details(scenario) == ("app_loja", "patinha")
