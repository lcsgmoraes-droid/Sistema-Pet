from types import SimpleNamespace
from uuid import uuid4

from jose import jwt

from app.auth.core import ALGORITHM
from app.config import JWT_SECRET_KEY
from app.routes.ecommerce_auth import (
    _extract_tenant_id_from_request,
    _get_current_ecommerce_user,
)
from app.routes.ecommerce_cart import _current_identity as cart_current_identity
from app.routes.ecommerce_checkout import _current_identity as checkout_current_identity
from app.routes.ecommerce_entregador import _get_entregador_cliente
from app.routes.ecommerce_notify_routes import _resolve_notify_tenant
from app.routes.ecommerce_public import _get_active_tenant
from app.tenancy.context import clear_current_tenant, get_current_tenant


class _Query:
    def __init__(self, result):
        self.result = result

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.result


class _Db:
    def __init__(self, *results):
        self.results = list(results)

    def query(self, *_args, **_kwargs):
        return _Query(self.results.pop(0))


def _token(user_id: int, tenant_id) -> str:
    return jwt.encode(
        {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "token_type": "ecommerce_customer",
        },
        JWT_SECRET_KEY,
        algorithm=ALGORITHM,
    )


def test_extract_tenant_id_from_request_sets_tenant_context():
    tenant_id = uuid4()
    clear_current_tenant()

    request = SimpleNamespace(headers={"X-Tenant-ID": str(tenant_id)})

    assert _extract_tenant_id_from_request(request) == tenant_id
    assert get_current_tenant() == tenant_id


def test_get_current_ecommerce_user_sets_tenant_context_from_token():
    tenant_id = uuid4()
    user = SimpleNamespace(id=123, tenant_id=tenant_id, is_active=True)
    user_tenant = SimpleNamespace(user_id=user.id, tenant_id=tenant_id, is_active=True)
    tenant = SimpleNamespace(id=tenant_id, status="active")
    credentials = SimpleNamespace(credentials=_token(user.id, tenant_id))
    clear_current_tenant()

    current_user = _get_current_ecommerce_user(credentials=credentials, db=_Db(user, user_tenant, tenant))

    assert current_user is user
    assert get_current_tenant() == tenant_id


def test_cart_and_checkout_identity_use_validated_ecommerce_user():
    tenant_id = uuid4()
    user = SimpleNamespace(id=123, tenant_id=tenant_id, is_active=True)
    cart_identity = cart_current_identity(current_user=user)
    checkout_identity = checkout_current_identity(current_user=user)

    assert cart_identity.user_id == user.id
    assert cart_identity.tenant_id == str(tenant_id)
    assert checkout_identity.user_id == user.id
    assert checkout_identity.tenant_id == str(tenant_id)


def test_get_entregador_cliente_uses_validated_ecommerce_user_context():
    tenant_id = uuid4()
    user = SimpleNamespace(id=123, tenant_id=tenant_id, is_active=True)
    cliente = SimpleNamespace(id=456, tenant_id=str(tenant_id), user_id=user.id, is_entregador=True)
    clear_current_tenant()

    entregador = _get_entregador_cliente(current_user=user, db=_Db(cliente))

    assert entregador is cliente


def test_get_active_public_tenant_sets_tenant_context():
    tenant_id = uuid4()
    tenant = SimpleNamespace(id=tenant_id, status="active")
    clear_current_tenant()

    active_tenant = _get_active_tenant(_Db(tenant), ("id", str(tenant_id)))

    assert active_tenant is tenant
    assert get_current_tenant() == tenant_id


def test_notify_tenant_resolver_accepts_slug_without_uuid_query_error():
    tenant_id = uuid4()
    tenant = SimpleNamespace(id=tenant_id, status="active", ecommerce_slug="loja-teste")

    resolved = _resolve_notify_tenant(_Db(tenant), "loja-teste")

    assert resolved is tenant
