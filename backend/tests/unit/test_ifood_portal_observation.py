"""Conferencia humana append-only, sem rede e sem rebaseline da fila."""

from datetime import timedelta
from decimal import Decimal

import pytest

from app.config import settings
from app.ifood_catalog_models import (
    IfoodCatalogConfirmation as Confirmation,
    IfoodCatalogLink as Link,
    IfoodCatalogSubmission as Submission,
    IfoodStockSyncState as State,
)
from app.integrations.ifood import catalog_pilot as catalog
from app.integrations.ifood.client import IfoodClientError
from app.routes import ifood_catalog_pilot_routes as routes
from tests.unit.test_ifood_management import api  # noqa: F401
from tests.unit.test_ifood_stock_sync import START, pilot  # noqa: F401


@pytest.fixture
def portal(pilot, monkeypatch):  # noqa: F811
    pilot.client.app.include_router(routes.router)
    monkeypatch.setattr(routes, "_credentials_configured", lambda: True)
    monkeypatch.setattr(catalog, "now", lambda: START + timedelta(seconds=5))
    return pilot


def publication(c):
    response = c.client.get(
        f"/integracoes/ifood/catalogo/produtos/{c.first.id}/publicacao"
    )
    assert response.status_code == 200, response.text
    return response.json()


def observe(c, *, view=None, **changes):
    view = view or publication(c)
    body = {
        "merchant_id": c.merchant,
        "barcode": c.first.codigo_barras,
        "present": True,
        "portal_active": True,
        "price": "154.90",
        "stock": "21",
        "confirmation_context_token": view["confirmation_context_token"],
        **changes,
    }
    return c.client.post(
        f"/integracoes/ifood/catalogo/produtos/{c.first.id}/confirmar-portal", json=body
    )


def snapshot(c):
    c.db.expire_all()
    return {
        model.__tablename__: [
            {col.key: getattr(row, col.key) for col in model.__mapper__.columns}
            for row in c.db.query(model).order_by(model.id)
        ]
        for model in (State, Submission, Link)
    }


def accepted(c):
    c.first.estoque_atual = 20
    assert c.tick()["status"] == "accepted"
    assert len(c.provider.calls) == 1


def test_observation_after_acceptance_preserves_reference_window_and_history(portal):
    c = portal
    accepted(c)
    before = snapshot(c)
    view = publication(c)
    response = observe(c, view=view, stock="20")
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["last_confirmation"]["kind"] == "observation"
    assert result["last_confirmation"]["portal_active"] is True
    assert result["last_confirmation"]["stock"] == "20.000"
    assert result["link"] == view["link"]
    assert snapshot(c) == before
    c.first.estoque_atual = 19
    assert c.tick(START + timedelta(minutes=1))["status"] == "cooldown"
    state = c.db.query(State).one()
    assert state.last_accepted_stock == 20
    assert state.next_attempt_at.replace(tzinfo=START.tzinfo) == START + timedelta(
        minutes=35
    )
    assert len(c.provider.calls) == 1


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"present": False, "portal_active": None}, "portal_item_not_found"),
        ({"portal_active": False}, "portal_item_inactive"),
        ({"portal_active": None}, "portal_activity_unknown"),
    ],
)
def test_inactive_unknown_absent_gate_preserves_queue_until_explicit_active(
    portal, changes, reason
):
    c = portal
    accepted(c)
    before = snapshot(c)
    response = observe(c, **changes)
    assert response.status_code == 200, response.text
    assert response.json()["stock_sync"]["observation_block_reason"] == reason
    assert reason in {row["code"] for row in response.json()["pending"]}
    assert snapshot(c) == before
    assert c.tick(START + timedelta(minutes=1)) == {
        "status": "blocked",
        "reason": reason,
    }
    assert snapshot(c) == before
    assert len(c.provider.calls) == 1
    assert observe(c, stock="20").status_code == 200
    assert c.tick(START + timedelta(minutes=2))["status"] == "unchanged"
    assert snapshot(c) == before
    assert len(c.provider.calls) == 1


def test_divergent_observed_stock_warns_without_reseeding_or_resending(portal):
    c = portal
    accepted(c)
    before = snapshot(c)
    response = observe(c, stock="5")
    assert response.status_code == 200
    assert "portal_stock_divergent" in {
        row["code"] for row in response.json()["pending"]
    }
    assert c.tick(START + timedelta(minutes=1))["status"] == "unchanged"
    assert snapshot(c) == before
    assert len(c.provider.calls) == 1


def test_token_rejects_missing_stale_and_other_product_context_without_writes(portal):
    c = portal
    accepted(c)
    view = publication(c)
    count = c.db.query(Confirmation).count()
    assert observe(c, view=view, confirmation_context_token=None).status_code == 409
    assert observe(c, view=view, confirmation_context_token="0" * 64).status_code == 409
    assert c.db.query(Confirmation).count() == count
    assert observe(c, view=view, stock="20").status_code == 200
    assert observe(c, view=view, stock="20").status_code == 409
    assert c.db.query(Confirmation).count() == count + 1


@pytest.mark.parametrize(
    "error", [IfoodClientError("fixture", status_code=429), TimeoutError()]
)
def test_pending_or_uncertain_cannot_be_released_by_common_observation(portal, error):
    c = portal
    c.first.estoque_atual = 20
    c.provider.error = error
    c.tick()
    before = snapshot(c)
    view = publication(c)
    assert not view["capabilities"]["can_confirm"]
    count = c.db.query(Confirmation).count()
    assert observe(c, view=view).status_code == 409
    assert snapshot(c) == before
    assert c.db.query(Confirmation).count() == count


def test_turned_off_existing_queue_still_records_receipt_without_rebaseline(
    portal, monkeypatch
):
    c = portal
    accepted(c)
    before = snapshot(c)
    monkeypatch.setattr(settings, "IFOOD_STOCK_SYNC_DEV_ENABLED", False)
    monkeypatch.setattr(settings, "IFOOD_STOCK_SYNC_POLLING_ENABLED", False)
    result = observe(c, stock="0", price="0", portal_active=False)
    assert result.status_code == 200
    assert result.json()["last_confirmation"]["kind"] == "observation"
    assert result.json()["last_confirmation"]["stock"] == "0.000"
    assert result.json()["last_confirmation"]["price"] == "0.00"
    assert snapshot(c) == before


def test_unknown_values_stay_unknown_in_receipt_and_do_not_replace_reference(portal):
    c = portal
    accepted(c)
    before = snapshot(c)
    result = observe(c, stock=None, price=None, portal_active=None)
    assert result.status_code == 200
    confirmation = result.json()["last_confirmation"]
    assert confirmation["stock"] is None and confirmation["price"] is None
    assert confirmation["portal_active"] is None
    assert snapshot(c) == before
    assert c.db.query(State).one().last_accepted_stock == 20
    assert (
        c.db.query(Confirmation).order_by(Confirmation.id.desc()).first().stock is None
    )


def test_first_manual_reference_without_state_remains_explicit_and_known(
    portal, monkeypatch
):
    c = portal
    monkeypatch.setattr(settings, "IFOOD_STOCK_SYNC_DEV_ENABLED", False)
    monkeypatch.setattr(settings, "IFOOD_STOCK_SYNC_POLLING_ENABLED", False)
    initial = publication(c)
    result = observe(c, stock="0", price="0", portal_active=False)
    assert result.status_code == 200
    value = result.json()
    assert value["last_confirmation"]["kind"] == "portal"
    assert value["link"]["revision"] == initial["link"]["revision"] + 1
    assert value["last_confirmation"]["portal_active"] is False
    assert c.db.query(Confirmation).order_by(
        Confirmation.id.desc()
    ).first().stock == Decimal(0)
    assert not c.db.query(State).count() and not c.db.query(Submission).count()
