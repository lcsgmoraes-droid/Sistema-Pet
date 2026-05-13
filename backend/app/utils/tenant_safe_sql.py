"""
Tenant-safe execution for raw SQL.

Raw SQL does not pass through the ORM tenant filter. Queries that touch
tenant-scoped tables must use {tenant_filter}; this helper replaces the marker
with a parameterized tenant predicate and injects the tenant id safely.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Optional

from sqlalchemy import text
from sqlalchemy.engine import Result
from sqlalchemy.orm import Session

from app.tenancy.context import get_current_tenant_id


TENANT_FILTER_MARKER = "{tenant_filter}"


TENANT_SCOPED_TABLES = {
    "agendamentos",
    "caixa",
    "caixa_movimentacoes",
    "categorias",
    "cliente_segmentos",
    "clientes",
    "comissoes_configuracao",
    "comissoes_estornos",
    "comissoes_itens",
    "comissoes_provisoes",
    "comissoes_vendedores",
    "conciliacao_cartao",
    "contas_pagar",
    "contas_receber",
    "categorias_financeiras",
    "departamentos",
    "dre_categorias",
    "dre_lancamentos",
    "dre_plano_contas",
    "dre_subcategorias",
    "estoque_movimentacoes",
    "estoque_reservas",
    "formas_pagamento",
    "lancamentos_financeiros",
    "lancamentos_manuais",
    "movimentacoes_financeiras",
    "marcas",
    "notas_entrada",
    "notas_entrada_itens",
    "notas_saida",
    "notas_saida_itens",
    "pedidos_compra",
    "pedidos_compra_itens",
    "pets",
    "produtos",
    "produtos_historico_precos",
    "subcategorias",
    "tenant_template_item_installs",
    "tenant_template_installs",
    "tipo_despesas",
    "users",
    "venda_itens",
    "venda_pagamentos",
    "vendas",
}


GLOBAL_TABLES = {
    "alembic_version",
    "fiscal_catalogo_produtos",
    "fiscal_estado_padrao",
    "information_schema",
    "migrations",
    "permissions",
    "pg_catalog",
    "roles",
    "sessions",
    "template_bundles",
    "template_items",
    "tenants",
}


class TenantSafeSQLError(RuntimeError):
    """Raised when raw SQL violates tenant-safety rules."""


def _sql_to_string(sql: Any) -> str:
    return str(getattr(sql, "text", sql))


def _sql_bindparams(sql: Any) -> list:
    return list(getattr(sql, "_bindparams", {}).values())


def _normalized_sql(sql: str) -> str:
    return re.sub(r"\s+", " ", sql.strip().lower())


def _tables_touched(sql: str) -> set[str]:
    normalized = _normalized_sql(sql)
    tables: set[str] = set()

    for match in re.finditer(
        r"\b(?:from|join|update|into|delete\s+from)\s+([a-zA-Z_][\w.]*)",
        normalized,
    ):
        table_name = match.group(1).split(".")[-1]
        tables.add(table_name)

    return tables


def _tenant_tables_touched(sql: str) -> set[str]:
    return _tables_touched(sql).intersection(TENANT_SCOPED_TABLES)


def _is_insert_with_explicit_tenant(sql: str, params: Mapping[str, Any]) -> bool:
    normalized = _normalized_sql(sql)
    return normalized.startswith("insert ") and "tenant_id" in normalized and "tenant_id" in params


def _resolve_tenant_id(explicit_tenant_id: Any, require_tenant: bool) -> Any:
    if explicit_tenant_id is not None:
        return explicit_tenant_id
    if not require_tenant:
        return None
    return get_current_tenant_id()


def _ensure_tenant_present(tenant_id: Any) -> None:
    if tenant_id is None or tenant_id == "":
        raise TenantSafeSQLError(
            "tenant_id ausente para SQL bruto tenant-scoped. Informe tenant_id "
            "explicitamente ou configure app.tenancy.context antes de executar."
        )


def _ensure_explicit_insert_tenant_matches(params: Mapping[str, Any], tenant_id: Any) -> None:
    if tenant_id is None:
        return
    if str(params.get("tenant_id")) != str(tenant_id):
        raise TenantSafeSQLError(
            "INSERT tenant-scoped com tenant_id diferente do tenant atual/explicito."
        )


def _ensure_global_allowed(
    sql: str,
    params: Mapping[str, Any],
    tenant_tables: set[str],
    allow_global: bool,
    global_reason: Optional[str],
    tenant_id: Any,
) -> None:
    if not tenant_tables:
        return

    if _is_insert_with_explicit_tenant(sql, params):
        _ensure_explicit_insert_tenant_matches(params, tenant_id)
        return

    if allow_global and global_reason:
        return

    raise TenantSafeSQLError(
        "SQL bruto toca tabela tenant-scoped sem {tenant_filter}: "
        f"{', '.join(sorted(tenant_tables))}. Use {TENANT_FILTER_MARKER} "
        "ou marque explicitamente como global/admin com justificativa."
    )


def execute_tenant_safe(
    db: Session,
    sql: Any,
    params: Optional[Mapping[str, Any]] = None,
    tenant_id: Any = None,
    require_tenant: bool = True,
    allow_global: bool = False,
    global_reason: Optional[str] = None,
) -> Result:
    """
    Execute raw SQL with tenant protection.

    Contract:
    - Tenant-scoped SQL should contain {tenant_filter}.
    - The marker is replaced by tenant_id = :__tenant_id.
    - tenant_id is injected as a bound parameter.
    - SQL without a tenant marker is blocked when it touches tenant tables.
    - Global/admin/health SQL can be allowed with allow_global + global_reason.
    """
    # Backward compatibility with old positional execute_tenant_safe(..., False).
    if isinstance(tenant_id, bool) and require_tenant is True:
        require_tenant = tenant_id
        tenant_id = None

    sql_text = _sql_to_string(sql)
    safe_params = dict(params or {})
    tenant_tables = _tenant_tables_touched(sql_text)
    has_marker = TENANT_FILTER_MARKER in sql_text
    resolved_tenant_id = _resolve_tenant_id(tenant_id, require_tenant)

    if require_tenant:
        _ensure_tenant_present(resolved_tenant_id)
        if not has_marker:
            raise TenantSafeSQLError(
                f"SQL bruto tenant-scoped sem marcador {TENANT_FILTER_MARKER}."
            )
    elif tenant_tables and not has_marker:
        _ensure_global_allowed(
            sql_text,
            safe_params,
            tenant_tables,
            allow_global,
            global_reason,
            resolved_tenant_id,
        )

    if has_marker:
        _ensure_tenant_present(resolved_tenant_id)
        sql_text = sql_text.replace(TENANT_FILTER_MARKER, "tenant_id = :__tenant_id")
        safe_params["__tenant_id"] = str(resolved_tenant_id)

    if "' +" in sql_text or '" +' in sql_text or "f'" in sql_text or 'f"' in sql_text:
        raise TenantSafeSQLError(
            "Possivel concatenacao insegura detectada em SQL bruto. "
            "Use parametros nomeados."
        )

    try:
        statement = text(sql_text)
        bindparams = _sql_bindparams(sql)
        if bindparams:
            statement = statement.bindparams(*bindparams)
        return db.execute(statement, safe_params)
    except Exception as exc:
        raise TenantSafeSQLError(
            "Erro ao executar SQL tenant-safe. "
            f"SQL: {sql_text[:300]}... Params: {safe_params}. Erro: {exc}"
        ) from exc


def execute_tenant_safe_scalar(
    db: Session,
    sql: Any,
    params: Optional[Mapping[str, Any]] = None,
    tenant_id: Any = None,
    require_tenant: bool = True,
    allow_global: bool = False,
    global_reason: Optional[str] = None,
) -> Any:
    return execute_tenant_safe(
        db,
        sql,
        params,
        tenant_id=tenant_id,
        require_tenant=require_tenant,
        allow_global=allow_global,
        global_reason=global_reason,
    ).scalar()


def execute_tenant_safe_one(
    db: Session,
    sql: Any,
    params: Optional[Mapping[str, Any]] = None,
    tenant_id: Any = None,
    require_tenant: bool = True,
    allow_global: bool = False,
    global_reason: Optional[str] = None,
) -> Any:
    return execute_tenant_safe(
        db,
        sql,
        params,
        tenant_id=tenant_id,
        require_tenant=require_tenant,
        allow_global=allow_global,
        global_reason=global_reason,
    ).one()


def execute_tenant_safe_first(
    db: Session,
    sql: Any,
    params: Optional[Mapping[str, Any]] = None,
    tenant_id: Any = None,
    require_tenant: bool = True,
    allow_global: bool = False,
    global_reason: Optional[str] = None,
) -> Optional[Any]:
    return execute_tenant_safe(
        db,
        sql,
        params,
        tenant_id=tenant_id,
        require_tenant=require_tenant,
        allow_global=allow_global,
        global_reason=global_reason,
    ).first()


def execute_tenant_safe_all(
    db: Session,
    sql: Any,
    params: Optional[Mapping[str, Any]] = None,
    tenant_id: Any = None,
    require_tenant: bool = True,
    allow_global: bool = False,
    global_reason: Optional[str] = None,
) -> list:
    return execute_tenant_safe(
        db,
        sql,
        params,
        tenant_id=tenant_id,
        require_tenant=require_tenant,
        allow_global=allow_global,
        global_reason=global_reason,
    ).fetchall()


execute_raw_sql_safe = execute_tenant_safe
execute_safe = execute_tenant_safe
