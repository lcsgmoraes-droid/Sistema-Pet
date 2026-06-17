"""Helpers for Alembic migrations that enable tenant-scoped RLS."""

from __future__ import annotations

from collections.abc import Iterator, Sequence


TENANT_RLS_GUARD = (
    "tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
)
AUTH_USER_ID_SETTING_INT = (
    "NULLIF(current_setting('app.auth_user_id', true), '')::integer"
)
AUTH_EMAIL_SETTING_TEXT = "NULLIF(current_setting('app.auth_email', true), '')"
PARTNER_TENANT_SETTING_UUID = "NULLIF(current_setting('app.tenant_id', true), '')::uuid"
PARTNER_OWN_TENANT_GUARD = f"tenant_id = {PARTNER_TENANT_SETTING_UUID}"
PARTNER_LINK_EXISTS_GUARD = (
    "EXISTS (SELECT 1 FROM vet_partner_link vpl "
    "WHERE vpl.empresa_tenant_id = tenant_id "
    f"AND vpl.vet_tenant_id = {PARTNER_TENANT_SETTING_UUID} "
    "AND vpl.ativo = true)"
)
PARTNER_SELECT_GUARD = f"({PARTNER_OWN_TENANT_GUARD}) OR ({PARTNER_LINK_EXISTS_GUARD})"

_PARTNER_POLICY_ORDER = (
    ("partner_select", f"FOR SELECT USING ({PARTNER_SELECT_GUARD})"),
    ("tenant_insert", f"FOR INSERT WITH CHECK ({PARTNER_OWN_TENANT_GUARD})"),
    (
        "tenant_update",
        f"FOR UPDATE USING ({PARTNER_OWN_TENANT_GUARD}) WITH CHECK ({PARTNER_OWN_TENANT_GUARD})",
    ),
    ("tenant_delete", f"FOR DELETE USING ({PARTNER_OWN_TENANT_GUARD})"),
)

AUTH_USER_SELF_GUARD = f"id = {AUTH_USER_ID_SETTING_INT}"
AUTH_USER_EMAIL_GUARD = f"lower(email) = lower({AUTH_EMAIL_SETTING_TEXT})"
AUTH_USERS_TENANT_MEMBERSHIP_GUARD = (
    "EXISTS (SELECT 1 FROM user_tenants aut "
    "WHERE aut.user_id = users.id "
    f"AND aut.tenant_id = {PARTNER_TENANT_SETTING_UUID} "
    "AND aut.is_active = true)"
)
AUTH_USERS_ACCESS_GUARD = (
    f"({PARTNER_OWN_TENANT_GUARD}) "
    f"OR ({AUTH_USERS_TENANT_MEMBERSHIP_GUARD}) "
    f"OR ({AUTH_USER_SELF_GUARD}) "
    f"OR ({AUTH_USER_EMAIL_GUARD})"
)
AUTH_USER_TENANTS_SELF_GUARD = f"user_id = {AUTH_USER_ID_SETTING_INT}"
AUTH_USER_TENANTS_ACCESS_GUARD = (
    f"({PARTNER_OWN_TENANT_GUARD}) OR ({AUTH_USER_TENANTS_SELF_GUARD})"
)

_AUTH_POLICY_ORDER = {
    "users": (
        ("auth_select", f"FOR SELECT USING ({AUTH_USERS_ACCESS_GUARD})"),
        ("auth_insert", f"FOR INSERT WITH CHECK ({PARTNER_OWN_TENANT_GUARD})"),
        (
            "auth_update",
            f"FOR UPDATE USING ({AUTH_USERS_ACCESS_GUARD}) WITH CHECK ({AUTH_USERS_ACCESS_GUARD})",
        ),
        ("auth_delete", f"FOR DELETE USING ({PARTNER_OWN_TENANT_GUARD})"),
    ),
    "user_tenants": (
        ("auth_select", f"FOR SELECT USING ({AUTH_USER_TENANTS_ACCESS_GUARD})"),
        ("auth_insert", f"FOR INSERT WITH CHECK ({PARTNER_OWN_TENANT_GUARD})"),
        (
            "auth_update",
            f"FOR UPDATE USING ({PARTNER_OWN_TENANT_GUARD}) WITH CHECK ({PARTNER_OWN_TENANT_GUARD})",
        ),
        ("auth_delete", f"FOR DELETE USING ({PARTNER_OWN_TENANT_GUARD})"),
    ),
}


def _postgres_bind(op_module):
    bind = op_module.get_bind()
    if bind.dialect.name != "postgresql":
        return None
    return bind


def _existing_tables(sa_module, bind, table_names: Sequence[str]) -> list[str]:
    inspector = sa_module.inspect(bind)
    return [table_name for table_name in table_names if inspector.has_table(table_name)]


def _policy_name(table_name: str) -> str:
    return f"{table_name}_tenant_isolation"


def _partner_policy_names(table_name: str) -> list[str]:
    return _custom_policy_names(table_name, _PARTNER_POLICY_ORDER)


def _auth_policy_names(table_name: str) -> list[str]:
    return _custom_policy_names(table_name, _AUTH_POLICY_ORDER[table_name])


def _custom_policy_names(
    table_name: str, policy_order: Sequence[tuple[str, str]]
) -> list[str]:
    return [f"{table_name}_{suffix}" for suffix, _ in policy_order]


def iter_tenant_rls_statements(table_name: str, *, enable: bool) -> Iterator[str]:
    policy = _policy_name(table_name)
    if enable:
        yield f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY"
        yield f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY"

    yield f"DROP POLICY IF EXISTS {policy} ON {table_name}"

    if enable:
        yield (
            f"CREATE POLICY {policy} ON {table_name} "
            f"USING ({TENANT_RLS_GUARD}) WITH CHECK ({TENANT_RLS_GUARD})"
        )
    else:
        yield f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY"
        yield f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY"


def _iter_custom_rls_statements(
    table_name: str,
    *,
    enable: bool,
    policy_names: Sequence[str],
    policy_order: Sequence[tuple[str, str]],
) -> Iterator[str]:
    if enable:
        yield f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY"
        yield f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY"
        yield f"DROP POLICY IF EXISTS {_policy_name(table_name)} ON {table_name}"
        for policy_name in policy_names:
            yield f"DROP POLICY IF EXISTS {policy_name} ON {table_name}"
        for policy_name, (_, clause) in zip(policy_names, policy_order, strict=True):
            yield f"CREATE POLICY {policy_name} ON {table_name} {clause}"
        return

    for policy_name in reversed(policy_names):
        yield f"DROP POLICY IF EXISTS {policy_name} ON {table_name}"
    yield f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY"
    yield f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY"


def iter_partner_readable_rls_statements(
    table_name: str, *, enable: bool
) -> Iterator[str]:
    yield from _iter_custom_rls_statements(
        table_name,
        enable=enable,
        policy_names=_partner_policy_names(table_name),
        policy_order=_PARTNER_POLICY_ORDER,
    )


def iter_auth_users_rls_statements(table_name: str, *, enable: bool) -> Iterator[str]:
    yield from _iter_custom_rls_statements(
        table_name,
        enable=enable,
        policy_names=_auth_policy_names(table_name),
        policy_order=_AUTH_POLICY_ORDER[table_name],
    )


def apply_tenant_rls(
    *,
    op_module,
    sa_module,
    table_names: Sequence[str],
    enable: bool,
) -> None:
    bind = _postgres_bind(op_module)
    if bind is None:
        return

    present_tables = _existing_tables(sa_module, bind, table_names)
    if not enable:
        present_tables.reverse()

    for table_name in present_tables:
        for statement in iter_tenant_rls_statements(table_name, enable=enable):
            op_module.execute(statement)


def apply_partner_readable_rls(
    *,
    op_module,
    sa_module,
    table_names: Sequence[str],
    enable: bool,
) -> None:
    bind = _postgres_bind(op_module)
    if bind is None:
        return

    present_tables = _existing_tables(sa_module, bind, table_names)
    if not enable:
        present_tables.reverse()

    for table_name in present_tables:
        for statement in iter_partner_readable_rls_statements(
            table_name, enable=enable
        ):
            op_module.execute(statement)


def apply_auth_users_rls(
    *,
    op_module,
    sa_module,
    table_names: Sequence[str],
    enable: bool,
) -> None:
    bind = _postgres_bind(op_module)
    if bind is None:
        return

    present_tables = _existing_tables(sa_module, bind, table_names)
    if not enable:
        present_tables.reverse()

    for table_name in present_tables:
        for statement in iter_auth_users_rls_statements(table_name, enable=enable):
            op_module.execute(statement)
