from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _read_frontend_source(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_ecommerce_orders_poll_pending_orders_until_webhook_updates_status():
    source = _read_frontend_source("frontend/src/pages/ecommerce/useEcommerceOrders.js")

    assert "PENDING_ORDER_POLL_MS" in source
    assert "setInterval(loadOrdersDetailed, PENDING_ORDER_POLL_MS)" in source
    assert 'pedido?.status === "pendente"' in source
    assert "clearInterval(interval)" in source
