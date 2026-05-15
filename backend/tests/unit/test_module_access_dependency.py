from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.security import module_access


def _user(**overrides):
    data = {
        "is_superadmin": False,
        "is_system_admin": False,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _credentials():
    return SimpleNamespace(credentials="token-teste")


def _patch_auth(monkeypatch, user, tenant_id):
    monkeypatch.setattr(module_access, "get_current_user", lambda credentials, session: user)

    async def fake_get_current_user_and_tenant(credentials, user, db):
        return user, tenant_id

    monkeypatch.setattr(
        module_access,
        "get_current_user_and_tenant",
        fake_get_current_user_and_tenant,
    )


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
    monkeypatch.setattr(module_access, "_load_active_modules", lambda db, tenant_id: ["compras"])

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
    monkeypatch.setattr(module_access, "_load_active_modules", lambda db, tenant_id: ["compras"])

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


def test_require_active_module_rejects_unknown_module():
    with pytest.raises(ValueError, match="Modulo comercial desconhecido"):
        module_access.require_active_module("modulo_fantasma")
