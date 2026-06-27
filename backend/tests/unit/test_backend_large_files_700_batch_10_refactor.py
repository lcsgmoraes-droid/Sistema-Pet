from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
TARGETS = [
    "app/routes/ecommerce_checkout.py",
    "app/routes/ecommerce_checkout_support.py",
]


def _line_count(relative: str) -> int:
    return len((BACKEND_ROOT / relative).read_text(encoding="utf-8").splitlines())


def test_ecommerce_checkout_batch_10_modules_ficam_abaixo_de_700_linhas():
    assert {relative: _line_count(relative) for relative in TARGETS} == {
        relative: count
        for relative in TARGETS
        if (count := _line_count(relative)) <= 700
    }


def test_ecommerce_checkout_facade_preserva_helpers_publicos():
    from app.routes import ecommerce_checkout
    from app.routes import ecommerce_checkout_support

    assert (
        ecommerce_checkout.CheckoutFinalizarRequest
        is ecommerce_checkout_support.CheckoutFinalizarRequest
    )
    assert (
        ecommerce_checkout.EcommerceIdentity
        is ecommerce_checkout_support.EcommerceIdentity
    )
    assert ecommerce_checkout._request_hash is ecommerce_checkout_support._request_hash
    assert (
        ecommerce_checkout._checkout_idempotency_payload
        is ecommerce_checkout_support._checkout_idempotency_payload
    )
    assert (
        ecommerce_checkout._frete_local_por_cidade
        is ecommerce_checkout_support._frete_local_por_cidade
    )


def test_ecommerce_checkout_rotas_publicas_permanecem_no_router():
    from app.routes import ecommerce_checkout

    routes = {
        (route.path, method)
        for route in ecommerce_checkout.router.routes
        for method in getattr(route, "methods", set())
    }

    assert ("/checkout/formas-pagamento", "GET") in routes
    assert ("/checkout/calcular-frete", "POST") in routes
    assert ("/checkout/resumo", "GET") in routes
    assert ("/checkout/finalizar", "POST") in routes
    assert ("/checkout/pedidos", "GET") in routes
    assert ("/checkout/pedido/{pedido_id}/status", "GET") in routes
    assert ("/checkout/pedido/{pedido_id}/cancelar", "POST") in routes
    assert ("/checkout/pedido/{pedido_id}/drive-cheguei", "POST") in routes


def test_ecommerce_checkout_mantem_fallback_de_pagamento_no_router_principal():
    source = (BACKEND_ROOT / "app/routes/ecommerce_checkout.py").read_text(
        encoding="utf-8"
    )

    assert "_payment_info_for_pedido(db, pedido)" in source
    assert "IdempotencyKey.response_body.contains(pedido.pedido_id)" in source
    assert 'carrinho.payment_url = preference.get("payment_url")' in source
