import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.security import permissions_service


def test_check_permission_honors_implicit_dependencies(monkeypatch):
    monkeypatch.setattr(
        permissions_service,
        "get_user_permissions",
        lambda db, user_id, tenant_id: {"vendas.criar"},
    )

    permissions_service.check_permission(
        db=object(),
        user_id=1,
        permission="clientes.visualizar",
        tenant_id=uuid.uuid4(),
        current_user=SimpleNamespace(id=1, is_admin=False),
    )


def test_check_permission_still_denies_unrelated_permission(monkeypatch):
    monkeypatch.setattr(
        permissions_service,
        "get_user_permissions",
        lambda db, user_id, tenant_id: {"vendas.criar"},
    )

    with pytest.raises(HTTPException):
        permissions_service.check_permission(
            db=object(),
            user_id=1,
            permission="usuarios.manage",
            tenant_id=uuid.uuid4(),
            current_user=SimpleNamespace(id=1, is_admin=False),
        )


def test_check_permission_does_not_use_global_admin_as_tenant_permission(monkeypatch):
    tenant_id = uuid.uuid4()
    calls = []

    def fake_user_permissions(db, user_id, checked_tenant_id):
        calls.append((user_id, checked_tenant_id))
        return set()

    monkeypatch.setattr(
        permissions_service,
        "get_user_permissions",
        fake_user_permissions,
    )

    with pytest.raises(HTTPException) as exc_info:
        permissions_service.check_permission(
            db=object(),
            user_id=1,
            permission="usuarios.manage",
            tenant_id=tenant_id,
            current_user=SimpleNamespace(id=1, is_admin=True),
        )

    assert exc_info.value.status_code == 403
    assert calls == [(1, tenant_id)]
