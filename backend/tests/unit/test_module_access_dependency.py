from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.security import module_access


class _TrialQuery:
    def __init__(self, model, tenant):
        self.model = model
        self.tenant = tenant

    def filter(self, *criteria):
        self.criteria = criteria
        return self

    def first(self):
        if self.model is module_access.Tenant:
            return self.tenant
        return None

    def all(self):
        return []


class _TrialDb:
    def __init__(self, tenant):
        self.tenant = tenant

    def query(self, model):
        return _TrialQuery(model, self.tenant)


def _user(**overrides):
    data = {
        "is_superadmin": False,
        "is_system_admin": False,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _credentials():
    return SimpleNamespace(credentials="token-teste")


def _client_com_modulo_bling(path: str) -> TestClient:
    app = FastAPI()
    app.dependency_overrides[module_access.get_session] = lambda: object()

    @app.post(
        path, dependencies=[Depends(module_access.require_active_module("bling"))]
    )
    def endpoint_teste():
        return {"status": "ok"}

    return TestClient(app)


def _patch_auth(monkeypatch, user, tenant_id):
    monkeypatch.setattr(
        module_access, "get_current_user", lambda credentials, session: user
    )

    async def fake_get_current_user_and_tenant(credentials, user, db):
        return user, tenant_id

    monkeypatch.setattr(
        module_access,
        "get_current_user_and_tenant",
        fake_get_current_user_and_tenant,
    )


def test_load_active_modules_libera_experiencia_completa_durante_trial():
    agora = datetime(2026, 7, 18, tzinfo=timezone.utc)
    tenant = SimpleNamespace(
        plan="pet-start",
        modulos_ativos="[]",
        billing_status="trial",
        trial_started_at=agora,
        trial_ends_at=agora + timedelta(days=30),
        subscription_source="manual",
        subscription_activated_at=None,
    )

    ativos = module_access._load_active_modules(_TrialDb(tenant), "tenant-1", agora)

    assert "compras" in ativos
    assert "veterinario" in ativos
    assert "banho_tosa" in ativos
    assert "bling" not in ativos


@pytest.mark.asyncio
async def test_require_active_module_blocks_tenant_without_module(monkeypatch):
    user = _user()
    _patch_auth(monkeypatch, user, "tenant-1")
    monkeypatch.setattr(module_access, "_load_active_modules", lambda db, tenant_id: [])

    dependency = module_access.require_active_module("compras")

    with pytest.raises(HTTPException) as exc:
        await dependency(credentials=_credentials(), db=object())

    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "module_not_enabled"
    assert exc.value.detail["modulo"] == "compras"


@pytest.mark.asyncio
async def test_require_active_module_allows_tenant_with_module(monkeypatch):
    user = _user()
    _patch_auth(monkeypatch, user, "tenant-1")
    monkeypatch.setattr(
        module_access, "_load_active_modules", lambda db, tenant_id: ["compras"]
    )

    dependency = module_access.require_active_module("compras")

    assert await dependency(credentials=_credentials(), db=object()) is None


@pytest.mark.asyncio
async def test_require_active_module_superadmin_bypasses_plan(monkeypatch):
    user = _user(is_superadmin=True)
    _patch_auth(monkeypatch, user, "tenant-1")

    def fail_if_called(db, tenant_id):  # pragma: no cover - should not run
        raise AssertionError("superadmin should not query tenant module plan")

    monkeypatch.setattr(module_access, "_load_active_modules", fail_if_called)

    dependency = module_access.require_active_module("compras")

    assert await dependency(credentials=_credentials(), db=object()) is None


@pytest.mark.asyncio
async def test_require_active_module_requires_tenant_context(monkeypatch):
    user = _user()
    _patch_auth(monkeypatch, user, None)
    monkeypatch.setattr(
        module_access, "_load_active_modules", lambda db, tenant_id: ["compras"]
    )

    dependency = module_access.require_active_module("compras")

    with pytest.raises(HTTPException) as exc:
        await dependency(credentials=_credentials(), db=object())

    assert exc.value.status_code == 403
    assert exc.value.detail == "Tenant obrigatorio para acessar este modulo"


@pytest.mark.asyncio
async def test_require_active_module_rejects_missing_credentials():
    dependency = module_access.require_active_module("compras")

    with pytest.raises(HTTPException) as exc:
        await dependency(credentials=None, db=object())

    assert exc.value.status_code == 403
    assert exc.value.detail == "Not authenticated"


@pytest.mark.parametrize("path", ["/integracoes/bling/pedido", "/integracoes/bling/nf"])
def test_require_active_module_allows_public_bling_webhooks_without_credentials(path):
    client = _client_com_modulo_bling(path)

    response = client.post(path)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_require_active_module_keeps_other_bling_routes_private_without_credentials():
    client = _client_com_modulo_bling("/integracoes/bling/pedidos")

    response = client.post("/integracoes/bling/pedidos")

    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"


def test_require_active_module_rejects_unknown_module():
    with pytest.raises(ValueError, match="Modulo comercial desconhecido"):
        module_access.require_active_module("modulo_fantasma")
