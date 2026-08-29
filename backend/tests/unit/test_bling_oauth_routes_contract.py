from starlette.requests import Request
from uuid import uuid4

from app.bling_oauth_routes import (
    _bling_redirect_uri,
    _encode_oauth_state,
    _html_erro,
    _validate_oauth_state,
    bling_oauth_callback,
    public_router,
)
from app.tenancy.context import clear_current_tenant, get_current_tenant


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "scheme": "http",
            "server": ("backend", 8000),
            "path": "/auth/bling/link-autorizacao",
            "headers": [],
        }
    )


def test_html_erro_escapes_message_content():
    html = _html_erro('<script>alert("x")</script>')

    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "&quot;x&quot;" in html


def test_bling_redirect_uri_uses_public_api_route(monkeypatch):
    monkeypatch.delenv("BLING_REDIRECT_URI", raising=False)
    monkeypatch.setenv("ECOMMERCE_PUBLIC_BASE_URL", "https://corepet.com.br/")

    assert (
        _bling_redirect_uri(_request())
        == "https://corepet.com.br/api/auth/bling/callback"
    )


def test_bling_redirect_uri_accepts_explicit_configuration(monkeypatch):
    monkeypatch.setenv(
        "BLING_REDIRECT_URI",
        "https://integracoes.example.com/bling/callback",
    )
    monkeypatch.setenv("ECOMMERCE_PUBLIC_BASE_URL", "https://corepet.com.br")

    assert (
        _bling_redirect_uri(_request())
        == "https://integracoes.example.com/bling/callback"
    )


def test_bling_oauth_state_is_signed_and_expires(monkeypatch):
    monkeypatch.setattr("app.bling_oauth_routes.time.time", lambda: 1_000)
    state = _encode_oauth_state(tenant_id=uuid4(), expires_in=60)

    assert _validate_oauth_state(state) is True

    monkeypatch.setattr("app.bling_oauth_routes.time.time", lambda: 1_061)
    assert _validate_oauth_state(state) is False
    assert _validate_oauth_state(f"{state}alterado") is False


def test_bling_oauth_callback_is_exposed_by_public_router():
    callback_paths = {
        route.path
        for route in public_router.routes
        if "GET" in (route.methods or set())
    }

    assert "/auth/bling/callback" in callback_paths


def test_bling_oauth_callback_salva_no_tenant_assinado(monkeypatch):
    tenant_id = uuid4()
    captured = {}
    clear_current_tenant()
    monkeypatch.setattr(
        "app.bling_oauth_routes._trocar_code_por_tokens",
        lambda *_args: {
            "access_token": "access-gabi",
            "refresh_token": "refresh-gabi",
            "expires_in": 3600,
        },
    )
    monkeypatch.setattr(
        "app.bling_oauth_routes._salvar_tokens",
        lambda *args, **kwargs: captured.update({"args": args, "kwargs": kwargs}),
    )

    response = bling_oauth_callback(
        request=_request(),
        code="authorization-code",
        state=_encode_oauth_state(tenant_id=tenant_id),
        db=object(),
    )

    assert response.status_code == 200
    assert captured["kwargs"]["tenant_id"] == tenant_id
    assert captured["args"] == ("access-gabi", "refresh-gabi")
    assert get_current_tenant() is None
