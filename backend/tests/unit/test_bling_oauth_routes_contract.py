from starlette.requests import Request

from app.bling_oauth_routes import (
    _bling_redirect_uri,
    _encode_oauth_state,
    _html_erro,
    _validate_oauth_state,
    public_router,
)


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
    state = _encode_oauth_state(expires_in=60)

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
