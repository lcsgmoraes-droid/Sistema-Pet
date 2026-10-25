"""Contrato HTTP e efeitos do piloto, sem credenciais/rede/dados de producao."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.ifood_catalog_models import (
    IfoodCatalogLink,
    IfoodCatalogConfirmation,
    IfoodCatalogSubmission,
)
from app.ifood_integration_models import IfoodMerchantConfig
from app.integrations.ifood.client import IfoodClientError
from app.integrations.ifood.catalog import item_description_text
from app.produtos_catalogo_models import Produto
from app.routes import ifood_catalog_pilot_routes as routes
from app.tenancy.context import tenant_context
from tests.unit.test_ifood_management import api  # noqa: F401 - fixture canonica

EAN = "4006381333931"
OTHER_EAN = "5901234123457"
BASE = "/integracoes/ifood/catalogo/produtos"


@pytest.fixture
def setup(api, monkeypatch):  # noqa: F811 - fixture importada
    api.client.app.include_router(routes.router)
    api.first.codigo_barras = EAN
    api.first.imagem_principal = "/uploads/foto-ficticia.jpg"
    api.first.descricao_curta = "Alimento ficticio para teste local"
    api.first.unidade = "UN"
    merchant = str(uuid4())
    config = IfoodMerchantConfig(
        tenant_id=api.tenant,
        merchant_id=merchant,
        active=True,
        default_markup_percent=0,
        stock_safety=0,
    )
    api.db.add(config)
    api.db.commit()
    monkeypatch.setattr(settings, "IFOOD_CATALOG_WRITE_ENABLED", False)
    monkeypatch.setattr(
        settings, "COREPET_FRONTEND_URL", "https://fixture.example.test"
    )
    monkeypatch.setattr(routes, "_credentials_configured", lambda: True)
    calls = []

    class Client:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def ingest_items(self, merchant_id, items, **kwargs):
            calls.append((merchant_id, items, kwargs))
            return {
                "status_code": 202,
                "response": {
                    "requestId": str(uuid4()),
                    "status": "ACCEPTED",
                    "secret": "must-never-appear",
                },
            }

    monkeypatch.setattr(routes, "_client", Client)
    return SimpleNamespace(
        **vars(api),
        merchant=merchant,
        config=config,
        calls=calls,
        path=f"{BASE}/{api.first.id}",
    )


def link(s, mode="existing", **extra):
    response = s.client.put(
        s.path + "/vinculo",
        json={
            "merchant_id": s.merchant,
            "barcode": EAN,
            "mode": mode,
            "portal_checked": True,
            **extra,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def prepare(s, operation="update", fields=None):
    response = s.client.post(
        s.path + "/preparar",
        json={
            "operation": operation,
            "fields": fields if fields is not None else ["price", "stock"],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def send(s, prepared, **extra):
    return s.client.post(
        s.path + "/enviar",
        json={
            "operation": prepared["operation"],
            "fields": prepared["fields"],
            "review_token": prepared["review_token"],
            "request_key": str(uuid4()),
            "confirm_send": True,
            **extra,
        },
    )


def test_view_simulation_and_send_default_never_write_or_call_provider(setup):
    s = setup
    response = s.client.get(s.path + "/publicacao")
    assert response.status_code == 200, response.text
    first = response.json()
    assert first["snapshot_saved"]["codigo_barras"] == EAN
    assert first["last_submission"] is None and first["last_confirmation"] is None
    assert (
        first["capabilities"]["can_prepare"] and not first["capabilities"]["can_send"]
    )
    p = prepare(s)
    assert not p["eligible"] and "link_missing" in {x["code"] for x in p["pending"]}
    simulated = send(s, p, confirm_send=False)
    assert simulated.status_code == 200 and simulated.json()["dry_run"]
    assert not s.calls
    assert s.db.query(IfoodCatalogLink).count() == 0
    assert s.db.query(IfoodCatalogSubmission).count() == 0
    assert s.db.query(IfoodCatalogConfirmation).count() == 0


def test_link_existing_unselected_inactive_remote_preserves_product_and_nullable_observations(
    setup,
):
    s = setup
    s.first.anunciar_ifood = False
    s.first.estoque_atual = 0
    s.db.commit()
    view = link(s, portal_active=False, price="17.60", stock="4")
    assert view["link"]["mode"] == "existing"
    assert view["last_confirmation"]["portal_active"] is False
    assert view["last_confirmation"]["stock"] == "4.000"
    assert not s.first.anunciar_ifood and s.first.estoque_atual == 0
    assert not s.calls and not prepare(s)["eligible"]
    view = link(s)
    assert view["last_confirmation"]["price"] is None
    assert view["last_confirmation"]["stock"] is None
    assert view["last_confirmation"]["portal_active"] is None
    assert s.db.query(IfoodCatalogConfirmation).count() == 2


@pytest.mark.parametrize(
    "fields,expected",
    [
        (["price"], {"barcode": EAN, "prices": {"price": 100.0}}),
        (["stock"], {"barcode": EAN, "inventory": {"stock": 10}}),
    ],
)
def test_patch_only_chosen_fields_preserves_remote_promo_and_metadata(
    setup, monkeypatch, fields, expected
):
    s = setup
    link(s)
    s.first.preco_ifood_promo = 80
    s.db.commit()
    p = prepare(s, fields=fields)
    assert p["eligible"] and p["payload"] == expected
    monkeypatch.setattr(settings, "IFOOD_CATALOG_WRITE_ENABLED", True)
    response = send(s, p)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "accepted"
    assert s.calls == [
        (s.merchant, [expected], {"method": "PATCH", "reset_catalog": False})
    ]
    assert "promotionPrice" not in str(s.calls)
    assert "must-never-appear" not in response.text
    assert body["publication"]["last_confirmation"]["price"] is None
    assert "portal_confirmation_required" in {
        x["code"] for x in body["publication"]["pending"]
    }


def test_create_single_item_requires_absence_review_and_always_reset_false(
    setup, monkeypatch
):
    s = setup
    link(s)
    assert not prepare(s, "create")["eligible"]
    link(s, "new")
    assert not prepare(s, "update")["eligible"]
    p = prepare(s, "create")
    assert p["eligible"] and p["reset_catalog"] is False
    assert p["payload"]["details"]["description"]
    assert p["payload"]["details"]["imageUrl"].startswith("https://")
    monkeypatch.setattr(settings, "IFOOD_CATALOG_WRITE_ENABLED", True)
    response = send(s, p)
    assert response.status_code == 200
    assert len(s.calls) == 1 and len(s.calls[0][1]) == 1
    assert s.calls[0][2] == {"method": "POST", "reset_catalog": False}
    assert response.json()["publication"]["link"]["mode"] == "new"
    confirmation = s.client.post(
        s.path + "/confirmar-portal",
        json={
            "merchant_id": s.merchant,
            "barcode": EAN,
            "present": True,
            "price": "100",
            "stock": "10",
            "portal_active": True,
        },
    )
    assert confirmation.status_code == 200
    assert confirmation.json()["link"]["mode"] == "existing"
    assert confirmation.json()["last_confirmation"]["price"] == "100.00"
    assert len(s.calls) == 1


def test_request_key_replay_does_not_send_twice_or_accept_another_product(
    setup, monkeypatch
):
    s = setup
    link(s)
    p = prepare(s)
    monkeypatch.setattr(settings, "IFOOD_CATALOG_WRITE_ENABLED", True)
    key = str(uuid4())
    first = send(s, p, request_key=key)
    second = send(s, p, request_key=key)
    assert first.status_code == second.status_code == 200
    assert second.json()["replayed"] and len(s.calls) == 1
    assert s.db.query(IfoodCatalogSubmission).count() == 1
    other = send(s, p, request_key=key, review_token="a" * 64)
    assert other.status_code == 409 and len(s.calls) == 1


@pytest.mark.parametrize(
    "failure,status,code",
    [
        (
            IfoodClientError("private token URL", status_code=400),
            "error",
            "provider_rejected",
        ),
        (
            IfoodClientError("private token URL", status_code=403),
            "error",
            "provider_rejected",
        ),
        (
            IfoodClientError("private token URL", status_code=429),
            "error",
            "rate_limited",
        ),
        (
            IfoodClientError("private token URL", status_code=500),
            "uncertain",
            "transport_uncertain",
        ),
        (IfoodClientError("private token URL"), "uncertain", "transport_uncertain"),
        (TimeoutError("private token URL"), "uncertain", "transport_uncertain"),
    ],
)
def test_rejections_timeouts_and_5xx_preserve_confirmed_evidence_without_leaks(
    setup, monkeypatch, failure, status, code
):
    s = setup
    initial = link(s, price="73.90", stock="5", portal_active=True)["last_confirmation"]
    p = prepare(s)
    monkeypatch.setattr(settings, "IFOOD_CATALOG_WRITE_ENABLED", True)

    class FailingClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def ingest_items(self, *args, **kwargs):
            # A tentativa deve sobreviver a falha de processo/transporte.
            assert s.db.query(IfoodCatalogSubmission).one().status == "sending"
            raise failure

    monkeypatch.setattr(routes, "_client", FailingClient)
    response = send(s, p)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == status and body["submission"]["error_code"] == code
    assert body["publication"]["last_confirmation"] == initial
    assert "private" not in response.text and "token URL" not in response.text
    if status == "uncertain":
        assert not prepare(s)["eligible"]
        assert send(s, p).status_code == 409


@pytest.mark.parametrize("status_code", [200, 201, 204])
def test_only_202_is_accepted_and_no_other_success_is_called_published(
    setup, monkeypatch, status_code
):
    s = setup
    link(s)
    p = prepare(s)
    monkeypatch.setattr(settings, "IFOOD_CATALOG_WRITE_ENABLED", True)

    class Unexpected:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def ingest_items(self, *args, **kwargs):
            return {
                "status_code": status_code,
                "response": {
                    "requestId": "https://private.invalid/secret",
                    "message": "private",
                },
            }

    monkeypatch.setattr(routes, "_client", Unexpected)
    result = send(s, p).json()
    assert result["status"] == "uncertain"
    assert result["submission"]["provider_request_id"] is None
    assert result["submission"]["error_code"] == "unexpected_response"


def test_review_stale_price_stock_and_barcode_cannot_be_sent(setup, monkeypatch):
    s = setup
    link(s)
    p = prepare(s)
    monkeypatch.setattr(settings, "IFOOD_CATALOG_WRITE_ENABLED", True)
    s.first.preco_ifood = 120
    s.db.commit()
    assert send(s, p).status_code == 409
    p = prepare(s)
    s.first.estoque_atual = 2
    s.db.commit()
    assert send(s, p).status_code == 409
    s.first.codigo_barras = OTHER_EAN
    s.db.commit()
    view = s.client.get(s.path + "/publicacao").json()
    assert view["link"]["stale"]
    assert not prepare(s)["eligible"] and send(s, p).status_code == 409
    relink = s.client.put(
        s.path + "/vinculo",
        json={
            "merchant_id": s.merchant,
            "barcode": OTHER_EAN,
            "mode": "existing",
            "portal_checked": True,
        },
    )
    assert relink.status_code == 200 and relink.json()["link"]["revision"] == 2
    assert not s.calls


def test_product_merchant_and_permission_guards_do_not_leak_other_tenant(setup):
    s = setup
    link(s, price="73.90")
    assert s.client.get(f"{BASE}/{s.other.id}/publicacao").status_code == 404
    bad = {
        "merchant_id": str(uuid4()),
        "barcode": EAN,
        "mode": "new",
        "portal_checked": True,
    }
    assert s.client.put(s.path + "/vinculo", json=bad).status_code == 409
    s.config.merchant_id = str(uuid4())
    s.db.commit()
    body = s.client.get(s.path + "/publicacao").json()
    assert body["link"] is None and body["last_confirmation"] is None
    assert body["last_submission"] is None
    s.state["denied_permissions"].add("produtos.editar")
    assert (
        s.client.get(s.path + "/publicacao").json()["capabilities"]["can_link"] is False
    )
    assert s.client.put(s.path + "/vinculo", json=bad).status_code == 403
    s.state["denied_permissions"].add("produtos.visualizar")
    assert s.client.get(s.path + "/publicacao").status_code == 403
    assert not s.calls


def test_duplicate_barcode_preview_management_and_pilot_agree_even_unselected(setup):
    s = setup
    other = Produto(
        tenant_id=s.tenant,
        user_id=1,
        codigo="DUPLICATE",
        nome="Produto ficticio duplicado",
        codigo_barras=EAN,
        preco_venda=5,
        estoque_atual=1,
        anunciar_ifood=False,
    )
    s.db.add(other)
    s.db.commit()
    preview = s.client.get("/integracoes/ifood/catalogo/preview").json()
    assert preview["summary"]["eligible"] == 0
    management = s.client.get("/integracoes/ifood/catalogo/gestao").json()
    assert not next(
        item for item in management["items"] if item["product_id"] == s.first.id
    )["eligible"]
    assert not prepare(s)["eligible"]
    result = s.client.put(
        s.path + "/vinculo",
        json={
            "merchant_id": s.merchant,
            "barcode": EAN,
            "mode": "existing",
            "portal_checked": True,
        },
    )
    assert result.status_code == 409 and not s.calls


def test_send_rechecks_write_flag_credentials_and_active_configuration(
    setup, monkeypatch
):
    s = setup
    link(s)
    p = prepare(s)
    assert send(s, p).status_code == 409
    monkeypatch.setattr(settings, "IFOOD_CATALOG_WRITE_ENABLED", True)
    monkeypatch.setattr(routes, "_credentials_configured", lambda: False)
    assert send(s, p).status_code == 503
    monkeypatch.setattr(routes, "_credentials_configured", lambda: True)
    s.config.active = False
    s.db.commit()
    assert send(s, p).status_code == 409 and not s.calls
    assert s.db.query(IfoodCatalogSubmission).count() == 0


def test_confirmed_zero_is_not_unknown_and_history_is_visible_in_central(setup):
    s = setup
    link(s, price="0", stock="0", portal_active=False)
    view = s.client.get(s.path + "/publicacao").json()
    assert view["last_confirmation"]["price"] == "0.00"
    assert view["last_confirmation"]["stock"] == "0.000"
    item = s.client.get("/integracoes/ifood/catalogo/gestao").json()["items"][0]
    assert item["publication"]["last_confirmation"] == view["last_confirmation"]
    assert item["last_confirmed_price"] == "0.00"


def test_pause_stock_zero_partial_does_not_send_activation(setup, monkeypatch):
    s = setup
    link(s, portal_active=False)
    s.first.ifood_pausado = True
    s.db.commit()
    p = prepare(s, fields=["stock"])
    assert p["eligible"] and p["payload"] == {"barcode": EAN, "inventory": {"stock": 0}}
    monkeypatch.setattr(settings, "IFOOD_CATALOG_WRITE_ENABLED", True)
    assert send(s, p).status_code == 200
    assert "active" not in s.calls[0][1][0]


def test_orphan_sending_stays_blocked_until_manual_confirmation_and_window(
    setup, monkeypatch
):
    s = setup
    link(s)
    s.db.query(IfoodCatalogConfirmation).one().confirmed_at = datetime.now(
        timezone.utc
    ) - timedelta(hours=2)
    row = IfoodCatalogSubmission(
        tenant_id=s.tenant,
        link_id=s.db.query(IfoodCatalogLink).one().id,
        merchant_id=s.merchant,
        barcode=EAN,
        request_key=str(uuid4()),
        operation="update",
        fields=["stock"],
        payload_hash="a" * 64,
        evidence={"barcode": EAN},
        status="sending",
        actor_id=1,
        created_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    s.db.add(row)
    s.db.commit()
    assert not prepare(s)["eligible"]
    result = s.client.post(
        s.path + "/confirmar-portal",
        json={"merchant_id": s.merchant, "barcode": EAN, "present": True},
    )
    assert result.status_code == 200
    assert prepare(s)["eligible"]
    assert s.db.query(IfoodCatalogSubmission).one().status == "sending"
    assert not s.calls


@pytest.mark.parametrize(
    "extra",
    [
        {"reset_catalog": True},
        {"fields": ["promotion"]},
        {"tenant_id": str(uuid4())},
        {"product_ids": [1, 2]},
    ],
)
def test_batch_reset_unknown_fields_and_cross_tenant_inputs_are_rejected(setup, extra):
    s = setup
    response = s.client.post(
        s.path + "/preparar", json={"operation": "update", "fields": ["price"], **extra}
    )
    assert response.status_code == 422 and not s.calls


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1", "12.345", "https://secret"])
def test_portal_money_validation_is_finite_and_exact(setup, value):
    s = setup
    response = s.client.put(
        s.path + "/vinculo",
        json={
            "merchant_id": s.merchant,
            "barcode": EAN,
            "mode": "existing",
            "portal_checked": True,
            "price": value,
        },
    )
    assert response.status_code == 422
    assert s.db.query(IfoodCatalogLink).count() == 0


def test_legacy_real_writes_and_production_reset_are_blocked(setup, monkeypatch):
    s = setup
    monkeypatch.setattr(settings, "IFOOD_CATALOG_WRITE_ENABLED", True)
    path = "/integracoes/ifood/catalogo/sincronizar"
    assert (
        s.client.post(
            path,
            json={"dry_run": False, "confirm_send": True, "product_ids": [s.first.id]},
        ).status_code
        == 409
    )
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    result = s.client.post(path, json={"reset_catalog": True, "dry_run": True})
    assert result.status_code == 409 and "Reset" in result.json()["detail"]
    assert not s.calls


def test_composite_fk_prevents_cross_tenant_link_and_barcode_is_unique(setup):
    s = setup
    # SQLite precisa explicitar FK; PostgreSQL aplica as mesmas constraints sempre.
    s.db.connection().exec_driver_sql("PRAGMA foreign_keys=ON")
    s.db.add(
        IfoodCatalogLink(
            tenant_id=s.tenant,
            merchant_id=s.merchant,
            product_id=s.other.id,
            barcode=EAN,
            mode="existing",
            revision=1,
            portal_checked_at=datetime.now(timezone.utc),
            portal_checked_by=1,
        )
    )
    with pytest.raises(IntegrityError):
        s.db.flush()
    s.db.rollback()


def test_two_tenants_can_link_same_barcode_without_shared_history(setup):
    s = setup
    own = link(s, price="73.90")
    with tenant_context(s.foreign):
        s.other.codigo_barras = EAN
        s.db.add(
            IfoodMerchantConfig(
                tenant_id=s.foreign, merchant_id=s.merchant, active=True
            )
        )
        foreign_link = IfoodCatalogLink(
            tenant_id=s.foreign,
            merchant_id=s.merchant,
            product_id=s.other.id,
            barcode=EAN,
            mode="new",
            revision=1,
            portal_checked_at=datetime.now(timezone.utc),
            portal_checked_by=2,
        )
        s.db.add(foreign_link)
        s.db.commit()
    result = s.client.get(s.path + "/publicacao").json()
    assert result["link"] == own["link"]
    assert result["last_confirmation"] == own["last_confirmation"]


def test_accepted_request_key_cannot_replay_as_another_operation_or_field(
    setup, monkeypatch
):
    s = setup
    link(s)
    p = prepare(s, fields=["stock"])
    monkeypatch.setattr(settings, "IFOOD_CATALOG_WRITE_ENABLED", True)
    key = str(uuid4())
    assert send(s, p, request_key=key).status_code == 200
    assert send(s, p, request_key=key, fields=["price"]).status_code == 409
    assert send(s, p, request_key=key, operation="create").status_code == 409
    assert len(s.calls) == 1


def test_fractional_stock_is_blocked_for_packaged_pilot_without_rounding_send(
    setup, monkeypatch
):
    s = setup
    link(s)
    s.first.estoque_atual = 1.5
    s.db.commit()
    p = prepare(s, fields=["stock"])
    assert not p["eligible"]
    assert "stock_invalid" in {entry["code"] for entry in p["pending"]}
    monkeypatch.setattr(settings, "IFOOD_CATALOG_WRITE_ENABLED", True)
    assert send(s, p).status_code == 409 and not s.calls


def test_central_exposes_stale_barcode_and_does_not_attach_old_confirmed_price(setup):
    s = setup
    link(s, price="73.90")
    s.first.codigo_barras = OTHER_EAN
    s.db.commit()
    item = s.client.get("/integracoes/ifood/catalogo/gestao").json()["items"][0]
    assert item["publication"]["link"]["stale"]
    assert item["publication"]["last_confirmation"]["barcode"] == EAN
    assert item["last_confirmed_price"] is None


def test_unique_binding_barcode_constraint_rejects_two_products_of_same_store(setup):
    s = setup
    link(s)
    another = Produto(
        tenant_id=s.tenant,
        user_id=1,
        codigo="UNIQUE-TEST",
        nome="Ficticio",
        codigo_barras=OTHER_EAN,
    )
    s.db.add(another)
    s.db.flush()
    s.db.add(
        IfoodCatalogLink(
            tenant_id=s.tenant,
            merchant_id=s.merchant,
            product_id=another.id,
            barcode=EAN,
            mode="existing",
            revision=1,
            portal_checked_at=datetime.now(timezone.utc),
            portal_checked_by=1,
        )
    )
    with pytest.raises(IntegrityError):
        s.db.flush()
    s.db.rollback()


@pytest.mark.parametrize(
    "source,expected",
    [
        (
            '<h2 style="color:red">Ração &amp; cuidado</h2><p class="editor">Cães <strong>adultos</strong>.<br>Água fresca.</p>',
            "Ração & cuidado\n\nCães adultos.\nÁgua fresca.",
        ),
        (
            "<p>Primeiro parágrafo.</p><div>Segundo parágrafo.</div>",
            "Primeiro parágrafo.\n\nSegundo parágrafo.",
        ),
        (
            "<ul><li><p>Frango &amp; arroz</p></li><li><p>Vitaminas</p></li></ul>",
            "• Frango & arroz\n• Vitaminas",
        ),
        (
            "<ol><li>Abra a embalagem</li><li>Sirva</li></ol>",
            "1. Abra a embalagem\n2. Sirva",
        ),
        (
            "<p>Até &lt;5 kg e &gt;2 kg; &#231; e &#xE3;.</p>",
            "Até <5 kg e >2 kg; ç e ã.",
        ),
        (
            '<p>Antes</p><script>segredo;document.write("texto")</script><style>.classe{color:red}</style><p>Depois</p>',
            "Antes\n\nDepois",
        ),
        ("<script>não exportar</script><style>nem isso</style>", ""),
        ("<p><br></p><div>&nbsp; &#160;</div><!-- comentario -->", ""),
        ("<div><custom>Acentuação</custom></div>", "Acentuação"),
        ("2 < 3 e 5 > 4; peso <5 kg.", "2 < 3 e 5 > 4; peso <5 kg."),
        ("x<y e y>z", "x<y e y>z"),
        ("Dose A<B e C>D.", "Dose A<B e C>D."),
        ("<p>Dose A<B e C>D.</p>", "Dose A<B e C>D."),
        ("<!-- somente comentario -->", ""),
        ("<ul><li></li></ul>", ""),
        ("<ol><li><p><br></p></li></ol>", ""),
        ("<p>1.</p>", "1."),
        (
            "Texto simples\n\nCom parágrafos e acentuação.",
            "Texto simples\n\nCom parágrafos e acentuação.",
        ),
        ("Ração &amp; água&nbsp;fresca", "Ração & água fresca"),
        ('<p>Ração <span class="x">com</span> arroz</p>', "Ração com arroz"),
    ],
)
def test_item_description_exports_legible_text(source, expected):
    assert item_description_text(source) == expected


def test_rich_description_normalized_only_in_create_payload_and_source_unchanged(setup):
    s = setup
    source = '<h2 style="font-weight:bold">Produto fictício</h2><p class="editor">Alimento &amp; cuidado.<br>Água fresca.</p>'
    s.first.descricao_completa = source
    s.db.commit()
    link(s, "new")
    result = prepare(s, "create")
    assert result["eligible"]
    assert (
        result["payload"]["details"]["description"]
        == "Produto fictício\n\nAlimento & cuidado.\nÁgua fresca."
    )
    s.db.expire_all()
    assert s.first.descricao_completa == source
    assert not s.calls and s.db.query(IfoodCatalogSubmission).count() == 0


def test_empty_full_html_falls_back_to_readable_short_description(setup):
    s = setup
    s.first.descricao_completa = "<p><br></p>"
    s.first.descricao_curta = "<p>Descrição curta &amp; legível.</p>"
    s.db.commit()
    link(s, "new")
    result = prepare(s, "create")
    assert result["eligible"]
    assert result["payload"]["details"]["description"] == "Descrição curta & legível."
    item = s.client.get("/integracoes/ifood/catalogo/gestao").json()["items"][0]
    assert "descricao" not in {pending["code"] for pending in item["pending"]}


def test_empty_html_is_a_description_pending_in_management_and_preparation(setup):
    s = setup
    s.first.descricao_completa = "<p><br></p><style>.vazio{}</style>"
    s.first.descricao_curta = "<script>não é descrição</script><p>&nbsp;</p>"
    s.db.commit()
    link(s, "new")
    result = prepare(s, "create")
    assert not result["eligible"]
    assert result["payload"]["details"]["description"] is None
    assert "content_missing" in {pending["code"] for pending in result["pending"]}
    item = s.client.get("/integracoes/ifood/catalogo/gestao").json()["items"][0]
    assert "descricao" in {pending["code"] for pending in item["pending"]}


def test_stock_only_patch_omits_even_rich_description(setup):
    s = setup
    source = '<h2 style="color:red">Descrição fictícia</h2><script>ignorar</script>'
    s.first.descricao_completa = source
    s.db.commit()
    link(s)
    result = prepare(s, fields=["stock"])
    assert result["eligible"] and result["payload"] == {
        "barcode": EAN,
        "inventory": {"stock": 10},
    }
    assert "details" not in result["payload"]
    assert s.first.descricao_completa == source and not s.calls


def test_automatic_stock_blocks_manual_mutations_but_preserves_read_only_evidence(
    setup, monkeypatch
):
    from app.ifood_catalog_models import IfoodStockSyncState
    from app.integrations.ifood import stock_sync

    s = setup
    initial = link(s, price="100", stock="21", portal_active=True)
    prepared = prepare(s, fields=["stock"])
    row = IfoodStockSyncState(
        tenant_id=s.tenant,
        merchant_id=s.merchant,
        link_id=initial["link"]["id"],
        link_revision=initial["link"]["revision"],
        desired_stock=20,
        last_accepted_stock=21,
        status="queued",
        failure_count=0,
    )
    s.db.add(row)
    s.db.commit()
    monkeypatch.setattr(
        stock_sync,
        "enabled_for",
        lambda tenant, merchant, product: (
            tenant == s.tenant and merchant == s.merchant and product == s.first.id
        ),
    )
    monkeypatch.setattr(settings, "IFOOD_CATALOG_WRITE_ENABLED", True)
    view = s.client.get(s.path + "/publicacao").json()
    assert view["stock_sync"]["desired_stock"] == 20
    assert view["stock_sync"]["last_accepted_stock"] == 21
    assert view["stock_sync"]["enabled"] is True
    assert view["stock_sync"]["external_confirmed"] is False
    assert not view["capabilities"]["can_link"]
    assert not view["capabilities"]["can_confirm"]
    assert not view["capabilities"]["can_send"]
    assert "automatic_stock_active" in {p["code"] for p in view["pending"]}
    assert not prepare(s, fields=["stock"])["eligible"]
    assert send(s, prepared).status_code == 409
    evidence = {"merchant_id": s.merchant, "barcode": EAN, "stock": "21"}
    assert (
        s.client.post(
            s.path + "/confirmar-portal", json={**evidence, "present": True}
        ).status_code
        == 409
    )
    assert (
        s.client.put(
            s.path + "/vinculo",
            json={**evidence, "mode": "existing", "portal_checked": True},
        ).status_code
        == 409
    )
    item = s.client.get("/integracoes/ifood/catalogo/gestao").json()["items"][0]
    assert item["publication"]["stock_sync"] == view["stock_sync"]
    assert not s.calls and s.db.query(IfoodCatalogSubmission).count() == 0
