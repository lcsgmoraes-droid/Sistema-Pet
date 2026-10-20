from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_user_and_tenant
from app.db import get_session
from app.ifood_integration_models import IfoodMerchantConfig
from app.integrations.ifood.catalog import build_catalog_item
from app.integrations.ifood.management import build_management_item, calculate_margin
from app.produtos.schemas import ProdutoCreate, ProdutoUpdate
from app.routes.ifood_integration_routes import router
from app.tenancy.context import set_current_tenant, tenant_context


def product(**overrides):
    values = dict(
        id=1,
        codigo="PET-01",
        nome="Racao 3 kg",
        codigo_barras="7891234567890",
        tipo="produto",
        tipo_produto="SIMPLES",
        ativo=True,
        situacao=True,
        is_parent=False,
        is_sellable=True,
        unidade="UN",
        anunciar_ifood=True,
        ifood_pausado=False,
        preco_venda=100,
        preco_custo=60,
        preco_ifood=None,
        preco_app=250,
        preco_ecommerce=300,
        preco_promocional=1,
        imagem_principal="/foto.jpg",
        descricao_curta="Alimento completo",
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def config(**overrides):
    values = dict(
        default_markup_percent=10,
        stock_safety=0,
        commission_merchant_percent=10,
        commission_ifood_percent=20,
        payment_fee_percent=2,
        tax_percent=5,
        additional_unit_cost=3,
        target_margin_percent=30,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def test_specific_price_is_exact_and_erp_rule_ignores_other_channels():
    inherited = build_management_item(product(), config(), available_stock=4)
    specific = build_management_item(
        product(preco_ifood=120), config(), available_stock=4
    )
    assert inherited["regular_price"] == 110
    assert specific["regular_price"] == specific["effective_price"] == 120
    assert specific["price_source"] == "especifico"
    assert specific["status"] == "pronto_para_envio"
    assert specific["sync_status"] == "nao_enviado"
    assert product(preco_ifood=120).preco_ifood == 120


def test_margin_uses_current_price_both_modalities_and_explicit_zero_fees():
    margin = calculate_margin(product(), config(), 100, "MERCHANT")
    assert margin["contribution"] == 20 and margin["percent"] == 20
    assert margin["below_target"] is True
    assert calculate_margin(product(), config(), 100, "IFOOD")["contribution"] == 10
    free = config(
        commission_merchant_percent=0,
        payment_fee_percent=0,
        tax_percent=0,
        additional_unit_cost=0,
        target_margin_percent=0,
    )
    assert calculate_margin(product(), free, 100, "MERCHANT")["contribution"] == 40
    unknown = calculate_margin(
        product(), config(payment_fee_percent=None), 100, "MERCHANT"
    )
    assert unknown["calculated"] is False and unknown["contribution"] is None
    assert "Taxa de pagamento" in unknown["missing"]
    assert (
        calculate_margin(product(preco_custo=0), free, 100, "MERCHANT")["calculated"]
        is False
    )
    rounded = calculate_margin(
        product(),
        config(
            commission_merchant_percent=10,
            payment_fee_percent=10,
            tax_percent=10,
            additional_unit_cost=0,
        ),
        100.05,
        "MERCHANT",
    )
    assert rounded["commission"] == rounded["payment_fee"] == rounded["tax"] == 10.01
    assert rounded["contribution"] == 10.02


def test_incomplete_ifood_does_not_prevent_saving_valid_product_schema():
    data = dict(
        codigo="NEW",
        nome="Racao",
        preco_venda=20,
        anunciar_ifood=True,
        preco_ifood=0,
        preco_ifood_promo=25,
    )
    assert ProdutoCreate(**data).anunciar_ifood is True
    assert ProdutoUpdate(**data).preco_ifood == 0
    item = build_management_item(
        product(**{k: v for k, v in data.items() if k != "codigo"}),
        config(),
        available_stock=3,
    )
    assert not item["eligible"] and item["status"] == "pendente"
    assert {p["kind"] for p in item["pending"]} >= {"bloqueio", "rentabilidade"}


def test_promotion_updates_contribution_only_inside_its_own_window():
    now = datetime.now(timezone.utc)
    p = product(
        preco_ifood=100,
        preco_ifood_promo=90,
        preco_ifood_promo_inicio=now - timedelta(hours=1),
        preco_ifood_promo_fim=now + timedelta(hours=1),
    )
    current = build_management_item(p, config(), available_stock=2, now=now)
    ended = build_management_item(
        p, config(), available_stock=2, now=now + timedelta(days=1)
    )
    assert current["promotion_active"] and current["effective_price"] == 90
    assert current["margins"]["MERCHANT"]["contribution"] == 11.7
    assert ended["effective_price"] == 100 and not ended["promotion_active"]
    assert ended["margins"]["MERCHANT"]["contribution"] == 20
    p.preco_ifood_promo_fim = now - timedelta(days=2)
    invalid = build_management_item(p, config(), available_stock=2, now=now)
    assert any(issue["code"] == "promo_datas" for issue in invalid["pending"])
    assert not invalid["eligible"]


@pytest.mark.parametrize(
    "offset,active,price,expected_next",
    [
        (timedelta(milliseconds=-1), False, 150, "2026-10-20T18:00:00Z"),
        (timedelta(0), True, 120, "2026-10-20T18:02:00.001000Z"),
        (timedelta(minutes=1), True, 120, "2026-10-20T18:02:00.001000Z"),
        (timedelta(minutes=2), True, 120, "2026-10-20T18:02:00.001000Z"),
        (timedelta(minutes=2, microseconds=1), False, 150, None),
    ],
)
def test_promotion_refresh_metadata_matches_server_clock_and_margin(
    offset, active, price, expected_next
):
    start = datetime(2026, 10, 20, 18, tzinfo=timezone.utc)
    now = start + offset
    item = build_management_item(
        product(
            preco_ifood=150,
            preco_ifood_promo=120,
            preco_ifood_promo_inicio=start,
            preco_ifood_promo_fim=start + timedelta(minutes=2),
        ),
        config(),
        available_stock=4,
        now=now,
    )
    assert item["evaluated_at"] == now.isoformat().replace("+00:00", "Z")
    assert item["next_price_change_at"] == expected_next
    assert item["promotion_active"] is active and item["effective_price"] == price
    assert item["margins"]["MERCHANT"]["contribution"] == (36.6 if active else 61.5)
    assert item["margins"]["IFOOD"]["contribution"] == (24.6 if active else 46.5)
    assert any(p["code"] == "margem_abaixo_meta" for p in item["pending"]) is active
    assert item["sync_status"] == "nao_enviado"


@pytest.mark.parametrize(
    "overrides",
    [
        {"preco_ifood_promo": None},
        {"preco_ifood_promo": 0},
        {"preco_ifood_promo": 150},
        {"preco_ifood_promo": 145},
        {"preco_ifood_promo_fim": "2026-10-20T17:00:00Z"},
    ],
)
def test_invalid_promotion_does_not_schedule_automatic_price_refresh(overrides):
    fields = dict(
        preco_ifood=150,
        preco_ifood_promo=120,
        preco_ifood_promo_inicio="2026-10-20T18:00:00Z",
        preco_ifood_promo_fim="2026-10-20T19:00:00Z",
    )
    item = build_management_item(
        product(**(fields | overrides)),
        config(),
        available_stock=4,
        now=datetime(2026, 10, 20, 17, tzinfo=timezone.utc),
    )
    assert item["next_price_change_at"] is None
    assert item["effective_price"] == 150 and not item["promotion_active"]


def test_refresh_metadata_normalizes_naive_brasilia_and_open_ended_promotion():
    start = datetime(2026, 10, 20, 15)
    p = product(preco_ifood=150, preco_ifood_promo=120, preco_ifood_promo_inicio=start)
    before = build_management_item(
        p,
        config(),
        available_stock=4,
        now=datetime(2026, 10, 20, 17, tzinfo=timezone.utc),
    )
    assert before["next_price_change_at"] == "2026-10-20T18:00:00Z"
    active = build_management_item(
        p,
        config(),
        available_stock=4,
        now=datetime(2026, 10, 20, 18, tzinfo=timezone.utc),
    )
    assert active["promotion_active"] and active["next_price_change_at"] is None
    none = build_management_item(product(), config(), available_stock=4)
    assert none["next_price_change_at"] is None


def test_pause_survives_restock_and_unready_cost_is_not_publication_blocker():
    paused = build_management_item(
        product(ifood_pausado=True), config(), available_stock=100
    )
    assert paused["status"] == "pausado" and paused["selected"]
    no_cost = build_management_item(
        product(preco_custo=None), config(), available_stock=100
    )
    assert no_cost["eligible"] and not no_cost["margins"]["MERCHANT"]["calculated"]
    assert (
        build_management_item(product(), config(), available_stock=0)["status"]
        == "sem_estoque"
    )
    assert not build_management_item(
        product(e_granel=True), config(), available_stock=10
    )["eligible"]


def test_external_catalog_uses_only_selected_ifood_price_and_available_stock():
    p = product(
        preco_ifood=50,
        estoque_atual=100,
        ifood_available_stock=3,
        anunciar_ecommerce=False,
    )
    result = build_catalog_item(p, source="ifood", markup_percent=10, stock_safety=1)
    assert result.payload["prices"]["price"] == 50
    assert result.payload["inventory"]["stock"] == 2
    p.anunciar_ifood = False
    assert build_catalog_item(p, source="ifood").payload is None


def test_naive_promotion_dates_are_brasilia_and_normalized_for_storage():
    schema = ProdutoUpdate(
        preco_ifood_promo_inicio="2026-10-19T09:00:00",
        preco_ifood_promo_fim="2026-10-19T10:00:00",
    )
    assert schema.preco_ifood_promo_inicio.isoformat() == "2026-10-19T12:00:00+00:00"
    p = product(
        preco_ifood=100, preco_ifood_promo=90, **schema.model_dump(exclude_unset=True)
    )
    assert build_management_item(
        p,
        config(),
        available_stock=2,
        now=datetime(2026, 10, 19, 12, 30, tzinfo=timezone.utc),
    )["promotion_active"]
    assert not build_management_item(
        p,
        config(),
        available_stock=2,
        now=datetime(2026, 10, 19, 11, 30, tzinfo=timezone.utc),
    )["promotion_active"]


@pytest.fixture
def api(monkeypatch):
    import app.db.base  # noqa: F401
    from app.db import Base
    from app.produtos_models import (
        Produto,
        Categoria,
        Marca,
        Departamento,
        ProdutoKitComponente,
    )
    from app.pedido_integrado_item_models import PedidoIntegradoItem
    import app.pedido_integrado_models  # noqa: F401
    from app.security import permissions_decorator

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(
        engine,
        tables=[
            model.__table__
            for model in (
                Produto,
                Categoria,
                Marca,
                Departamento,
                IfoodMerchantConfig,
                PedidoIntegradoItem,
                ProdutoKitComponente,
            )
        ],
    )
    db = Session(engine)
    tenant, foreign = uuid4(), uuid4()
    first = Produto(
        tenant_id=tenant,
        user_id=1,
        codigo="A",
        nome="Racao A",
        preco_venda=100,
        preco_custo=60,
        estoque_atual=10,
        anunciar_ifood=True,
    )
    other = Produto(
        tenant_id=foreign,
        user_id=1,
        codigo="B",
        nome="Racao B",
        preco_venda=100,
        preco_custo=60,
        estoque_atual=5,
        anunciar_ifood=True,
    )
    with tenant_context(tenant):
        db.add(first)
        db.commit()
    with tenant_context(foreign):
        db.add(other)
        db.commit()
    set_current_tenant(tenant)
    state = dict(
        tenant=tenant, allow=True, admin=True, configure=True, denied_permissions=set()
    )
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_session] = lambda: db
    app.dependency_overrides[get_current_user_and_tenant] = lambda: (
        SimpleNamespace(id=1, is_admin=state["admin"]),
        state["tenant"],
    )

    def permission(*args, **kwargs):
        if (
            not state["allow"]
            or args[2] in state["denied_permissions"]
            or (args[2] == "configuracoes.editar" and not state["configure"])
        ):
            raise HTTPException(status_code=403, detail="Sem permissao")

    monkeypatch.setattr(permissions_decorator, "check_permission", permission)
    from app.security import permissions_service

    monkeypatch.setattr(permissions_service, "check_permission", permission)
    with TestClient(app) as client:
        yield SimpleNamespace(
            client=client,
            db=db,
            state=state,
            first=first,
            other=other,
            tenant=tenant,
            foreign=foreign,
            engine=engine,
        )
    db.close()
    engine.dispose()


def test_catalog_preview_and_permission_are_tenant_scoped_without_persistence(api):
    client = api.client
    response = client.get("/integracoes/ifood/catalogo/gestao")
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["product_id"] == api.first.id
    path = "/integracoes/ifood/catalogo/produto/preview"
    assert client.post(path, json={"produto": {"id": api.other.id}}).status_code == 404
    response = client.post(
        path, json={"produto": {"id": api.first.id, "preco_ifood": 99}}
    )
    assert response.status_code == 200, response.text
    assert response.json()["regular_price"] == 99
    assert api.first.preco_ifood is None
    api.state["allow"] = False
    assert client.get("/integracoes/ifood/catalogo/gestao").status_code == 403
    assert client.post(path, json={"produto": {"id": api.first.id}}).status_code == 403


def test_catalog_clock_covers_hidden_products_filters_pages_and_exact_tenant_item(
    api, monkeypatch
):
    from app.integrations.ifood import pricing
    from app.routes import ifood_integration_routes as routes

    start = datetime(2026, 10, 20, 18, tzinfo=timezone.utc)
    end = start + timedelta(minutes=2)

    class ServerClock(datetime):
        current = start - timedelta(minutes=1)

        @classmethod
        def now(cls, tz=None):
            return (
                cls.current.astimezone(tz) if tz else cls.current.replace(tzinfo=None)
            )

    monkeypatch.setattr(routes, "datetime", ServerClock)
    monkeypatch.setattr(pricing, "datetime", ServerClock)
    api.first.preco_ifood = 150
    api.first.preco_ifood_promo = 120
    # SQLite nao preserva timezone; nesta fixture gravamos a forma legada
    # naive Brasilia, que o resolvedor normaliza (Postgres preserva o offset).
    brasilia = timezone(timedelta(hours=-3))
    api.first.preco_ifood_promo_inicio = start.astimezone(brasilia).replace(tzinfo=None)
    api.first.preco_ifood_promo_fim = end.astimezone(brasilia).replace(tzinfo=None)
    api.first.imagem_principal = "/foto.jpg"
    api.first.descricao_curta = "Alimento completo"
    api.db.add(IfoodMerchantConfig(tenant_id=api.tenant, **vars(config())))
    api.db.commit()
    # Outra empresa tem uma mudanca anterior, que nao pode vazar no agendamento.
    with tenant_context(api.foreign):
        api.other.preco_ifood = 150
        api.other.preco_ifood_promo = 120
        api.other.preco_ifood_promo_inicio = (
            (start - timedelta(seconds=30)).astimezone(brasilia).replace(tzinfo=None)
        )
        api.other.preco_ifood_promo_fim = end.astimezone(brasilia).replace(tzinfo=None)
        api.db.commit()
    path = "/integracoes/ifood/catalogo/gestao"
    hidden = api.client.get(
        path, params={"q": "sem correspondencia", "filtro": "pendencias", "offset": 30}
    ).json()
    assert hidden["items"] == [] and hidden["total"] == 0
    assert hidden["summary"]["total"] == 1 and hidden["summary"]["issues"] == 0
    assert hidden["evaluated_at"] == "2026-10-20T17:59:00Z"
    assert hidden["next_price_change_at"] == "2026-10-20T18:00:00Z"
    outside_page = api.client.get(path, params={"offset": 1, "limit": 1}).json()
    assert outside_page["items"] == [] and outside_page["total"] == 1
    assert outside_page["next_price_change_at"] == hidden["next_price_change_at"]
    before = api.client.get(path, params={"filtro": "pendencias"}).json()
    assert before["items"] == [] and before["next_price_change_at"]

    ServerClock.current = start
    during = api.client.get(path, params={"filtro": "pendencias"}).json()
    item = during["items"][0]
    assert during["summary"]["issues"] == during["total"] == 1
    assert item["product_id"] == api.first.id and item["effective_price"] == 120
    assert item["evaluated_at"] == during["evaluated_at"] == "2026-10-20T18:00:00Z"
    assert item["next_price_change_at"] == during["next_price_change_at"]
    assert during["next_price_change_at"] == "2026-10-20T18:02:00.001000Z"
    exact = api.client.get(path, params={"product_id": api.first.id, "limit": 1}).json()
    assert exact["items"][0]["product_id"] == api.first.id
    foreign = api.client.get(path, params={"product_id": api.other.id}).json()
    assert foreign["items"] == [] and foreign["total"] == 0
    assert foreign["summary"] == during["summary"]
    assert api.client.get(path, params={"product_id": 0}).status_code == 422

    # As duas previews recebem o mesmo contrato temporal, sem gravar preco ou datas.
    for preview_path, payload in (
        (
            "/integracoes/ifood/catalogo/produto/preview",
            {"produto": {"id": api.first.id}},
        ),
        (
            "/integracoes/ifood/catalogo/produto/simular-preco",
            {"product_id": api.first.id, "preco_ifood": 160},
        ),
    ):
        response = api.client.post(preview_path, json=payload)
        assert response.status_code == 200, response.text
        preview = response.json()
        assert preview["effective_price"] == 120
        assert preview["evaluated_at"] == during["evaluated_at"]
        assert preview["next_price_change_at"] == during["next_price_change_at"]
    api.db.expire_all()
    assert api.first.preco_ifood == 150 and api.first.preco_ifood_promo == 120
    assert pricing.aware(api.first.preco_ifood_promo_inicio) == start
    assert pricing.aware(api.first.preco_ifood_promo_fim) == end

    ServerClock.current = end + timedelta(milliseconds=1)
    after = api.client.get(path, params={"filtro": "pendencias"}).json()
    assert after["items"] == [] and after["summary"]["issues"] == 0
    assert after["next_price_change_at"] is None
    saved = api.client.get(path, params={"product_id": api.first.id}).json()["items"][0]
    assert saved["regular_price"] == saved["saved_specific_price"] == 150
    assert saved["effective_price"] == 150 and not saved["promotion_active"]
    assert saved["sync_status"] == "nao_enviado"


def test_config_partial_update_keeps_connection_fields_and_other_tenant(api):
    merchant = str(uuid4())
    with tenant_context(api.tenant):
        api.db.add(
            IfoodMerchantConfig(
                tenant_id=api.tenant,
                merchant_id=merchant,
                active=True,
                catalog_source="erp",
                default_markup_percent=12,
                stock_safety=2,
                status="connected",
            )
        )
        api.db.commit()
    with tenant_context(api.foreign):
        api.db.add(
            IfoodMerchantConfig(tenant_id=api.foreign, default_markup_percent=50)
        )
        api.db.commit()
    response = api.client.put(
        "/integracoes/ifood/config",
        json={"payment_fee_percent": 0, "tax_percent": None},
    )
    assert response.status_code == 200, response.text
    saved = response.json()["config"]
    assert saved["merchant_id"] == merchant and saved["active"] is True
    assert saved["catalog_source"] == "erp" and saved["default_markup_percent"] == 12
    assert saved["status"] == "connected" and saved["payment_fee_percent"] == 0
    assert saved["tax_percent"] is None and saved["additional_unit_cost"] is None
    with tenant_context(api.foreign):
        assert (
            api.db.query(IfoodMerchantConfig)
            .filter_by(tenant_id=api.foreign)
            .one()
            .default_markup_percent
            == 50
        )
    api.state["admin"] = False
    assert (
        api.client.put(
            "/integracoes/ifood/config", json={"payment_fee_percent": 2}
        ).status_code
        == 403
    )


def test_price_calculator_uses_saved_erp_inputs_and_never_persists(api):
    api.db.add(IfoodMerchantConfig(tenant_id=api.tenant, **vars(config())))
    api.first.preco_ifood = 100
    api.db.commit()
    api.state["denied_permissions"] = {"produtos.editar", "configuracoes.editar"}
    route = "/integracoes/ifood/catalogo/produto/simular-preco"
    payload = {"product_id": api.first.id, "preco_ifood": 150}
    response = api.client.post(route, json=payload)
    assert response.status_code == 200, response.text
    item = response.json()
    assert item["saved_specific_price"] == 100 and item["effective_price"] == 150
    assert item["regular_price"] == 150 and item["available_stock"] == 10
    assert item["margins"]["MERCHANT"]["contribution"] == 61.5
    assert item["margins"]["IFOOD"]["contribution"] == 46.5
    assert not item["margins"]["MERCHANT"]["below_target"]
    assert not item["margins"]["IFOOD"]["below_target"]
    assert not any(p["code"] == "margem_abaixo_meta" for p in item["pending"])
    api.db.expire_all()
    assert api.first.preco_ifood == 100 and api.first.preco_custo == 60
    assert api.first.preco_venda == 100 and api.first.estoque_atual == 10
    saved = api.client.get("/integracoes/ifood/catalogo/gestao").json()["items"][0]
    assert saved["saved_specific_price"] == saved["regular_price"] == 100
    assert any(p["code"] == "margem_abaixo_meta" for p in saved["pending"])
    zero = api.client.post(route, json=payload | {"preco_ifood": 0}).json()
    assert zero["status"] == "pendente" and not zero["eligible"]
    assert zero["regular_price"] == 0 and zero["saved_specific_price"] == 100
    inherited = api.client.post(route, json=payload | {"preco_ifood": None}).json()
    assert (
        inherited["price_source"] == "regra_loja" and inherited["regular_price"] == 110
    )
    assert inherited["saved_specific_price"] == 100
    assert api.client.post(route, json=payload | {"preco_custo": 1}).status_code == 422
    assert api.client.post(route, json={"product_id": api.first.id}).status_code == 422
    assert (
        api.client.post(route, json=payload | {"product_id": api.other.id}).status_code
        == 404
    )
    api.state["denied_permissions"].add("produtos.visualizar")
    assert api.client.post(route, json=payload).status_code == 403


def test_price_calculator_keeps_existing_promotion_effective_after_reload(api):
    api.db.add(IfoodMerchantConfig(tenant_id=api.tenant, **vars(config())))
    api.first.preco_ifood = 100
    api.first.preco_ifood_promo = 90
    api.db.commit()
    response = api.client.post(
        "/integracoes/ifood/catalogo/produto/simular-preco",
        json={"product_id": api.first.id, "preco_ifood": 150},
    )
    assert response.status_code == 200, response.text
    item = response.json()
    assert item["saved_specific_price"] == 100 and item["regular_price"] == 150
    assert item["effective_price"] == 90 and item["promotion_active"]
    assert item["margins"]["MERCHANT"]["contribution"] == 11.7
    api.db.expire_all()
    saved = api.client.get("/integracoes/ifood/catalogo/gestao").json()["items"][0]
    assert saved["regular_price"] == saved["saved_specific_price"] == 100
    assert saved["effective_price"] == 90 and saved["promotion_active"]


def test_price_calculator_uses_component_cost_and_reserved_stock_for_virtual_kit(
    api, monkeypatch
):
    from app.estoque_reserva_service import EstoqueReservaService
    from app.produtos_models import Produto, ProdutoKitComponente

    kit = Produto(
        tenant_id=api.tenant,
        user_id=1,
        codigo="CALC-KIT",
        nome="Kit calculadora",
        tipo_produto="KIT",
        tipo_kit="VIRTUAL",
        preco_custo=1,
        preco_venda=200,
        preco_ifood=200,
        anunciar_ifood=True,
    )
    api.db.add(kit)
    api.db.flush()
    api.db.add(
        ProdutoKitComponente(
            tenant_id=api.tenant,
            kit_id=kit.id,
            produto_componente_id=api.first.id,
            quantidade=2,
        )
    )
    api.db.add(IfoodMerchantConfig(tenant_id=api.tenant, **vars(config())))
    api.db.commit()
    monkeypatch.setattr(
        EstoqueReservaService,
        "mapa_reservas_ativas_por_produto",
        staticmethod(lambda *_: {api.first.id: 3}),
    )
    response = api.client.post(
        "/integracoes/ifood/catalogo/produto/simular-preco",
        json={"product_id": kit.id, "preco_ifood": 250},
    )
    assert response.status_code == 200, response.text
    item = response.json()
    assert item["available_stock"] == 3
    assert item["margins"]["MERCHANT"]["cost"] == 120
    assert item["saved_specific_price"] == 200


def test_ifood_existing_revision_merges_with_current_main_without_reapplying_it():
    from pathlib import Path
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    backend = Path(__file__).resolve().parents[2]
    alembic_config = Config(str(backend / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(backend / "alembic"))
    script = ScriptDirectory.from_config(alembic_config)
    assert script.get_heads() == ["zzzzm20261020a1"]
    assert script.get_revision("zzzzg20261019a1").down_revision == "zzzzf20261019a1"
    assert script.get_revision("zzzzl20261020a1").down_revision == "zzzzk20261020a1"
    assert script.get_revision("zzzzm20261020a1").down_revision == (
        "zzzzg20261019a1",
        "zzzzl20261020a1",
    )
    steps = script._upgrade_revs("head", "zzzzg20261019a1")
    revisions = {step.revision.revision for step in steps}
    assert revisions == {
        "zzzzh20261019a1",
        "zzzzi20261019a1",
        "zzzzj20261019a1",
        "zzzzk20261020a1",
        "zzzzl20261020a1",
        "zzzzm20261020a1",
    }
    # A head sozinha nao detecta dois arquivos com o mesmo revision: Alembic
    # pode sobrescrever um deles no mapa e pular DDL ao aplicar a migration.
    import ast

    revisions_on_disk = []
    for path in (backend / "alembic" / "versions").glob("*.py"):
        module = ast.parse(path.read_text(encoding="utf-8-sig"))
        for node in module.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "revision"
                for target in node.targets
            ):
                revisions_on_disk.append(ast.literal_eval(node.value))
    assert len(revisions_on_disk) == len(set(revisions_on_disk))
    # Um banco com g+k ja aplicados ainda precisa do DDL fiscal l, uma vez.
    steps = script._upgrade_revs("head", ("zzzzg20261019a1", "zzzzk20261020a1"))
    assert [step.revision.revision for step in steps] == [
        "zzzzl20261020a1",
        "zzzzm20261020a1",
    ]


def test_catalog_settings_permission_uses_tenant_role_and_cannot_activate_provider(api):
    merchant = str(uuid4())
    api.db.add(
        IfoodMerchantConfig(
            tenant_id=api.tenant,
            merchant_id=merchant,
            active=True,
            status="connected",
            stock_safety=2,
        )
    )
    api.db.commit()
    api.state["admin"] = False
    route = "/integracoes/ifood/catalogo/configuracao"
    assert (
        api.client.get("/integracoes/ifood/catalogo/gestao").json()["can_configure"]
        is True
    )
    response = api.client.put(
        route, json={"default_markup_percent": 15, "payment_fee_percent": 0}
    )
    assert response.status_code == 200, response.text
    saved = response.json()["config"]
    assert saved["default_markup_percent"] == 15 and saved["payment_fee_percent"] == 0
    assert (
        saved["merchant_id"] == merchant
        and saved["active"]
        and saved["status"] == "connected"
    )
    assert saved["stock_safety"] == 2
    # Mesmo quem pode editar premissas locais nao pode mandar campos externos.
    for field, value in (
        ("merchant_id", str(uuid4())),
        ("active", False),
        ("catalog_source", "erp"),
    ):
        assert api.client.put(route, json={field: value}).status_code == 422
    api.state["configure"] = False
    api.state["admin"] = True
    assert (
        api.client.get("/integracoes/ifood/catalogo/gestao").json()["can_configure"]
        is False
    )
    assert api.client.put(route, json={"default_markup_percent": 99}).status_code == 403
    api.db.expire_all()
    assert (
        api.db.query(IfoodMerchantConfig)
        .filter_by(tenant_id=api.tenant)
        .one()
        .default_markup_percent
        == 15
    )


def test_stock_reserves_and_kit_capacity_use_batches(api, monkeypatch):
    from app.estoque_reserva_service import EstoqueReservaService
    from app.produtos_models import Produto, ProdutoKitComponente

    kit = Produto(
        tenant_id=api.tenant,
        user_id=1,
        codigo="KIT",
        nome="Kit",
        tipo_produto="KIT",
        tipo_kit="VIRTUAL",
        preco_venda=200,
        preco_custo=0,
        anunciar_ifood=True,
    )
    api.db.add(kit)
    api.db.flush()
    api.db.add(
        ProdutoKitComponente(
            tenant_id=api.tenant,
            kit_id=kit.id,
            produto_componente_id=api.first.id,
            quantidade=2,
        )
    )
    api.db.commit()
    monkeypatch.setattr(
        EstoqueReservaService,
        "mapa_reservas_ativas_por_produto",
        staticmethod(lambda *_: {api.first.id: 3}),
    )
    queries = []
    event.listen(
        api.engine, "before_cursor_execute", lambda *args: queries.append(args[2])
    )
    response = api.client.get("/integracoes/ifood/catalogo/gestao")
    assert response.status_code == 200, response.text
    items = {item["product_id"]: item for item in response.json()["items"]}
    assert items[api.first.id]["available_stock"] == 7
    assert items[kit.id]["available_stock"] == 3
    assert items[kit.id]["margins"]["MERCHANT"]["cost"] == 120
    assert len(queries) <= 5
    route = "/integracoes/ifood/catalogo/produto/preview"
    unchanged = api.client.post(
        route,
        json={
            "produto": {
                "id": kit.id,
                "preco_custo": 1,
                "composicao_kit": [
                    {"produto_componente_id": api.first.id, "quantidade": 2}
                ],
            }
        },
    )
    assert unchanged.status_code == 200, unchanged.text
    assert unchanged.json()["margins"]["MERCHANT"]["cost"] == 120
    assert unchanged.json()["available_stock"] == 3
    changed = api.client.post(
        route,
        json={
            "produto": {
                "id": kit.id,
                "preco_custo": 1,
                "composicao_kit": [
                    {"produto_componente_id": api.first.id, "quantidade": 4}
                ],
            }
        },
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["available_stock"] is None
    assert changed.json()["margins"]["MERCHANT"]["cost"] is None
    assert changed.json()["status"] == "pendente"
    assert (
        api.db.query(ProdutoKitComponente).filter_by(kit_id=kit.id).one().quantidade
        == 2
    )


def test_canonical_update_persists_ifood_and_shared_update_cannot_change_origin_channel(
    api, monkeypatch
):
    from app.produtos import cadastro_routes
    from app.produtos.schemas import ProdutoResponse
    from app.produtos_models import Produto
    from app.services.produto_identidade_service import INHERENT_FIELDS

    assert (
        not {
            "anunciar_ifood",
            "ifood_pausado",
            "preco_ifood",
            "preco_ifood_promo",
            "preco_ifood_promo_inicio",
            "preco_ifood_promo_fim",
        }
        & INHERENT_FIELDS
    )
    api.client.app.include_router(cadastro_routes.router, prefix="/produtos")
    access = SimpleNamespace(tenant_origem_id=api.tenant, compartilhado=False)
    monkeypatch.setattr(
        cadastro_routes.GrupoComercialEstoqueCompartilhadoService,
        "resolver_produto_catalogo",
        staticmethod(lambda *_: access),
    )
    monkeypatch.setattr(
        cadastro_routes,
        "obter_produto",
        lambda *_: ProdutoResponse(
            id=api.first.id,
            codigo="A",
            nome="Racao A",
            ativo=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            anunciar_ifood=api.first.anunciar_ifood,
            preco_ifood=api.first.preco_ifood,
        ),
    )
    response = api.client.put(
        f"/produtos/{api.first.id}",
        json={"anunciar_ifood": True, "preco_ifood": 123, "ifood_pausado": True},
    )
    assert response.status_code == 200, response.text
    api.db.expire_all()
    assert api.db.get(Produto, api.first.id).preco_ifood == 123
    access.compartilhado = True
    response = api.client.put(f"/produtos/{api.first.id}", json={"preco_ifood": 999})
    assert response.status_code == 403
    # A edicao comum continua valida sem levar configuracao iFood na gravacao.
    response = api.client.put(f"/produtos/{api.first.id}", json={"estoque_minimo": 4})
    assert response.status_code == 200, response.text
    api.db.expire_all()
    saved = api.db.get(Produto, api.first.id)
    assert (
        saved.estoque_minimo == 4 and saved.preco_ifood == 123 and saved.ifood_pausado
    )


@pytest.mark.parametrize(
    "regular,promo,expected_price,expected_error",
    [
        (1, 0.004, 1, "promo_preco"),
        (1, 0.005, 0.01, None),
        (1, 0.954, 0.95, None),
        (1, 0.955, 1, "promo_desconto"),
        (1, 0.999, 1, "promo_preco"),
    ],
)
def test_promotion_validates_the_actual_rounded_money_sent_to_catalog(
    regular, promo, expected_price, expected_error
):
    p = product(preco_ifood=regular, preco_ifood_promo=promo, ifood_available_stock=4)
    item = build_management_item(p, config(), available_stock=4)
    catalog = build_catalog_item(p, source="ifood")
    assert item["effective_price"] == expected_price
    assert item["promotion_active"] is (expected_error is None)
    assert item["eligible"] is (expected_error is None)
    assert catalog.eligible is item["eligible"]
    if expected_error:
        assert expected_error in {issue["code"] for issue in item["pending"]}
        assert catalog.payload is None
    else:
        assert catalog.payload["prices"]["promotionPrice"] == expected_price


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity", -1, 1e30, 1e300])
def test_simulation_rejects_nonfinite_and_negative_prices_without_writes(api, value):
    response = api.client.post(
        "/integracoes/ifood/catalogo/produto/simular-preco",
        json={"product_id": api.first.id, "preco_ifood": value},
    )
    assert response.status_code == 422, response.text
    api.db.expire_all()
    assert api.first.preco_ifood is None
    assert api.first.preco_venda == 100 and api.first.preco_custo == 60


@pytest.mark.parametrize(
    "field,value",
    [
        ("commission_ifood_percent", -1),
        ("commission_merchant_percent", 100.01),
        ("payment_fee_percent", "NaN"),
        ("tax_percent", "Infinity"),
        ("additional_unit_cost", -0.01),
        ("target_margin_percent", 100),
        ("stock_safety", -1),
        ("default_markup_percent", 301),
    ],
)
def test_invalid_catalog_premises_do_not_create_or_modify_configuration(
    api, field, value
):
    response = api.client.put(
        "/integracoes/ifood/catalogo/configuracao", json={field: value}
    )
    assert response.status_code == 422, response.text
    assert api.db.query(IfoodMerchantConfig).count() == 0


def test_local_previews_and_blocked_sync_never_instantiate_provider_client(
    api, monkeypatch
):
    from app.config import settings
    from app.routes import ifood_integration_routes as routes

    def forbidden_client():
        pytest.fail("Nenhuma operacao local pode abrir o cliente externo iFood")

    monkeypatch.setattr(routes, "_client", forbidden_client)
    monkeypatch.setattr(settings, "IFOOD_CATALOG_WRITE_ENABLED", False)
    for method, path, payload in (
        ("get", "/catalogo/gestao", None),
        ("get", "/catalogo/preview", None),
        ("post", "/catalogo/produto/preview", {"produto": {"id": api.first.id}}),
        (
            "post",
            "/catalogo/produto/simular-preco",
            {"product_id": api.first.id, "preco_ifood": 150},
        ),
        ("post", "/catalogo/sincronizar", {"product_ids": [api.first.id]}),
    ):
        request = getattr(api.client, method)
        response = request(
            "/integracoes/ifood" + path, **({"json": payload} if payload else {})
        )
        assert response.status_code == 200, response.text
    response = api.client.post(
        "/integracoes/ifood/catalogo/sincronizar",
        json={"dry_run": False, "confirm_send": True, "product_ids": [api.first.id]},
    )
    assert response.status_code == 409
    assert "bloqueados" in response.json()["detail"]
    api.db.expire_all()
    assert api.first.preco_ifood is None
    assert api.db.query(IfoodMerchantConfig).count() == 0
    api.state["admin"] = False
    assert (
        api.client.post("/integracoes/ifood/catalogo/sincronizar", json={}).status_code
        == 403
    )


@pytest.mark.parametrize("field", ["preco_ifood", "preco_ifood_promo"])
@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity", 1e30, 1e300])
def test_product_preview_rejects_unrepresentable_prices(api, field, value):
    response = api.client.post(
        "/integracoes/ifood/catalogo/produto/preview",
        json={"produto": {"id": api.first.id, field: value}},
    )
    assert response.status_code == 422, response.text
    api.db.expire_all()
    assert api.first.preco_ifood is None and api.first.preco_ifood_promo is None


def test_large_legacy_erp_inputs_report_pending_instead_of_crashing(api):
    api.db.add(IfoodMerchantConfig(tenant_id=api.tenant, **vars(config())))
    api.db.commit()
    for field in ("preco_venda", "preco_custo", "preco_ifood", "preco_ifood_promo"):
        response = api.client.post(
            "/integracoes/ifood/catalogo/produto/preview",
            json={"produto": {"id": api.first.id, field: 1e30}},
        )
        if field in ("preco_ifood", "preco_ifood_promo"):
            assert response.status_code == 422
            continue
        assert response.status_code == 200, response.text
        item = response.json()
        assert not item["margins"]["MERCHANT"]["calculated"]
        assert any(issue["code"] == "margem_incompleta" for issue in item["pending"])
    # Dados legados fora da faixa nao devem herdar o preco ERP silenciosamente.
    bad = build_management_item(product(preco_ifood=1e30), config(), available_stock=1)
    assert bad["regular_price"] is None and not bad["eligible"]
    bad_promo = build_management_item(
        product(preco_ifood_promo=1e30), config(), available_stock=1
    )
    assert not bad_promo["eligible"] and not bad_promo["promotion_active"]


def test_maximum_representable_promotion_end_does_not_overflow_refresh_schedule():
    item = build_management_item(
        product(
            preco_ifood=100,
            preco_ifood_promo=90,
            preco_ifood_promo_fim=datetime.max.replace(tzinfo=timezone.utc),
        ),
        config(),
        available_stock=1,
        now=datetime(2026, 10, 20, tzinfo=timezone.utc),
    )
    assert item["promotion_active"] and item["effective_price"] == 90
    assert item["next_price_change_at"] is None


def test_timezone_conversion_overflow_is_a_validation_error(api):
    response = api.client.post(
        "/integracoes/ifood/catalogo/produto/preview",
        json={
            "produto": {
                "id": api.first.id,
                "preco_ifood_promo_fim": "9999-12-31T23:59:59-03:00",
            }
        },
    )
    assert response.status_code == 422, response.text


def test_parent_type_is_blocked_even_if_legacy_boolean_flags_are_inconsistent():
    p = product(tipo_produto="PAI", is_parent=False, ifood_available_stock=4)
    item = build_management_item(p, config(), available_stock=4)
    catalog = build_catalog_item(p, source="ifood")
    assert not item["eligible"] and not catalog.eligible
    assert catalog.payload is None


def test_product_preview_permission_accepts_create_or_edit_and_denies_neither(api):
    path = "/integracoes/ifood/catalogo/produto/preview"
    payload = {"produto": {"nome": "Novo produto", "codigo": "NEW"}}
    for denied in ({"produtos.editar"}, {"produtos.criar"}):
        api.state["denied_permissions"] = denied
        response = api.client.post(path, json=payload)
        assert response.status_code == 200, response.text
        assert response.json()["product_id"] is None
    api.state["denied_permissions"] = {"produtos.criar", "produtos.editar"}
    assert api.client.post(path, json=payload).status_code == 403
    assert api.db.query(IfoodMerchantConfig).count() == 0


def test_maximum_currency_and_datetime_remain_valid_http_inputs(api):
    from app.integrations.ifood.pricing import MAX_IFOOD_MONEY

    response = api.client.post(
        "/integracoes/ifood/catalogo/produto/simular-preco",
        json={"product_id": api.first.id, "preco_ifood": MAX_IFOOD_MONEY},
    )
    assert response.status_code == 200, response.text
    assert response.json()["regular_price"] == MAX_IFOOD_MONEY
    response = api.client.post(
        "/integracoes/ifood/catalogo/produto/preview",
        json={
            "produto": {
                "id": api.first.id,
                "preco_ifood": 100,
                "preco_ifood_promo": 90,
                "preco_ifood_promo_fim": "9999-12-31T23:59:59.999999Z",
            }
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["promotion_active"]
    assert response.json()["next_price_change_at"] is None
    api.db.expire_all()
    assert api.first.preco_ifood is None and api.first.preco_ifood_promo is None
