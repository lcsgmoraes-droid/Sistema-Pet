from uuid import UUID

from app.models import Permission, Role, RolePermission
from app.services.default_roles_service import (
    CAIXA_PERMISSIONS,
    DEFAULT_TENANT_ROLES,
    sync_default_roles,
)


def _seed_permissions(db_session, codes):
    permissions = [Permission(code=code, description=code) for code in sorted(codes)]
    db_session.add_all(permissions)
    db_session.flush()
    return {permission.code: permission for permission in permissions}


def _role_permission_codes(db_session, tenant_id, role_id):
    return {
        code
        for (code,) in (
            db_session.query(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .filter(
                RolePermission.tenant_id == tenant_id,
                RolePermission.role_id == role_id,
            )
            .all()
        )
    }


def test_sync_default_roles_creates_least_privilege_profiles(
    db_session, tenant_factory, tenant_context
):
    tenant = tenant_factory(nome="Tenant perfis padrao")
    tenant_id = UUID(str(tenant.id))
    tenant_context(tenant_id)
    configured_codes = set().union(*DEFAULT_TENANT_ROLES.values())
    _seed_permissions(db_session, configured_codes)

    result = sync_default_roles(db_session, tenant_id)
    db_session.flush()

    assert result["missing_permissions"] == []
    assert set(result["roles"]) == set(DEFAULT_TENANT_ROLES)

    roles = (
        db_session.query(Role)
        .filter(Role.tenant_id == tenant_id)
        .order_by(Role.name)
        .all()
    )
    assert {role.name for role in roles} == set(DEFAULT_TENANT_ROLES)
    for role in roles:
        assert _role_permission_codes(db_session, tenant_id, role.id) == set(
            DEFAULT_TENANT_ROLES[role.name]
        )


def test_sync_existing_caixa_removes_excess_permissions_only_on_apply(
    db_session, tenant_factory, tenant_context
):
    tenant = tenant_factory(nome="Tenant caixa legado")
    tenant_id = UUID(str(tenant.id))
    tenant_context(tenant_id)
    excessive_code = "produtos.excluir"
    permissions = _seed_permissions(
        db_session, set().union(*DEFAULT_TENANT_ROLES.values()) | {excessive_code}
    )
    caixa = Role(name="Caixa", tenant_id=tenant_id)
    db_session.add(caixa)
    db_session.flush()
    db_session.add(
        RolePermission(
            tenant_id=tenant_id,
            role_id=caixa.id,
            permission_id=permissions[excessive_code].id,
        )
    )
    db_session.flush()

    preview = sync_default_roles(
        db_session,
        tenant_id,
        update_existing=True,
        dry_run=True,
    )

    assert excessive_code in preview["roles"]["Caixa"]["removed_permissions"]
    assert _role_permission_codes(db_session, tenant_id, caixa.id) == {excessive_code}

    applied = sync_default_roles(
        db_session,
        tenant_id,
        update_existing=True,
        dry_run=False,
    )
    db_session.flush()

    assert excessive_code in applied["roles"]["Caixa"]["removed_permissions"]
    assert _role_permission_codes(db_session, tenant_id, caixa.id) == set(
        CAIXA_PERMISSIONS
    )


def test_sync_default_roles_reports_unavailable_permissions_without_overgranting(
    db_session, tenant_factory, tenant_context
):
    tenant = tenant_factory(nome="Tenant permissoes parciais")
    tenant_id = UUID(str(tenant.id))
    tenant_context(tenant_id)
    _seed_permissions(db_session, {"vendas.criar"})

    result = sync_default_roles(db_session, tenant_id)
    db_session.flush()

    assert "clientes.visualizar" in result["missing_permissions"]
    caixa = (
        db_session.query(Role)
        .filter(Role.tenant_id == tenant_id, Role.name == "Caixa")
        .one()
    )
    assert _role_permission_codes(db_session, tenant_id, caixa.id) == {"vendas.criar"}
