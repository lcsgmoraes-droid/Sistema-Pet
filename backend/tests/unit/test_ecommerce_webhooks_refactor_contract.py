from pathlib import Path


EXPECTED_WEBHOOK_PATHS = {
    "/webhooks/pagarme",
    "/webhooks/mercadopago/{webhook_token}",
    "/webhooks/mercadopago",
}


def _route_paths(router):
    return {getattr(route, "path", None) for route in router.routes}


def test_ecommerce_webhooks_preserva_paths_publicos():
    from app.routes.ecommerce_webhooks import router

    assert EXPECTED_WEBHOOK_PATHS.issubset(_route_paths(router))


def test_ecommerce_webhooks_delega_blocos_extraidos():
    from app.routes import ecommerce_webhooks
    from app.routes.ecommerce_webhooks import payment as payment_helpers
    from app.routes.ecommerce_webhooks import sales as sales_helpers
    from app.routes.ecommerce_webhooks import security as security_helpers

    assert ecommerce_webhooks._get_signature_config is (
        security_helpers._get_signature_config
    )
    assert ecommerce_webhooks._find_pedido_for_payment is (
        payment_helpers._find_pedido_for_payment
    )
    assert ecommerce_webhooks._extrair_pagamento_do_webhook is (
        payment_helpers._extrair_pagamento_do_webhook
    )
    assert ecommerce_webhooks._integrar_venda_ao_motor is (
        sales_helpers._integrar_venda_ao_motor
    )


def test_ecommerce_webhooks_modulos_ficam_abaixo_de_700_linhas():
    backend_root = Path(__file__).resolve().parents[2]
    limites = {
        "app/routes/ecommerce_webhooks.py": 700,
        "app/routes/ecommerce_webhooks_security.py": 700,
        "app/routes/ecommerce_webhooks_payment.py": 700,
        "app/routes/ecommerce_webhooks_sales.py": 700,
    }

    for rel_path, limite in limites.items():
        path = backend_root / rel_path
        linhas = path.read_text(encoding="utf-8").splitlines()
        assert len(linhas) <= limite, f"{rel_path} tem {len(linhas)} linhas"
