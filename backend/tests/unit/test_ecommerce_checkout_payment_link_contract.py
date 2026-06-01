from pathlib import Path


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
