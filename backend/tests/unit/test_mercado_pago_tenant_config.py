import os
import inspect
from types import SimpleNamespace

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("ENVIRONMENT", "test")

from app.services.mercado_pago_checkout import (
    build_preference_payload,
    create_preference,
    fetch_payment,
)
from app.services.ecommerce_payment_config import (
    build_mercado_pago_webhook_url,
    decrypt_secret,
    encrypt_secret,
    resolve_mercado_pago_tenant_id_from_webhook_token,
    save_mercado_pago_config,
    serialize_mercado_pago_config,
)


def _pedido():
    return SimpleNamespace(
        pedido_id="PED-TENANT-001",
        tenant_id="180d9cbf-5dcb-4676-bf11-dcbd91ed444b",
        origem="app",
    )


def test_config_mercado_pago_mascara_segredos_e_expoe_webhook_url(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "tenant-secret-for-tests")
    config = SimpleNamespace(
        enabled=True,
        environment="production",
        public_key="APP_USR-public-key",
        access_token_encrypted=encrypt_secret("APP_USR-access-token"),
        webhook_secret_encrypted=encrypt_secret("webhook-secret"),
        oauth_client_id="tenant-oauth-client-id",
        oauth_client_secret_encrypted=encrypt_secret("tenant-oauth-client-secret"),
        webhook_token="mp_abc123",
        updated_at=None,
    )

    serialized = serialize_mercado_pago_config(
        config,
        base_url="https://corepet.com.br/",
    )

    assert serialized == {
        "provider": "mercadopago",
        "enabled": True,
        "environment": "production",
        "public_key": None,
        "public_key_configured": True,
        "public_key_preview": "APP_US...-key",
        "access_token_configured": True,
        "webhook_secret_configured": True,
        "oauth_client_id_configured": True,
        "oauth_client_id_preview": "tenant...t-id",
        "oauth_client_secret_configured": True,
        "oauth_available": True,
        "oauth_connected": False,
        "oauth_connected_at": None,
        "mercado_pago_user_id": None,
        "oauth_redirect_uri": "https://corepet.com.br/api/ecommerce-payment-config/mercadopago/oauth/callback",
        "webhook_url": "https://corepet.com.br/api/webhooks/mercadopago/mp_abc123",
        "updated_at": None,
    }
    assert "access_token" not in serialized
    assert "webhook_secret" not in serialized
    assert "APP_USR-public-key" not in serialized.values()
    assert decrypt_secret(config.access_token_encrypted) == "APP_USR-access-token"


def test_save_config_preserva_valores_sensiveis_quando_campos_vazios(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "tenant-secret-for-save-tests")
    config = SimpleNamespace(
        enabled=True,
        environment="production",
        public_key="APP_USR-existing-public-key",
        access_token_encrypted=encrypt_secret("existing-access-token"),
        webhook_secret_encrypted=encrypt_secret("existing-webhook-secret"),
        oauth_client_id="existing-client-id",
        oauth_client_secret_encrypted=encrypt_secret("existing-client-secret"),
        refresh_token_encrypted=None,
        access_token_expires_at=None,
        oauth_connected=False,
        oauth_connected_at=None,
        mercado_pago_user_id=None,
        oauth_scope=None,
        oauth_last_error=None,
        oauth_refresh_failed_at=None,
    )

    class Db:
        committed = False

        def commit(self):
            self.committed = True

        def refresh(self, _config):
            return None

    import app.services.ecommerce_payment_config as service

    monkeypatch.setattr(
        service, "get_mercado_pago_config", lambda db, tenant_id: config
    )
    db = Db()

    saved = save_mercado_pago_config(
        db,
        tenant_id="180d9cbf-5dcb-4676-bf11-dcbd91ed444b",
        user_id=1,
        enabled=True,
        environment="production",
        public_key=None,
        access_token=None,
        webhook_secret=None,
        oauth_client_id=None,
        oauth_client_secret=None,
    )

    assert saved.public_key == "APP_USR-existing-public-key"
    assert decrypt_secret(saved.access_token_encrypted) == "existing-access-token"
    assert decrypt_secret(saved.webhook_secret_encrypted) == "existing-webhook-secret"
    assert saved.oauth_client_id == "existing-client-id"
    assert (
        decrypt_secret(saved.oauth_client_secret_encrypted) == "existing-client-secret"
    )
    assert db.committed is True


def test_save_config_ativa_com_oauth_sem_access_token_para_permitir_conectar(
    monkeypatch,
):
    monkeypatch.setenv("JWT_SECRET_KEY", "tenant-secret-for-oauth-save-tests")
    config = SimpleNamespace(
        enabled=False,
        environment="production",
        public_key=None,
        access_token_encrypted=None,
        webhook_secret_encrypted=encrypt_secret("existing-webhook-secret"),
        oauth_client_id=None,
        oauth_client_secret_encrypted=None,
        refresh_token_encrypted=None,
        access_token_expires_at=None,
        oauth_connected=False,
        oauth_connected_at=None,
        mercado_pago_user_id=None,
        oauth_scope=None,
        oauth_last_error=None,
        oauth_refresh_failed_at=None,
    )

    class Db:
        def commit(self):
            return None

        def refresh(self, _config):
            return None

    import app.services.ecommerce_payment_config as service

    monkeypatch.setattr(
        service, "get_mercado_pago_config", lambda db, tenant_id: config
    )

    saved = save_mercado_pago_config(
        Db(),
        tenant_id="180d9cbf-5dcb-4676-bf11-dcbd91ed444b",
        user_id=1,
        enabled=True,
        environment="production",
        public_key=None,
        access_token=None,
        webhook_secret=None,
        oauth_client_id="tenant-client-id",
        oauth_client_secret="tenant-client-secret",
    )

    assert saved.enabled is True
    assert saved.oauth_client_id == "tenant-client-id"
    assert decrypt_secret(saved.oauth_client_secret_encrypted) == "tenant-client-secret"
    assert saved.access_token_encrypted is None


def test_preferencia_usa_webhook_especifico_do_tenant():
    webhook_url = build_mercado_pago_webhook_url(
        "tenant-token",
        base_url="https://corepet.com.br",
    )

    payload = build_preference_payload(
        pedido=_pedido(),
        total=99.9,
        forma_pagamento_tipo="pix",
        endereco_entrega="RETIRADA NA LOJA",
        tipo_retirada="app_loja",
        notification_url=webhook_url,
    )

    assert payload["notification_url"] == (
        "https://corepet.com.br/api/webhooks/mercadopago/tenant-token"
    )
    assert payload["metadata"]["tenant_id"] == "180d9cbf-5dcb-4676-bf11-dcbd91ed444b"


def test_sync_webhook_token_configura_setting_rls_transacional_no_postgres():
    import app.services.ecommerce_payment_config as service

    captured = {}

    class Connection:
        def execute(self, statement, params):
            captured["statement"] = str(statement)
            captured["params"] = params

    class Db:
        def get_bind(self):
            return SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))

        def connection(self):
            return Connection()

    synced = service.sync_mercado_pago_webhook_token(Db(), " mp_abc123 ")

    assert synced is True
    assert "set_config" in captured["statement"]
    assert "true" in captured["statement"]
    assert captured["params"] == {
        "setting_name": "app.payment_webhook_token",
        "setting_value": "mp_abc123",
    }


def test_sync_webhook_token_ignora_bancos_sem_rls():
    import app.services.ecommerce_payment_config as service

    class Db:
        def get_bind(self):
            return SimpleNamespace(dialect=SimpleNamespace(name="sqlite"))

        def connection(self):  # pragma: no cover - falha se for chamado
            raise AssertionError("sqlite nao deve tentar set_config")

    assert service.sync_mercado_pago_webhook_token(Db(), "mp_abc123") is False


def test_webhook_tenant_resolve_tenant_por_token_com_sql_tenant_safe(monkeypatch):
    import app.services.ecommerce_payment_config as service

    captured = {}

    def fake_sync(db, token):
        captured["sync"] = {"db": db, "token": token}
        return True

    def fake_execute(db, sql, params=None, **kwargs):
        captured["execute"] = {"db": db, "sql": sql, "params": params or {}, **kwargs}
        return ("180d9cbf-5dcb-4676-bf11-dcbd91ed444b",)

    monkeypatch.setattr(service, "sync_mercado_pago_webhook_token", fake_sync)
    monkeypatch.setattr(service, "execute_tenant_safe_one", fake_execute)

    db = object()
    tenant_id = resolve_mercado_pago_tenant_id_from_webhook_token(db, " mp_abc123 ")

    assert tenant_id == "180d9cbf-5dcb-4676-bf11-dcbd91ed444b"
    assert captured["sync"] == {"db": db, "token": "mp_abc123"}
    assert captured["execute"]["db"] is db
    assert "ecommerce_payment_gateway_configs" in captured["execute"]["sql"]
    assert "webhook_token" in captured["execute"]["sql"]
    assert captured["execute"]["params"] == {
        "provider": "mercadopago",
        "webhook_token": "mp_abc123",
    }
    assert captured["execute"]["require_tenant"] is False
    assert captured["execute"]["allow_global"] is True
    assert captured["execute"]["global_reason"]


def test_webhook_tenant_ativa_contexto_antes_de_carregar_runtime_config():
    from app.routes import ecommerce_webhooks

    source = inspect.getsource(ecommerce_webhooks.webhook_mercadopago_tenant)

    assert "resolve_mercado_pago_tenant_id_from_webhook_token" in source
    assert source.index(
        "resolve_mercado_pago_tenant_id_from_webhook_token"
    ) < source.index("runtime_config_from_webhook_token")
    assert source.index(
        "set_current_tenant(UUID(str(webhook_tenant_id)))"
    ) < source.index("runtime_config_from_webhook_token")


def test_create_preference_usa_access_token_do_tenant(monkeypatch):
    monkeypatch.delenv("MERCADO_PAGO_ACCESS_TOKEN", raising=False)
    captured = {}

    class Response:
        status_code = 201

        @staticmethod
        def json():
            return {
                "id": "pref_123",
                "init_point": "https://mercadopago.com.br/checkout",
                "sandbox_init_point": "https://sandbox.mercadopago.com.br/checkout",
            }

    def http_post(url, headers, json, timeout):
        captured.update(
            {"url": url, "headers": headers, "json": json, "timeout": timeout}
        )
        return Response()

    preference = create_preference(
        pedido=_pedido(),
        total=10,
        forma_pagamento_tipo="cartao_credito",
        endereco_entrega="Rua Teste, 1",
        tipo_retirada=None,
        access_token="APP_USR-tenant-token",
        notification_url="https://corepet.com.br/api/webhooks/mercadopago/tenant-token",
        use_sandbox=False,
        http_post=http_post,
    )

    assert captured["headers"]["Authorization"] == "Bearer APP_USR-tenant-token"
    assert captured["json"]["notification_url"].endswith("/tenant-token")
    assert preference["preference_id"] == "pref_123"
    assert preference["payment_url"] == "https://mercadopago.com.br/checkout"


def test_fetch_payment_usa_access_token_do_tenant(monkeypatch):
    monkeypatch.delenv("MERCADO_PAGO_ACCESS_TOKEN", raising=False)
    captured = {}

    class Response:
        status_code = 200

        @staticmethod
        def json():
            return {"id": "pay_123", "status": "approved"}

    def http_get(url, headers, timeout):
        captured.update({"url": url, "headers": headers, "timeout": timeout})
        return Response()

    payment = fetch_payment(
        "pay_123",
        access_token="APP_USR-tenant-token",
        http_get=http_get,
    )

    assert captured["headers"]["Authorization"] == "Bearer APP_USR-tenant-token"
    assert payment == {"id": "pay_123", "status": "approved"}
