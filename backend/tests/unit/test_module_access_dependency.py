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


def test_require_active_module_blocks_tenant_without_module(monkeypatch):
    monkeypatch.setattr(module_access, "_load_active_modules", lambda db, tenant_id: [])

    dependency = module_access.require_active_module("compras")

    with pytest.raises(HTTPException) as exc:
        dependency(user_and_tenant=(_user(), "tenant-1"), db=object())

    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "module_not_enabled"
    assert exc.value.detail["modulo"] == "compras"


def test_require_active_module_allows_tenant_with_module(monkeypatch):
    monkeypatch.setattr(module_access, "_load_active_modules", lambda db, tenant_id: ["compras"])

    dependency = module_access.require_active_module("compras")

    assert dependency(user_and_tenant=(_user(), "tenant-1"), db=object()) is None


def test_require_active_module_superadmin_bypasses_plan(monkeypatch):
    def fail_if_called(db, tenant_id):  # pragma: no cover - should not run
        raise AssertionError("superadmin should not query tenant module plan")

    monkeypatch.setattr(module_access, "_load_active_modules", fail_if_called)

    dependency = module_access.require_active_module("compras")

    assert dependency(user_and_tenant=(_user(is_superadmin=True), "tenant-1"), db=object()) is None


def test_require_active_module_requires_tenant_context(monkeypatch):
    monkeypatch.setattr(module_access, "_load_active_modules", lambda db, tenant_id: ["compras"])

    dependency = module_access.require_active_module("compras")

    with pytest.raises(HTTPException) as exc:
        dependency(user_and_tenant=(_user(), None), db=object())

    assert exc.value.status_code == 403
    assert exc.value.detail == "Tenant obrigatorio para acessar este modulo"


def test_require_active_module_rejects_unknown_module():
    with pytest.raises(ValueError, match="Modulo comercial desconhecido"):
        module_access.require_active_module("modulo_fantasma")
