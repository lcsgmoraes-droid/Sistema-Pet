from types import SimpleNamespace
import importlib
import logging
import sys

from app.services.order_push_notifications import (
    build_order_push_content,
    notify_order_event,
)


class FakeQuery:
    def __init__(self, user):
        self.user = user

    def filter(self, *args):
        return self

    def first(self):
        return self.user


class FakeDB:
    def __init__(self, user):
        self.user = user

    def query(self, model):
        return FakeQuery(self.user)


def test_order_push_service_does_not_import_customer_history_models():
    sys.modules.pop("app.services.order_push_notifications", None)
    sys.modules.pop("app.services.customer_order_history", None)

    importlib.import_module("app.services.order_push_notifications")

    assert "app.services.customer_order_history" not in sys.modules


def test_build_order_push_content_maps_payment_and_fulfillment_events():
    approved = build_order_push_content(
        event="payment_approved",
        pedido_id="PED-1",
        venda_id=10,
        canal="ecommerce",
    )
    ready = build_order_push_content(
        event="ready_for_pickup",
        pedido_id="PED-1",
        venda_id=10,
        canal="app",
    )

    assert approved["title"] == "Pagamento aprovado"
    assert approved["data"]["source"] == "order"
    assert approved["data"]["kind"] == "order_status"
    assert approved["data"]["canal"] == "ecommerce"
    assert ready["title"] == "Pedido pronto para retirada"
    assert ready["data"]["canal"] == "app"


def test_notify_order_event_sends_expo_push_without_blocking(monkeypatch):
    calls = []

    def fake_post(url, json, timeout, headers=None):
        calls.append({"url": url, "json": json, "timeout": timeout, "headers": headers})
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {"data": {"status": "ok"}},
        )

    monkeypatch.setattr(
        "app.services.order_push_notifications.requests.post", fake_post
    )
    user = SimpleNamespace(
        id=5, tenant_id="tenant-1", push_token="ExponentPushToken[test]"
    )

    sent = notify_order_event(
        FakeDB(user),
        tenant_id="tenant-1",
        user_id=5,
        event="checkout_created",
        pedido_id="PED-2",
        venda_id=None,
        canal="app",
    )

    assert sent is True
    assert calls[0]["json"]["to"] == "ExponentPushToken[test]"
    assert calls[0]["json"]["data"]["pedido_id"] == "PED-2"


def test_notify_order_event_ignores_missing_token_and_send_errors(monkeypatch):
    def failing_post(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr(
        "app.services.order_push_notifications.requests.post", failing_post
    )

    assert (
        notify_order_event(
            FakeDB(SimpleNamespace(push_token=None)),
            tenant_id="t",
            user_id=1,
            event="checkout_created",
        )
        is False
    )
    assert (
        notify_order_event(
            FakeDB(
                SimpleNamespace(
                    id=1, tenant_id="t", push_token="ExponentPushToken[test]"
                )
            ),
            tenant_id="t",
            user_id=1,
            event="checkout_created",
        )
        is False
    )


def test_notify_order_event_logs_when_user_has_no_push_token(caplog):
    caplog.set_level(logging.INFO, logger="app.services.order_push_notifications")

    sent = notify_order_event(
        FakeDB(SimpleNamespace(id=11, tenant_id="tenant-1", push_token=None)),
        tenant_id="tenant-1",
        user_id=11,
        event="ready_for_pickup",
        pedido_id="202606200026",
        venda_id=1065887,
        canal="ecommerce",
    )

    assert sent is False
    assert "sem push_token" in caplog.text
    assert "user_id=11" in caplog.text
    assert "venda_id=1065887" in caplog.text
