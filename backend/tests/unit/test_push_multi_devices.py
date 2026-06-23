from types import SimpleNamespace

from app.campaigns.models import (
    NotificationChannelEnum,
    NotificationQueue,
    NotificationStatusEnum,
)
from app.campaigns.notification_sender import NotificationSender
from app.models import Cliente, EcommerceNotifyRequest, Tenant, User, UserPushDevice
from app.produtos_models import Produto
from app.routes.ecommerce_notify_routes import notificar_clientes_estoque_disponivel


class FakeQuery:
    def __init__(self, items):
        self.items = items

    def filter(self, *args):
        return self

    def order_by(self, *args):
        return self

    def with_for_update(self, **kwargs):
        return self

    def limit(self, value):
        return self

    def all(self):
        if isinstance(self.items, list):
            return self.items
        return [] if self.items is None else [self.items]

    def first(self):
        if isinstance(self.items, list):
            return self.items[0] if self.items else None
        return self.items


class FakeNotificationDB:
    def __init__(self, *, notification, cliente, user, devices):
        self.notification = notification
        self.cliente = cliente
        self.user = user
        self.devices = devices
        self.committed = False
        self.closed = False
        self.rolled_back = False

    def query(self, model):
        if model is NotificationQueue:
            return FakeQuery([self.notification])
        if model is Cliente:
            return FakeQuery(self.cliente)
        if model is User:
            return FakeQuery(self.user)
        if model is UserPushDevice:
            return FakeQuery(self.devices)
        return FakeQuery(None)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


class FakeNotifyDB:
    def __init__(self, *, tenant, product, pending, user, devices):
        self.tenant = tenant
        self.product = product
        self.pending = pending
        self.user = user
        self.devices = devices
        self.committed = False

    def query(self, model):
        if model is Tenant:
            return FakeQuery(self.tenant)
        if model is Produto:
            return FakeQuery(self.product)
        if model is EcommerceNotifyRequest:
            return FakeQuery(self.pending)
        if model is User:
            return FakeQuery(self.user)
        if model is UserPushDevice:
            return FakeQuery(self.devices)
        return FakeQuery(None)

    def commit(self):
        self.committed = True


def _push_device(device_id: int, token: str):
    return SimpleNamespace(
        id=device_id,
        expo_push_token=token,
        enabled=True,
        last_success_at=None,
        last_ticket_id=None,
        last_error=None,
        last_error_at=None,
    )


def test_notification_sender_sends_queued_push_to_all_active_customer_devices(
    monkeypatch,
):
    calls = []

    def fake_post(url, json, timeout, headers=None):
        calls.append(json)
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {"data": {"status": "ok", "id": f"ticket-{len(calls)}"}},
        )

    monkeypatch.setattr("app.campaigns.notification_sender.requests.post", fake_post)

    notification = SimpleNamespace(
        id=1,
        tenant_id="tenant-1",
        customer_id=77,
        channel=NotificationChannelEnum.push,
        status=NotificationStatusEnum.pending,
        retry_count=0,
        max_retries=3,
        subject="Pedido atualizado",
        body="Seu pedido mudou de status.",
        idempotency_key="order:77:push",
        push_token=None,
    )
    db = FakeNotificationDB(
        notification=notification,
        cliente=SimpleNamespace(id=77, tenant_id="tenant-1", user_id=5),
        user=SimpleNamespace(id=5, tenant_id="tenant-1", push_token=None),
        devices=[
            _push_device(10, "ExponentPushToken[phone-a]"),
            _push_device(11, "ExponentPushToken[phone-b]"),
        ],
    )

    stats = NotificationSender(lambda: db).process_batch()

    assert stats["sent"] == 1
    assert notification.status == NotificationStatusEnum.sent
    assert [call["to"] for call in calls] == [
        "ExponentPushToken[phone-a]",
        "ExponentPushToken[phone-b]",
    ]
    assert db.devices[0].last_ticket_id == "ticket-1"
    assert db.devices[1].last_ticket_id == "ticket-2"


def test_stock_available_push_uses_all_active_user_devices(monkeypatch):
    calls = []

    tenant_id = "11111111-1111-1111-1111-111111111111"

    def fake_post(url, json, timeout, headers=None):
        calls.append(json)
        return SimpleNamespace(raise_for_status=lambda: None)

    monkeypatch.setattr("requests.post", fake_post)
    monkeypatch.setattr(
        "app.services.email_service.send_notify_me_email",
        lambda **kwargs: True,
    )

    request = SimpleNamespace(
        email="cliente@example.com",
        product_id=123,
        product_name="Racao",
        notified=False,
        notified_at=None,
    )
    db = FakeNotifyDB(
        tenant=SimpleNamespace(id=tenant_id, name="Pet Teste", ecommerce_slug="pet"),
        product=SimpleNamespace(id=123, tenant_id=tenant_id, codigo="RACAO-1"),
        pending=[request],
        user=SimpleNamespace(
            id=5,
            tenant_id=tenant_id,
            email="cliente@example.com",
            push_token="ExponentPushToken[legacy]",
        ),
        devices=[
            _push_device(10, "ExponentPushToken[phone-a]"),
            _push_device(11, "ExponentPushToken[phone-b]"),
        ],
    )

    sent = notificar_clientes_estoque_disponivel(
        db,
        tenant_id=tenant_id,
        product_id=123,
        product_name="Racao",
    )

    assert sent == 1
    assert request.notified is True
    assert db.committed is True
    assert [message["to"] for message in calls[0]] == [
        "ExponentPushToken[phone-a]",
        "ExponentPushToken[phone-b]",
    ]
