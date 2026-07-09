from types import SimpleNamespace
from uuid import UUID

from app.models import Cliente, User, UserPushDevice
from app.services.push_devices import load_customer_push_targets


TENANT_ID = UUID("11111111-1111-4111-8111-111111111111")


def _flatten_conditions(conditions):
    for condition in conditions:
        clauses = getattr(condition, "clauses", None)
        if clauses is None:
            yield condition
        else:
            yield from _flatten_conditions(tuple(clauses))


def _condition_name_value(condition):
    left_name = getattr(getattr(condition, "left", None), "name", None)
    right_value = getattr(getattr(condition, "right", None), "value", None)
    return left_name, right_value


class _FilteringQuery:
    def __init__(self, items):
        self.items = list(items)
        self.conditions = []

    def filter(self, *conditions):
        self.conditions.extend(_flatten_conditions(conditions))
        return self

    def order_by(self, *columns):
        return self

    def _matches(self, item):
        for condition in self.conditions:
            name, value = _condition_name_value(condition)
            if name == "enabled" and " IS true" in str(condition):
                if getattr(item, name, None) is not True:
                    return False
                continue
            if name is None:
                continue

            current = getattr(item, name, None)
            if name == "email":
                if str(current or "").strip().lower() != str(value or "").lower():
                    return False
                continue
            if str(current) != str(value):
                return False
        return True

    def all(self):
        return [item for item in self.items if self._matches(item)]

    def first(self):
        matches = self.all()
        return matches[0] if matches else None


class _PushDb:
    def __init__(self, *, clientes, users, devices):
        self.clientes = clientes
        self.users = users
        self.devices = devices

    def query(self, model):
        if model is Cliente:
            return _FilteringQuery(self.clientes)
        if model is User:
            return _FilteringQuery(self.users)
        if model is UserPushDevice:
            return _FilteringQuery(self.devices)
        return _FilteringQuery([])


def test_load_customer_push_targets_uses_app_user_email_when_cliente_user_id_is_operational():
    cliente_pdv = SimpleNamespace(
        id=77,
        tenant_id=TENANT_ID,
        user_id=999,
        nome="Lucas Guerra de Moraes",
        email="lcsgmoraes@gmail.com",
    )
    usuario_operacional = SimpleNamespace(
        id=999,
        tenant_id=TENANT_ID,
        email="loja@example.com",
        push_token=None,
    )
    usuario_app = SimpleNamespace(
        id=5,
        tenant_id=TENANT_ID,
        email="lcsgmoraes@gmail.com",
        push_token=None,
    )
    device_app = SimpleNamespace(
        id=9,
        user_id=5,
        tenant_id=TENANT_ID,
        expo_push_token="ExponentPushToken[phone-a]",
        enabled=True,
    )

    targets = load_customer_push_targets(
        _PushDb(
            clientes=[cliente_pdv],
            users=[usuario_operacional, usuario_app],
            devices=[device_app],
        ),
        tenant_id=TENANT_ID,
        customer_id=77,
    )

    assert [target.token for target in targets] == ["ExponentPushToken[phone-a]"]


def test_load_customer_push_targets_prefers_app_user_email_over_operational_user_device():
    cliente_pdv = SimpleNamespace(
        id=77,
        tenant_id=TENANT_ID,
        user_id=999,
        nome="Lucas Guerra de Moraes",
        email="lcsgmoraes@gmail.com",
    )
    usuario_operacional = SimpleNamespace(
        id=999,
        tenant_id=TENANT_ID,
        email="loja@example.com",
        push_token=None,
    )
    usuario_app = SimpleNamespace(
        id=5,
        tenant_id=TENANT_ID,
        email="lcsgmoraes@gmail.com",
        push_token=None,
    )
    device_operacional = SimpleNamespace(
        id=8,
        user_id=999,
        tenant_id=TENANT_ID,
        expo_push_token="ExponentPushToken[store-user]",
        enabled=True,
    )
    device_app = SimpleNamespace(
        id=9,
        user_id=5,
        tenant_id=TENANT_ID,
        expo_push_token="ExponentPushToken[phone-a]",
        enabled=True,
    )

    targets = load_customer_push_targets(
        _PushDb(
            clientes=[cliente_pdv],
            users=[usuario_operacional, usuario_app],
            devices=[device_operacional, device_app],
        ),
        tenant_id=TENANT_ID,
        customer_id=77,
    )

    assert [target.token for target in targets] == ["ExponentPushToken[phone-a]"]
