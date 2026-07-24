from uuid import UUID

from app.models import Permission, Role, RolePermission
from app.services.default_roles_service import (
    DEFAULT_TENANT_ROLES,
    create_default_roles_for_new_tenant,
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


def test_create_default_roles_for_new_tenant_uses_least_privilege(
    db_session, tenant_factory, tenant_context
):
    tenant = tenant_factory(nome="Tenant perfis padrao")
    tenant_id = UUID(str(tenant.id))
    tenant_context(tenant_id)
    configured_codes = set().union(*DEFAULT_TENANT_ROLES.values())
    _seed_permissions(db_session, configured_codes)

    result = create_default_roles_for_new_tenant(db_session, tenant_id)
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


def test_create_default_roles_never_changes_an_existing_caixa(
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

    result = create_default_roles_for_new_tenant(db_session, tenant_id)
    db_session.flush()

    assert result["roles"]["Caixa"]["created"] is False
    assert result["roles"]["Caixa"]["added_permissions"] == []
    assert _role_permission_codes(db_session, tenant_id, caixa.id) == {excessive_code}


def test_create_default_roles_reports_unavailable_permissions_without_overgranting(
    db_session, tenant_factory, tenant_context
):
    tenant = tenant_factory(nome="Tenant permissoes parciais")
    tenant_id = UUID(str(tenant.id))
    tenant_context(tenant_id)
    _seed_permissions(db_session, {"vendas.criar"})

    result = create_default_roles_for_new_tenant(db_session, tenant_id)
    db_session.flush()

    assert "clientes.visualizar" in result["missing_permissions"]
    caixa = (
        db_session.query(Role)
        .filter(Role.tenant_id == tenant_id, Role.name == "Caixa")
        .one()
    )
    assert _role_permission_codes(db_session, tenant_id, caixa.id) == {"vendas.criar"}
