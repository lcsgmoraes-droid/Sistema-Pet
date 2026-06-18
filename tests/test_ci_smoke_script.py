from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SMOKE_SCRIPT = ROOT / "scripts" / "ci_smoke.py"


def _load_smoke_module():
    spec = importlib.util.spec_from_file_location("ci_smoke", SMOKE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FakeRoute:
    def __init__(self, path: str, methods: set[str]):
        self.path = path
        self.methods = methods


class FakeApp:
    routes = [
        FakeRoute("/health", {"GET"}),
        FakeRoute("/auth/login-multitenant", {"POST"}),
    ]


def test_assert_route_exists_accepts_registered_method():
    smoke = _load_smoke_module()

    smoke.assert_route_exists(FakeApp(), "/auth/login-multitenant", "POST")


def test_assert_route_exists_accepts_fastapi_included_router():
    from fastapi import APIRouter, FastAPI

    smoke = _load_smoke_module()
    router = APIRouter(prefix="/auth")

    @router.post("/login-multitenant")
    def login_multitenant():
        return {"ok": True}

    app = FastAPI()
    app.include_router(router)

    smoke.assert_route_exists(app, "/auth/login-multitenant", "POST")


def test_assert_route_exists_rejects_missing_method():
    smoke = _load_smoke_module()

    with pytest.raises(AssertionError, match="POST /health"):
        smoke.assert_route_exists(FakeApp(), "/health", "POST")


def test_audit_request_id_smoke_records_request_id(tmp_path):
    smoke = _load_smoke_module()

    result = smoke.run_audit_request_id_smoke(
        db_path=tmp_path / "audit-smoke.db",
        request_id="ci-test-request-id",
    )

    assert result["action"] == "business.smoke.audit_request_id"
    assert result["request_id"] == "ci-test-request-id"
