from uuid import uuid4

from starlette.requests import Request

from app.services.error_event_reporter import _extract_identity


def _request(path: str, headers: dict[str, str] | None = None) -> Request:
    raw_headers = [
        (key.lower().encode("latin-1"), value.encode("latin-1"))
        for key, value in (headers or {}).items()
    ]
    return Request(
        {
            "type": "http",
            "method": "POST",
            "scheme": "http",
            "server": ("testserver", 80),
            "client": ("127.0.0.1", 12345),
            "path": path,
            "query_string": b"",
            "headers": raw_headers,
        }
    )


def test_extract_identity_uses_bling_webhook_tenant_for_bling_routes(monkeypatch):
    tenant_id = str(uuid4())
    monkeypatch.setenv("BLING_WEBHOOK_TENANT_ID", tenant_id)

    identity = _extract_identity(_request("/integracoes/bling/pedido"))

    assert identity["tenant_id"] == tenant_id
    assert identity["tenant_source"] == "bling_webhook_env"


def test_extract_identity_prefers_request_state_over_route_fallback(monkeypatch):
    fallback_tenant_id = str(uuid4())
    state_tenant_id = str(uuid4())
    monkeypatch.setenv("BLING_WEBHOOK_TENANT_ID", fallback_tenant_id)
    request = _request("/integracoes/bling/pedido")
    request.state.tenant_id = state_tenant_id
    request.state.tenant_source = "route"

    identity = _extract_identity(request)

    assert identity["tenant_id"] == state_tenant_id
    assert identity["tenant_source"] == "route"


def test_extract_identity_does_not_assign_public_route_to_bling_tenant(monkeypatch):
    monkeypatch.setenv("BLING_WEBHOOK_TENANT_ID", str(uuid4()))

    identity = _extract_identity(_request("/health"))

    assert identity["tenant_id"] is None
    assert identity["tenant_source"] is None
