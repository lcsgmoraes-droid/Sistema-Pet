import uuid
from types import SimpleNamespace

from app.security.permissions_decorator import require_permission
from app.tenancy.context import clear_current_tenant, get_current_tenant


def test_require_permission_reapplies_tenant_context_for_sync_route():
    clear_current_tenant()
    tenant_id = uuid.uuid4()
    admin_user = SimpleNamespace(id=123, is_admin=True)

    @require_permission("clientes.visualizar")
    def endpoint(db, user_and_tenant):
        assert get_current_tenant() == tenant_id
        return "ok"

    assert endpoint(db=object(), user_and_tenant=(admin_user, tenant_id)) == "ok"
