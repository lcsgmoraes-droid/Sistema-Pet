from app.routes.ecommerce_checkout import (
    CheckoutFinalizarRequest,
    EcommerceIdentity,
    _classificar_forma_pagamento_online,
    _checkout_idempotency_payload,
    _pagamento_online_configurado,
    _request_hash,
)


def _payload(**overrides):
    data = {
        "cidade_destino": "Sao Paulo",
        "endereco_entrega": "Rua Teste, 123",
        "cupom": "MVP10",
        "tipo_retirada": None,
        "is_drive": False,
        "forma_pagamento_nome": "PIX",
        "origem": "web",
    }
    data.update(overrides)
    return CheckoutFinalizarRequest(**data)


def test_checkout_idempotency_payload_inclui_campos_operacionais():
    identity = EcommerceIdentity(
        user_id=42,
        tenant_id="180d9cbf-5dcb-4676-bf11-dcbd91ed444b",
    )

    data = _checkout_idempotency_payload(
        identity,
        _payload(tipo_retirada="proprio", is_drive=True, origem="app"),
    )

    assert data == {
        "user_id": 42,
        "tenant_id": "180d9cbf-5dcb-4676-bf11-dcbd91ed444b",
        "cidade_destino": "Sao Paulo",
        "endereco_entrega": "Rua Teste, 123",
        "cupom": "MVP10",
        "tipo_retirada": "proprio",
        "is_drive": True,
        "forma_pagamento_nome": "PIX",
        "origem": "app",
    }


def test_checkout_idempotency_hash_muda_ao_alterar_pagamento():
    identity = EcommerceIdentity(
        user_id=42,
        tenant_id="180d9cbf-5dcb-4676-bf11-dcbd91ed444b",
    )

    base = _checkout_idempotency_payload(identity, _payload(forma_pagamento_nome="PIX"))
    alterado = _checkout_idempotency_payload(
        identity,
        _payload(forma_pagamento_nome="Credito Visa 3x"),
    )

    assert _request_hash(base) != _request_hash(alterado)


def test_checkout_idempotency_hash_muda_ao_alterar_retirada_drive():
    identity = EcommerceIdentity(
        user_id=42,
        tenant_id="180d9cbf-5dcb-4676-bf11-dcbd91ed444b",
    )

    retirada = _checkout_idempotency_payload(
        identity,
        _payload(tipo_retirada="proprio", is_drive=False),
    )
    drive = _checkout_idempotency_payload(
        identity,
        _payload(tipo_retirada="proprio", is_drive=True),
    )

    assert _request_hash(retirada) != _request_hash(drive)


def test_checkout_aceita_somente_pagamentos_online():
    assert _classificar_forma_pagamento_online("PIX") == "pix"
    assert _classificar_forma_pagamento_online("Débito Visa") == "cartao_debito"
    assert _classificar_forma_pagamento_online("Credito Mastercard 3x") == "cartao_credito"
    assert _classificar_forma_pagamento_online("Dinheiro") is None
    assert _classificar_forma_pagamento_online(None) is None


def test_checkout_gateway_online_fica_desligado_sem_intermediadora(monkeypatch):
    monkeypatch.delenv("ECOMMERCE_PAYMENT_GATEWAY_ENABLED", raising=False)
    monkeypatch.delenv("ECOMMERCE_PAYMENT_PROVIDER", raising=False)

    assert _pagamento_online_configurado() is False


def test_checkout_gateway_online_exige_flag_e_provider(monkeypatch):
    monkeypatch.setenv("ECOMMERCE_PAYMENT_GATEWAY_ENABLED", "true")
    monkeypatch.delenv("ECOMMERCE_PAYMENT_PROVIDER", raising=False)
    assert _pagamento_online_configurado() is False

    monkeypatch.setenv("ECOMMERCE_PAYMENT_PROVIDER", "gateway-futuro")
    assert _pagamento_online_configurado() is True
