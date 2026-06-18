import os
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.security.jwt_compat import jwt
from starlette.requests import Request
from starlette.responses import PlainTextResponse

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ["DEBUG"] = "false"

from app.auth.core import ALGORITHM
from app.config import JWT_SECRET_KEY
from app.middlewares.tenant_middleware import TenantSecurityMiddleware


def _token(payload: dict) -> str:
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=ALGORITHM)


def _request(path: str, token: str | None = None) -> Request:
    headers = []
    if token:
        headers.append((b"authorization", f"Bearer {token}".encode("utf-8")))

    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "headers": headers,
            "scheme": "http",
            "server": ("testserver", 80),
            "client": ("testclient", 50000),
        }
    )


async def _call_next(_request: Request):
    return PlainTextResponse("ok")


async def _call_next_no_response(_request: Request):
    raise RuntimeError("No response returned.")


class _DisconnectedRequest:
    headers = {}
    url = SimpleNamespace(path="/produtos/vendaveis")

    async def is_disconnected(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_tenant_security_blocks_valid_jwt_without_tenant():
    middleware = TenantSecurityMiddleware(app=lambda scope, receive, send: None)
    response = await middleware.dispatch(
        _request("/vendas", _token({"sub": "1"})), _call_next
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_tenant_security_allows_valid_jwt_with_tenant():
    middleware = TenantSecurityMiddleware(app=lambda scope, receive, send: None)
    token = _token({"sub": "1", "tenant_id": str(uuid4())})
    response = await middleware.dispatch(_request("/vendas", token), _call_next)

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_tenant_security_allows_select_tenant_without_tenant():
    middleware = TenantSecurityMiddleware(app=lambda scope, receive, send: None)
    token = _token({"sub": "1", "tenant_id": None})
    response = await middleware.dispatch(
        _request("/api/auth/select-tenant", token), _call_next
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_tenant_security_returns_no_content_when_client_disconnects():
    middleware = TenantSecurityMiddleware(app=lambda scope, receive, send: None)
    response = await middleware.dispatch(_DisconnectedRequest(), _call_next_no_response)

    assert response.status_code == 204
