from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Any
import uuid


ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"


class _EmptyQuery:
    def filter(self, *args: Any, **kwargs: Any) -> "_EmptyQuery":
        return self

    def first(self) -> None:
        return None

    def all(self) -> list[Any]:
        return []


class _FakeDbSession:
    def query(self, *args: Any, **kwargs: Any) -> _EmptyQuery:
        return _EmptyQuery()

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None


def assert_route_exists(app: Any, path: str, method: str) -> None:
    expected_method = method.upper()
    for route in app.routes:
        if getattr(route, "path", None) == path and expected_method in getattr(route, "methods", set()):
            return
    raise AssertionError(f"Rota obrigatoria ausente: {expected_method} {path}")


def configure_backend_smoke_env() -> None:
    os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
    os.environ.setdefault("ENVIRONMENT", "testing")
    os.environ.setdefault("DEBUG", "false")
    os.environ.setdefault("JWT_SECRET_KEY", "ci-smoke-secret-key-with-more-than-32-characters")
    os.environ.setdefault("EMAIL_VERIFICATION_REQUIRED", "false")
    os.environ.setdefault("BLING_SYNC_SCHEDULER_ENABLED", "false")
    os.environ.setdefault("SEFAZ_IMPORTACAO_AUTOMATICA", "false")


def run_backend_smoke() -> None:
    configure_backend_smoke_env()
    sys.path.insert(0, str(BACKEND_ROOT))

    from fastapi.testclient import TestClient

    import app.main as backend_main
    from app.auth_routes_multitenant import get_session as auth_get_session

    app = backend_main.app
    assert_route_exists(app, "/health", "GET")
    assert_route_exists(app, "/auth/login-multitenant", "POST")

    app.dependency_overrides[auth_get_session] = lambda: _FakeDbSession()
    client = TestClient(app)

    health_response = client.get("/health")
    assert health_response.status_code == 200, health_response.text

    auth_payload = {
        "email": "ci-smoke@example.com",
        "pass" + "word": f"invalid-{uuid.uuid4()}",
    }
    auth_response = client.post("/auth/login-multitenant", json=auth_payload)
    assert auth_response.status_code == 401, auth_response.text

    print("Backend smoke OK: /health e /auth/login-multitenant")


def main() -> int:
    run_backend_smoke()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
