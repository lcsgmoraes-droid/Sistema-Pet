from datetime import datetime, timedelta
import os
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("ENVIRONMENT", "test")

from fastapi.testclient import TestClient

from app.main import app
from app.services.ecommerce_payment_config import (
    build_mercado_pago_oauth_authorization_url,
    decrypt_secret,
    encode_mercado_pago_oauth_state,
    ensure_mercado_pago_access_token_fresh,
    encrypt_secret,
    exchange_mercado_pago_oauth_code,
    is_mercado_pago_oauth_available,
    save_mercado_pago_oauth_tokens,
    serialize_mercado_pago_config,
    validate_mercado_pago_oauth_state,
)


TENANT_ID = "180d9cbf-5dcb-4676-bf11-dcbd91ed444b"


def test_callback_oauth_mercado_pago_nao_exige_token_do_erp():
    client = TestClient(app, follow_redirects=False)

    response = client.get(
        "/ecommerce-payment-config/mercadopago/oauth/callback",
        params={"state": "invalido", "code": "TG-code"},
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("https://corepet.com.br/ecommerce/configuracoes")
    assert "mercadopago_oauth=error" in response.headers["location"]


def test_oauth_authorization_url_usa_client_id_redirect_e_state_assinado(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "oauth-state-secret")
    monkeypatch.setenv("MERCADO_PAGO_OAUTH_CLIENT_ID", "123456789")
    monkeypatch.setenv("MERCADO_PAGO_OAUTH_CLIENT_SECRET", "client-secret")

    auth_url = build_mercado_pago_oauth_authorization_url(
        tenant_id=TENANT_ID,
        user_id=42,
        redirect_uri="https://corepet.com.br/api/ecommerce-payment-config/mercadopago/oauth/callback",
    )

    parsed = urlparse(auth_url)
    params = parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert parsed.netloc == "auth.mercadopago.com"
    assert parsed.path == "/authorization"
    assert params["client_id"] == ["123456789"]
    assert params["response_type"] == ["code"]
    assert params["platform_id"] == ["mp"]
    assert params["redirect_uri"] == [
        "https://corepet.com.br/api/ecommerce-payment-config/mercadopago/oauth/callback"
    ]

    state_payload = validate_mercado_pago_oauth_state(params["state"][0])
    assert state_payload["tenant_id"] == TENANT_ID
    assert state_payload["user_id"] == 42


def test_oauth_state_rejeita_alteracao_do_payload(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "oauth-state-secret")
    state = encode_mercado_pago_oauth_state(tenant_id=TENANT_ID, user_id=42)
    payload, signature = state.split(".", 1)

    tampered = f"{payload[:-2]}xx.{signature}"

    assert validate_mercado_pago_oauth_state(tampered) is None


def test_oauth_available_exige_client_id_e_secret(monkeypatch):
    monkeypatch.delenv("MERCADO_PAGO_OAUTH_CLIENT_ID", raising=False)
    monkeypatch.delenv("MERCADO_PAGO_OAUTH_CLIENT_SECRET", raising=False)

    assert is_mercado_pago_oauth_available() is False

    monkeypatch.setenv("MERCADO_PAGO_OAUTH_CLIENT_ID", "client-id")
    monkeypatch.setenv("MERCADO_PAGO_OAUTH_CLIENT_SECRET", "client-secret")

    assert is_mercado_pago_oauth_available() is True


def test_oauth_pode_usar_client_id_e_secret_do_tenant(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "oauth-config-secret")
    monkeypatch.delenv("MERCADO_PAGO_OAUTH_CLIENT_ID", raising=False)
    monkeypatch.delenv("MERCADO_PAGO_OAUTH_CLIENT_SECRET", raising=False)
    config = SimpleNamespace(
        oauth_client_id="tenant-client-id",
        oauth_client_secret_encrypted=encrypt_secret("tenant-client-secret"),
    )

    assert is_mercado_pago_oauth_available(config) is True

    auth_url = build_mercado_pago_oauth_authorization_url(
        tenant_id=TENANT_ID,
        user_id=42,
        redirect_uri="https://corepet.com.br/api/ecommerce-payment-config/mercadopago/oauth/callback",
        config=config,
    )

    params = parse_qs(urlparse(auth_url).query)
    assert params["client_id"] == ["tenant-client-id"]


def test_exchange_oauth_usa_client_secret_do_tenant(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "oauth-exchange-secret")
    monkeypatch.delenv("MERCADO_PAGO_OAUTH_CLIENT_ID", raising=False)
    monkeypatch.delenv("MERCADO_PAGO_OAUTH_CLIENT_SECRET", raising=False)
    config = SimpleNamespace(
        oauth_client_id="tenant-client-id",
        oauth_client_secret_encrypted=encrypt_secret("tenant-client-secret"),
    )
    captured = {}

    class Response:
        status_code = 200
        text = "{}"

        @staticmethod
        def json():
            return {"access_token": "oauth-access-token", "expires_in": 21600}

    def http_post(url, headers, json, timeout):
        captured.update({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return Response()

    payload = exchange_mercado_pago_oauth_code(
        code="oauth-code",
        redirect_uri="https://corepet.com.br/api/ecommerce-payment-config/mercadopago/oauth/callback",
        config=config,
        http_post=http_post,
    )

    assert payload["access_token"] == "oauth-access-token"
    assert captured["json"]["client_id"] == "tenant-client-id"
    assert captured["json"]["client_secret"] == "tenant-client-secret"


def test_salva_tokens_oauth_criptografados_no_tenant(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "oauth-token-secret")
    config = SimpleNamespace(
        access_token_encrypted=None,
        refresh_token_encrypted=None,
        access_token_expires_at=None,
        oauth_connected=False,
        oauth_connected_at=None,
        mercado_pago_user_id=None,
        oauth_scope=None,
        oauth_last_error=None,
        oauth_refresh_failed_at=None,
    )

    save_mercado_pago_oauth_tokens(
        config,
        {
            "access_token": "APP_USR-oauth-access",
            "refresh_token": "oauth-refresh",
            "expires_in": 21600,
            "user_id": 987654321,
            "scope": "offline_access read write",
        },
        connected_at=datetime(2026, 6, 1, 10, 0, 0),
    )

    assert config.oauth_connected is True
    assert config.mercado_pago_user_id == "987654321"
    assert config.oauth_scope == "offline_access read write"
    assert decrypt_secret(config.access_token_encrypted) == "APP_USR-oauth-access"
    assert decrypt_secret(config.refresh_token_encrypted) == "oauth-refresh"
    assert config.access_token_expires_at == datetime(2026, 6, 1, 16, 0, 0)
    assert config.oauth_last_error is None


def test_refresh_oauth_atualiza_access_token_expirado(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "oauth-refresh-secret")
    monkeypatch.setenv("MERCADO_PAGO_OAUTH_CLIENT_ID", "client-id")
    monkeypatch.setenv("MERCADO_PAGO_OAUTH_CLIENT_SECRET", "client-secret")
    captured = {}
    config = SimpleNamespace(
        access_token_encrypted=None,
        refresh_token_encrypted=None,
        access_token_expires_at=datetime.utcnow() - timedelta(minutes=1),
        oauth_connected=True,
        oauth_connected_at=datetime.utcnow() - timedelta(hours=1),
        mercado_pago_user_id="987654321",
        oauth_scope=None,
        oauth_last_error=None,
        oauth_refresh_failed_at=None,
    )
    save_mercado_pago_oauth_tokens(
        config,
        {
            "access_token": "old-access",
            "refresh_token": "old-refresh",
            "expires_in": 1,
            "user_id": "987654321",
        },
        connected_at=datetime.utcnow() - timedelta(hours=1),
    )
    config.access_token_expires_at = datetime.utcnow() - timedelta(minutes=1)

    class Response:
        status_code = 200
        text = "{}"

        @staticmethod
        def json():
            return {
                "access_token": "new-access",
                "refresh_token": "new-refresh",
                "expires_in": 21600,
                "user_id": "987654321",
            }

    def http_post(url, headers, json, timeout):
        captured.update({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return Response()

    class Db:
        committed = False

        def commit(self):
            self.committed = True

    db = Db()
    token = ensure_mercado_pago_access_token_fresh(db, config, http_post=http_post)

    assert token == "new-access"
    assert captured["url"] == "https://api.mercadopago.com/oauth/token"
    assert captured["json"]["grant_type"] == "refresh_token"
    assert captured["json"]["refresh_token"] == "old-refresh"
    assert decrypt_secret(config.refresh_token_encrypted) == "new-refresh"
    assert db.committed is True


def test_serialize_informa_status_oauth_sem_expor_tokens(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "oauth-serialize-secret")
    config = SimpleNamespace(
        enabled=True,
        environment="production",
        public_key=None,
        access_token_encrypted="",
        webhook_secret_encrypted="",
        webhook_token="mp_tenant",
        refresh_token_encrypted=None,
        oauth_connected=True,
        oauth_connected_at=datetime(2026, 6, 1, 10, 0, 0),
        mercado_pago_user_id="987654321",
        updated_at=None,
    )
    save_mercado_pago_oauth_tokens(
        config,
        {"access_token": "oauth-access", "refresh_token": "oauth-refresh", "expires_in": 21600},
        connected_at=datetime(2026, 6, 1, 10, 0, 0),
    )

    serialized = serialize_mercado_pago_config(config, base_url="https://corepet.com.br")

    assert serialized["oauth_available"] is False
    assert serialized["oauth_connected"] is True
    assert serialized["oauth_connected_at"] == "2026-06-01T10:00:00"
    assert serialized["mercado_pago_user_id"] == "987654321"
    assert serialized["access_token_configured"] is True
    assert "access_token" not in serialized
    assert "refresh_token" not in serialized
