"""Autorizacao tenant-scoped do unico endpoint novo do piloto DEV."""

from types import SimpleNamespace
from contextlib import nullcontext
from unittest.mock import Mock
from uuid import uuid4

from fastapi import HTTPException
import pytest

from app.config import settings
from app.routes import ifood_order_routes as routes


@pytest.fixture
def local_pilot(monkeypatch):
    tenant, merchant, order_id = uuid4(), str(uuid4()), str(uuid4())
    for key in ("APP_ENV", "ENV", "ENVIRONMENT"):
        monkeypatch.delenv(key, raising=False)
    for key, value in {
        "ENVIRONMENT": "test",
        "IFOOD_PDV_PILOT_ENABLED": True,
        "IFOOD_PDV_PILOT_TENANT_ID": str(tenant),
        "IFOOD_PDV_PILOT_MERCHANT_ID": merchant,
        "IFOOD_PDV_PILOT_ORDER_ID": order_id,
        "IFOOD_PDV_PILOT_SKU": "018631.1",
    }.items():
        monkeypatch.setattr(settings, key, value)
    # Administrador da empresa pode ser um usuario sem privilegio global.
    user = SimpleNamespace(id=21, tenant_id=tenant, is_admin=False)
    db = SimpleNamespace(commit=Mock(), rollback=Mock())
    imported = SimpleNamespace(id=1)
    import_call = Mock(return_value=imported)
    monkeypatch.setattr(routes, "import_pdv_pilot", import_call)
    monkeypatch.setattr(
        routes,
        "order_detail",
        lambda order, db: {"id": order.id, "pdv_bridge": {"status": "reserved"}},
    )
    return SimpleNamespace(
        tenant=tenant,
        merchant=merchant,
        order_id=order_id,
        user=user,
        db=db,
        imported=imported,
        import_call=import_call,
    )


def test_tenant_administrator_with_both_permissions_can_import_without_global_admin(
    local_pilot, monkeypatch
):
    c = local_pilot
    checked = []

    def check(db, user_id, permission, tenant_id, *, current_user):
        assert db is c.db and current_user is c.user
        assert user_id == c.user.id and tenant_id == c.tenant
        checked.append(permission)

    monkeypatch.setattr(routes.permissions_service, "check_permission", check)
    result = routes.import_ifood_pdv_pilot(c.order_id, auth=(c.user, c.tenant), db=c.db)
    assert checked == ["vendas.criar", "configuracoes.editar"]
    assert result["pdv_bridge"]["status"] == "reserved"
    c.import_call.assert_called_once_with(
        c.db, tenant_id=c.tenant, order_id=c.order_id, actor_id=c.user.id
    )
    c.db.commit.assert_called_once()
    c.db.rollback.assert_not_called()


@pytest.mark.parametrize("missing", ["vendas.criar", "configuracoes.editar"])
@pytest.mark.parametrize("global_admin", [False, True])
def test_missing_either_tenant_permission_is_denied_even_for_global_admin(
    local_pilot, monkeypatch, missing, global_admin
):
    c = local_pilot
    c.user.is_admin = global_admin
    checked = []

    def check(db, user_id, permission, tenant_id, *, current_user):
        assert tenant_id == c.tenant and current_user is c.user
        checked.append(permission)
        if permission == missing:
            raise HTTPException(403, "Sem permissao nesta empresa")

    monkeypatch.setattr(routes.permissions_service, "check_permission", check)
    with pytest.raises(HTTPException) as exc:
        routes.import_ifood_pdv_pilot(c.order_id, auth=(c.user, c.tenant), db=c.db)
    assert exc.value.status_code == 403 and missing in checked
    c.import_call.assert_not_called()
    c.db.commit.assert_not_called()


@pytest.mark.parametrize(
    "scenario", ["production", "staging", "other_tenant", "other_order"]
)
def test_production_and_outside_scope_stop_before_permission_database_or_import(
    local_pilot, monkeypatch, scenario
):
    c = local_pilot
    auth_tenant, order_id = c.tenant, c.order_id
    if scenario in {"production", "staging"}:
        monkeypatch.setenv("APP_ENV", scenario)
    elif scenario == "other_tenant":
        auth_tenant = uuid4()
    else:
        order_id = str(uuid4())
    permission_check = Mock(
        side_effect=AssertionError(
            "Nao deve consultar permissoes/banco fora do escopo DEV"
        )
    )
    monkeypatch.setattr(
        routes.permissions_service, "check_permission", permission_check
    )
    with pytest.raises(HTTPException) as exc:
        routes.import_ifood_pdv_pilot(order_id, auth=(c.user, auth_tenant), db=c.db)
    assert exc.value.status_code == 409
    permission_check.assert_not_called()
    c.import_call.assert_not_called()
    c.db.commit.assert_not_called()


def test_import_error_rolls_back_once_after_authorized_scope(local_pilot, monkeypatch):
    c = local_pilot
    monkeypatch.setattr(
        routes.permissions_service, "check_permission", lambda *a, **kw: None
    )
    c.import_call.side_effect = HTTPException(409, "Pedido divergente")
    with pytest.raises(HTTPException):
        routes.import_ifood_pdv_pilot(c.order_id, auth=(c.user, c.tenant), db=c.db)
    c.db.rollback.assert_called_once()
    c.db.commit.assert_not_called()


@pytest.fixture
def pilot_ui(local_pilot, monkeypatch):
    c = local_pilot
    c.permission_check = Mock()
    c.ready = Mock(return_value=SimpleNamespace(merchant_id=c.merchant))
    c.order_lookup = Mock(
        return_value=SimpleNamespace(
            merchant_id=c.merchant, ifood_order_id=c.order_id, tenant_id=c.tenant
        )
    )
    c.provider = SimpleNamespace()
    c.client = Mock(side_effect=lambda: nullcontext(c.provider))
    c.refresh = Mock(return_value={"refreshed": True})
    c.poll = Mock(return_value={"received": 1})
    monkeypatch.setattr(
        routes.permissions_service, "check_permission", c.permission_check
    )
    monkeypatch.setattr(routes, "_require_order_operations", lambda: None)
    monkeypatch.setattr(routes, "_ensure_ready", c.ready)
    monkeypatch.setattr(routes, "_order", c.order_lookup)
    monkeypatch.setattr(routes, "_client", c.client)
    monkeypatch.setattr(routes, "_refresh_virtual_bag", c.refresh)
    monkeypatch.setattr(routes, "process_order_events", c.poll)
    return c


def invoke_pilot_ui(c, action, *, tenant=None, order_id=None):
    auth = (c.user, tenant or c.tenant)
    if action == "poll":
        return routes.poll_ifood_order_events(auth=auth, db=c.db)
    return routes.refresh_ifood_virtual_bag(order_id or c.order_id, auth=auth, db=c.db)


@pytest.mark.parametrize("action", ["poll", "refresh"])
def test_test_store_poll_and_bag_refresh_allow_tenant_permissions_without_global_admin(
    pilot_ui, action
):
    c = pilot_ui
    invoke_pilot_ui(c, action)
    assert c.user.is_admin is False
    assert [call.args[2] for call in c.permission_check.call_args_list] == [
        "vendas.criar",
        "configuracoes.editar",
    ]
    assert all(
        call.args[3] == c.tenant and call.kwargs["current_user"] is c.user
        for call in c.permission_check.call_args_list
    )
    c.client.assert_called_once()
    assert c.poll.called if action == "poll" else c.refresh.called


@pytest.mark.parametrize("action", ["poll", "refresh"])
@pytest.mark.parametrize("permission", ["vendas.criar", "configuracoes.editar"])
def test_test_store_poll_and_refresh_deny_missing_tenant_permission_before_provider(
    pilot_ui, action, permission
):
    c = pilot_ui

    def deny(db, user_id, name, tenant_id, *, current_user):
        if name == permission:
            raise HTTPException(403, "Sem permissao na empresa")

    c.permission_check.side_effect = deny
    with pytest.raises(HTTPException) as exc:
        invoke_pilot_ui(c, action)
    assert exc.value.status_code == 403
    c.ready.assert_not_called()
    c.client.assert_not_called()


@pytest.mark.parametrize("action", ["poll", "refresh"])
def test_disabled_pilot_preserves_legacy_global_admin_rejection(
    pilot_ui, monkeypatch, action
):
    c = pilot_ui
    monkeypatch.setattr(settings, "IFOOD_PDV_PILOT_ENABLED", False)
    with pytest.raises(HTTPException) as exc:
        invoke_pilot_ui(c, action)
    assert exc.value.status_code == 403
    c.permission_check.assert_not_called()
    c.ready.assert_not_called()
    c.client.assert_not_called()


@pytest.mark.parametrize("action", ["poll", "refresh"])
@pytest.mark.parametrize("scenario", ["production", "staging", "other_tenant"])
def test_pilot_read_exceptions_fail_closed_before_db_outside_dev_scope(
    pilot_ui, monkeypatch, action, scenario
):
    c = pilot_ui
    tenant = c.tenant
    if scenario == "other_tenant":
        tenant = uuid4()
    else:
        monkeypatch.setenv("APP_ENV", scenario)
    with pytest.raises(HTTPException) as exc:
        invoke_pilot_ui(c, action, tenant=tenant)
    assert exc.value.status_code == 409
    c.permission_check.assert_not_called()
    c.ready.assert_not_called()
    c.client.assert_not_called()


@pytest.mark.parametrize("action", ["poll", "refresh"])
def test_pilot_ui_does_not_call_provider_for_different_configured_merchant(
    pilot_ui, action
):
    c = pilot_ui
    c.ready.return_value.merchant_id = str(uuid4())
    with pytest.raises(HTTPException) as exc:
        invoke_pilot_ui(c, action)
    assert exc.value.status_code == 409
    c.client.assert_not_called()


def test_pilot_virtual_bag_checks_both_order_id_and_order_merchant(pilot_ui):
    c = pilot_ui
    with pytest.raises(HTTPException) as exc:
        invoke_pilot_ui(c, "refresh", order_id=str(uuid4()))
    assert exc.value.status_code == 409
    c.permission_check.assert_not_called()
    c.order_lookup.return_value.merchant_id = str(uuid4())
    with pytest.raises(HTTPException) as exc:
        invoke_pilot_ui(c, "refresh")
    assert exc.value.status_code == 409
    c.client.assert_not_called()


def test_test_store_poll_can_connect_before_checkout_has_generated_order_id(
    pilot_ui, monkeypatch
):
    c = pilot_ui
    monkeypatch.setattr(settings, "IFOOD_PDV_PILOT_ORDER_ID", "")
    assert invoke_pilot_ui(c, "poll") == {"received": 1}
    c.client.assert_called_once()


@pytest.mark.parametrize("action", ["poll", "refresh"])
def test_disabled_pilot_keeps_existing_global_admin_flow_unchanged(
    pilot_ui, monkeypatch, action
):
    c = pilot_ui
    c.user.is_admin = True
    monkeypatch.setattr(settings, "IFOOD_PDV_PILOT_ENABLED", False)
    invoke_pilot_ui(c, action)
    c.permission_check.assert_not_called()
    c.client.assert_called_once()
