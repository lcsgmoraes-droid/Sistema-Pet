import inspect

from app.routes import ecommerce_checkout, ecommerce_webhooks
from app.services import customer_order_history


def test_checkout_pedidos_route_uses_customer_order_history_service():
    source = inspect.getsource(ecommerce_checkout.listar_pedidos_cliente)

    assert "list_customer_order_history" in source
    assert "user_id=identity.user_id" in source
    assert "tenant_id=tenant_id" in source


def test_customer_order_history_queries_only_cliente_user_id_scope():
    source = inspect.getsource(customer_order_history.list_customer_order_history)

    assert "Cliente.user_id == user_id" in source
    assert "Pedido.cliente_id == user_id" in source
    assert "Venda.cliente_id.in_(cliente_ids)" in source
    assert "Venda.tenant_id == tenant_id" in source


def test_webhook_payment_status_triggers_order_push():
    module_source = inspect.getsource(ecommerce_webhooks)
    tenant_webhook_source = inspect.getsource(
        ecommerce_webhooks.webhook_mercadopago_tenant
    )

    assert "notify_order_event" in module_source
    assert "_notify_payment_status_change" in tenant_webhook_source
    assert "payment_approved" in module_source
    assert "payment_in_analysis" in module_source
    assert "payment_failed" in module_source
