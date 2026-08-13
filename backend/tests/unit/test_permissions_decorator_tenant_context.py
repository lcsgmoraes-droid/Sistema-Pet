import uuid
from types import SimpleNamespace

import pytest

from app.security import permissions_decorator, permissions_service
from app.security.permissions_decorator import (
    require_permission,
    require_permission_dependency,
)
from app.tenancy.context import clear_current_tenant, get_current_tenant


def test_require_permission_reapplies_tenant_context_for_sync_route(monkeypatch):
    clear_current_tenant()
    tenant_id = uuid.uuid4()
    admin_user = SimpleNamespace(id=123, is_admin=False)

    monkeypatch.setattr(
        permissions_service,
        "get_user_permissions",
        lambda db, user_id, checked_tenant_id: {"clientes.visualizar"},
    )

    @require_permission("clientes.visualizar")
    def endpoint(db, user_and_tenant):
        assert get_current_tenant() == tenant_id
        return "ok"

    assert endpoint(db=object(), user_and_tenant=(admin_user, tenant_id)) == "ok"


@pytest.mark.asyncio
async def test_permission_dependency_reapplies_tenant_and_checks_permission(
    monkeypatch,
):
    clear_current_tenant()
    tenant_id = uuid.uuid4()
    user = SimpleNamespace(id=456, is_admin=False)
    calls = []

    def fake_check_permission(db, user_id, permission, checked_tenant_id, current_user):
        calls.append((db, user_id, permission, checked_tenant_id, current_user))

    monkeypatch.setattr(
        permissions_decorator, "check_permission", fake_check_permission
    )
    dependency = require_permission_dependency("comissoes.demonstrativo")
    db = object()

    await dependency(db=db, user_and_tenant=(user, tenant_id))

    assert get_current_tenant() == tenant_id
    assert calls == [(db, 456, "comissoes.demonstrativo", tenant_id, user)]
