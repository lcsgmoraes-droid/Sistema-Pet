"""Ciclos de estoque via rotas reais e estado remoto ficticio; nenhuma rede."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.config import settings
from app.ifood_catalog_models import IfoodCatalogSubmission
from app.integrations.ifood import catalog_pilot
from app.produtos_catalogo_models import Produto
from app.routes import ifood_catalog_pilot_routes as routes
from app.tenancy.context import tenant_context
from tests.unit.test_ifood_catalog_pilot import EAN, OTHER_EAN, link, prepare, send
from tests.unit.test_ifood_catalog_pilot import setup  # noqa: F401 - fixture HTTP
from tests.unit.test_ifood_management import api  # noqa: F401 - dependencia setup


def _snapshot(product, *, allow_stock_and_pause=False):
    excluded = set()
    if allow_stock_and_pause:
        excluded |= {"estoque_atual", "ifood_pausado", "updated_at"}
    return deepcopy(
        {
            column.key: getattr(product, column.key)
            for column in Produto.__table__.columns
            if column.key not in excluded
        }
    )


@pytest.fixture
def cycle(setup, monkeypatch):  # noqa: F811 - fixture importada
    s = setup

    class Clock:
        current = datetime(2042, 4, 5, 12, tzinfo=timezone.utc)

        def advance(self, seconds):
            self.current += timedelta(seconds=seconds)

    clock = Clock()
    monkeypatch.setattr(catalog_pilot, "now", lambda: clock.current)
    monkeypatch.setattr(settings, "IFOOD_CATALOG_WRITE_ENABLED", True)
    s.first.codigo = "018631.1"
    s.first.preco_ifood_promo = 80
    s.first.preco_app = 111
    s.first.preco_app_promo = 99
    s.first.preco_ecommerce = 112
    s.first.preco_ecommerce_promo = 98
    neighbor = Produto(
        tenant_id=s.tenant,
        user_id=1,
        codigo="DEV-OUTRO-NAO-OPERAR",
        nome="Produto ficticio fora do ciclo",
        codigo_barras=OTHER_EAN,
        preco_venda=45,
        preco_custo=23,
        preco_app=48,
        preco_ecommerce=49,
        preco_ifood=50,
        estoque_atual=7,
        anunciar_ifood=False,
        ifood_pausado=True,
    )
    s.db.add(neighbor)
    s.db.commit()
    remote = {
        EAN: {
            "barcode": EAN,
            "name": "Nome remoto diferente do cadastro local",
            "active": True,
            "inventory": {"stock": 10},
            "prices": {"price": 147.90, "promotionPrice": 119.90},
            "details": {
                "description": "Descricao remota preservada",
                "imageUrl": "https://fixture.example.test/imagem-remota.png",
            },
            "channels": ["ifood-app", "ifood-shop"],
            "plu": "PLU-REMOTO",
        },
        OTHER_EAN: {"barcode": OTHER_EAN, "inventory": {"stock": 7}},
    }
    remote_baseline = deepcopy(remote)
    requests = []

    class ReceiverClient:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def ingest_items(self, merchant_id, items, **kwargs):
            assert merchant_id == s.merchant
            assert kwargs == {"method": "PATCH", "reset_catalog": False}
            assert len(items) == 1
            payload = items[0]
            assert payload["barcode"] == EAN
            assert set(payload) == {"barcode", "inventory"}
            assert set(payload["inventory"]) == {"stock"}
            assert type(payload["inventory"]["stock"]) is int
            assert payload["inventory"]["stock"] >= 0
            requests.append(deepcopy(payload))
            remote[EAN]["inventory"] = deepcopy(payload["inventory"])
            return {"status_code": 202, "response": {"requestId": str(uuid4())}}

    monkeypatch.setattr(routes, "_client", ReceiverClient)
    protected_target = _snapshot(s.first, allow_stock_and_pause=True)
    protected_neighbor = _snapshot(neighbor)
    with tenant_context(s.foreign):
        protected_foreign = _snapshot(s.other)
    config_baseline = {
        column.key: deepcopy(getattr(s.config, column.key))
        for column in s.config.__table__.columns
    }
    link(s, portal_active=True, price="147.90", stock="10")
    return SimpleNamespace(
        s=s,
        clock=clock,
        remote=remote,
        remote_baseline=remote_baseline,
        requests=requests,
        neighbor=neighbor,
        protected_target=protected_target,
        protected_neighbor=protected_neighbor,
        protected_foreign=protected_foreign,
        config_baseline=config_baseline,
    )


def _save_local(c, *, stock=None, paused=None):
    """Simula alteracao legitima no ERP; nao abre nem opera cliente externo."""
    before = len(c.requests)
    if stock is not None:
        c.s.first.estoque_atual = stock
    if paused is not None:
        c.s.first.ifood_pausado = paused
    c.s.db.commit()
    assert len(c.requests) == before


def _send_phase(c, expected_stock):
    p = prepare(c.s, fields=["stock"])
    assert p["eligible"], p["pending"]
    assert p["payload"] == {"barcode": EAN, "inventory": {"stock": expected_stock}}
    key = str(uuid4())
    before = len(c.requests)
    result = send(c.s, p, request_key=key)
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "accepted"
    assert len(c.requests) == before + 1
    replay = send(c.s, p, request_key=key)
    assert replay.status_code == 200, replay.text
    assert replay.json()["replayed"]
    assert replay.json()["submission"]["id"] == result.json()["submission"]["id"]
    assert len(c.requests) == before + 1
    assert c.remote[EAN]["inventory"]["stock"] == expected_stock
    assert c.s.db.query(IfoodCatalogSubmission).count() == len(c.requests)
    return result.json()


def _confirm(c):
    c.clock.advance(1)
    before = len(c.requests)
    response = c.s.client.post(
        c.s.path + "/confirmar-portal",
        json={
            "merchant_id": c.s.merchant,
            "barcode": EAN,
            "present": True,
            "portal_active": c.remote[EAN]["active"],
            "price": str(c.remote[EAN]["prices"]["price"]),
            "stock": str(c.remote[EAN]["inventory"]["stock"]),
        },
    )
    assert response.status_code == 200, response.text
    assert len(c.requests) == before
    return response.json()


def _finish_phase(c):
    confirmed = _confirm(c)
    assert confirmed["last_confirmation"]["portal_active"] is True
    assert "ingestion_window" in {p["code"] for p in confirmed["pending"]}
    c.clock.advance(35 * 60)


def _assert_protected(c):
    remote_target = deepcopy(c.remote[EAN])
    remote_baseline = deepcopy(c.remote_baseline[EAN])
    remote_target.pop("inventory")
    remote_baseline.pop("inventory")
    assert remote_target == remote_baseline
    assert c.remote[OTHER_EAN] == c.remote_baseline[OTHER_EAN]
    c.s.db.expire_all()
    assert _snapshot(c.s.first, allow_stock_and_pause=True) == c.protected_target
    assert _snapshot(c.neighbor) == c.protected_neighbor
    with tenant_context(c.s.foreign):
        assert _snapshot(c.s.other) == c.protected_foreign
    assert {
        column.key: deepcopy(getattr(c.s.config, column.key))
        for column in c.s.config.__table__.columns
    } == c.config_baseline


def test_active_product_stock_zero_then_restock_without_post_or_metadata_changes(cycle):
    c = cycle
    _save_local(c, stock=0)
    _send_phase(c, 0)
    assert c.remote[EAN]["active"] is True
    assert not (c.remote[EAN]["active"] and c.remote[EAN]["inventory"]["stock"] > 0)
    _assert_protected(c)
    _finish_phase(c)
    _save_local(c, stock=8)
    _send_phase(c, 8)
    assert c.remote[EAN]["active"] and c.remote[EAN]["inventory"]["stock"] > 0
    _confirm(c)
    assert len(c.requests) == 2
    assert not c.s.first.ifood_pausado
    _assert_protected(c)


def test_manual_pause_survives_restock_until_explicitly_removed(cycle):
    c = cycle
    _save_local(c, paused=True)
    _send_phase(c, 0)
    assert c.s.first.estoque_atual == 10 and c.s.first.ifood_pausado
    _finish_phase(c)
    _save_local(c, stock=24)
    _send_phase(c, 0)
    assert c.s.first.estoque_atual == 24 and c.s.first.ifood_pausado
    assert c.remote[EAN]["inventory"]["stock"] == 0
    _assert_protected(c)
    _finish_phase(c)
    _save_local(c, paused=False)
    _send_phase(c, 24)
    _confirm(c)
    assert not c.s.first.ifood_pausado
    assert len(c.requests) == 3
    _assert_protected(c)


@pytest.mark.parametrize("change", [{"stock": 2}, {"paused": True}])
def test_changed_stock_or_pause_rejects_stale_review_before_external_call(
    cycle, change
):
    c = cycle
    p = prepare(c.s, fields=["stock"])
    assert p["eligible"] and p["payload"]["inventory"]["stock"] == 10
    _save_local(c, **change)
    result = send(c.s, p)
    assert result.status_code == 409, result.text
    assert not c.requests
    assert c.s.db.query(IfoodCatalogSubmission).count() == 0
    _assert_protected(c)


def test_confirmation_and_full_35_minute_window_are_independent_requirements(cycle):
    c = cycle
    _save_local(c, stock=0)
    _send_phase(c, 0)
    _confirm(c)
    _save_local(c, stock=4)
    c.clock.advance(35 * 60 - 2)  # Ainda 1s antes do limite.
    p = prepare(c.s, fields=["stock"])
    assert not p["eligible"]
    assert "ingestion_window" in {item["code"] for item in p["pending"]}
    assert "portal_confirmation_required" not in {item["code"] for item in p["pending"]}
    assert send(c.s, p).status_code == 409
    assert len(c.requests) == 1
    c.clock.advance(1)  # Limite exato, nao esperar nem ignorar a guarda.
    _send_phase(c, 4)
    _save_local(c, stock=6)
    c.clock.advance(35 * 60 + 1)
    p = prepare(c.s, fields=["stock"])
    assert not p["eligible"]
    assert "portal_confirmation_required" in {item["code"] for item in p["pending"]}
    assert "ingestion_window" not in {item["code"] for item in p["pending"]}
    assert send(c.s, p).status_code == 409
    assert len(c.requests) == 2
    _confirm(c)
    _send_phase(c, 6)
    _confirm(c)
    _assert_protected(c)
