import os
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("ENVIRONMENT", "test")

from app.routes.ecommerce_checkout import _payment_info_for_pedido
from app.tenancy.context import (
    clear_current_tenant,
    get_current_tenant,
    set_current_tenant,
)


ROOT = Path(__file__).resolve().parents[3]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_checkout_history_returns_stored_payment_link():
    source = _read("backend/app/routes/ecommerce_checkout.py")

    assert "_payment_info_for_pedido(db, pedido)" in source
    assert '"payment_url": pedido.payment_url' in source
    assert '"payment_preference_id": pedido.payment_preference_id' in source
    assert '"payment_provider": pedido.payment_provider' in source


def test_checkout_history_falls_back_to_idempotency_response_for_existing_orders():
    source = _read("backend/app/routes/ecommerce_checkout.py")

    assert "IdempotencyKey.response_body.contains(pedido.pedido_id)" in source
    assert "json.loads(idem_row.response_body" in source
    assert 'response.get("payment_url")' in source


def test_checkout_history_ativa_tenant_antes_do_fallback_idempotente():
    tenant_id = UUID("180d9cbf-5dcb-4676-bf11-dcbd91ed444b")
    seen_tenants = []

    class Query:
        def filter(self, *_args):
            return self

        def order_by(self, *_args):
            return self

        def limit(self, *_args):
            return self

        def all(self):
            return []

    class Db:
        def query(self, *_args):
            seen_tenants.append(get_current_tenant())
            return Query()

    pedido = SimpleNamespace(
        cliente_id=123,
        tenant_id=str(tenant_id),
        pedido_id="PED-001",
        payment_provider=None,
        payment_preference_id=None,
        payment_url=None,
    )

    clear_current_tenant()
    try:
        assert _payment_info_for_pedido(Db(), pedido) == {
            "payment_provider": None,
            "payment_preference_id": None,
            "payment_url": None,
        }
    finally:
        clear_current_tenant()

    assert seen_tenants == [tenant_id]


def test_checkout_history_restaura_tenant_anterior_apos_fallback_idempotente():
    previous_tenant = UUID("9a982f52-b149-4e87-812d-59b9a4010f7e")
    pedido_tenant = UUID("180d9cbf-5dcb-4676-bf11-dcbd91ed444b")

    class Query:
        def filter(self, *_args):
            return self

        def order_by(self, *_args):
            return self

        def limit(self, *_args):
            return self

        def all(self):
            return []

    class Db:
        def query(self, *_args):
            return Query()

    pedido = SimpleNamespace(
        cliente_id=123,
        tenant_id=str(pedido_tenant),
        pedido_id="PED-001",
        payment_provider=None,
        payment_preference_id=None,
        payment_url=None,
    )

    set_current_tenant(previous_tenant)
    try:
        _payment_info_for_pedido(Db(), pedido)
        assert get_current_tenant() == previous_tenant
    finally:
        clear_current_tenant()


def test_checkout_finalization_persists_mercado_pago_link_on_order():
    source = _read("backend/app/routes/ecommerce_checkout.py")

    assert 'carrinho.payment_provider = "mercadopago"' in source
    assert 'carrinho.payment_preference_id = preference.get("preference_id")' in source
    assert 'carrinho.payment_url = preference.get("payment_url")' in source


def test_pedido_model_has_payment_link_fields():
    source = _read("backend/app/pedido_models.py")

    assert "payment_provider = Column(String" in source
    assert "payment_preference_id = Column(String" in source
    assert "payment_url = Column(String" in source
