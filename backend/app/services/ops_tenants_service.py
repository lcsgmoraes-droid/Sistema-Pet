from __future__ import annotations

from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.services.base_catalog_import_service import (
    DEFAULT_BASE_CATALOG_BUNDLE_CODE,
    DEFAULT_BASE_CATALOG_BUNDLE_VERSION,
    DEFAULT_BASE_CATALOG_SOURCE_EMAIL,
    import_base_catalog,
)


COUNT_TABLES = {
    "produtos": "produtos",
    "clientes": "clientes",
    "pets": "pets",
    "vendas": "vendas",
}


class OpsTenantActionError(RuntimeError):
    pass


def _table_exists(db: Session, table_name: str) -> bool:
    return inspect(db.connection()).has_table(table_name)


def _count_by_tenant(db: Session, table_name: str, tenant_id: str) -> int:
    if not _table_exists(db, table_name):
        return 0
    return int(
        db.execute(
            text(f"SELECT COUNT(*) FROM {table_name} WHERE CAST(tenant_id AS TEXT) = :tenant_id"),
            {"tenant_id": tenant_id},
        ).scalar()
        or 0
    )


def _count_users(db: Session, tenant_id: str) -> int:
    if _table_exists(db, "user_tenants"):
        return int(
            db.execute(
                text(
                    """
                    SELECT COUNT(DISTINCT user_id)
                    FROM user_tenants
                    WHERE CAST(tenant_id AS TEXT) = :tenant_id
                      AND COALESCE(CAST(is_active AS TEXT), 'true') NOT IN ('false', '0')
                    """
                ),
                {"tenant_id": tenant_id},
            ).scalar()
            or 0
        )
    if _table_exists(db, "users"):
        return _count_by_tenant(db, "users", tenant_id)
    return 0


def _principal_user(db: Session, tenant_id: str) -> dict[str, Any] | None:
    if not _table_exists(db, "users"):
        return None

    row = db.execute(
        text(
            """
            SELECT id, email, nome, is_active, is_admin
            FROM users
            WHERE CAST(tenant_id AS TEXT) = :tenant_id
            ORDER BY is_admin DESC, id ASC
            LIMIT 1
            """
        ),
        {"tenant_id": tenant_id},
    ).mappings().first()

    if not row and _table_exists(db, "user_tenants"):
        row = db.execute(
            text(
                """
                SELECT u.id, u.email, u.nome, u.is_active, u.is_admin
                FROM user_tenants ut
                JOIN users u ON u.id = ut.user_id
                WHERE CAST(ut.tenant_id AS TEXT) = :tenant_id
                ORDER BY u.is_admin DESC, u.id ASC
                LIMIT 1
                """
            ),
            {"tenant_id": tenant_id},
        ).mappings().first()

    if not row:
        return None
    return {
        "id": int(row["id"]),
        "email": row["email"],
        "nome": row.get("nome"),
        "is_active": bool(row.get("is_active")),
        "is_admin": bool(row.get("is_admin")),
    }


def _base_catalog_status(db: Session, tenant_id: str) -> dict[str, Any]:
    empty = {
        "installed": False,
        "status": None,
        "bundle_code": DEFAULT_BASE_CATALOG_BUNDLE_CODE,
        "bundle_version": DEFAULT_BASE_CATALOG_BUNDLE_VERSION,
        "updated_at": None,
        "created_by_user_id": None,
    }
    if not _table_exists(db, "tenant_template_installs"):
        return empty

    row = db.execute(
        text(
            """
            SELECT status, updated_at, created_at, created_by_user_id
            FROM tenant_template_installs
            WHERE CAST(tenant_id AS TEXT) = :tenant_id
              AND bundle_code = :bundle_code
              AND bundle_version = :bundle_version
            ORDER BY updated_at DESC, created_at DESC, id DESC
            LIMIT 1
            """
        ),
        {
            "tenant_id": tenant_id,
            "bundle_code": DEFAULT_BASE_CATALOG_BUNDLE_CODE,
            "bundle_version": DEFAULT_BASE_CATALOG_BUNDLE_VERSION,
        },
    ).mappings().first()
    if not row:
        return empty

    return {
        **empty,
        "installed": True,
        "status": row["status"],
        "updated_at": row.get("updated_at") or row.get("created_at"),
        "created_by_user_id": row.get("created_by_user_id"),
    }


def _tenant_counts(db: Session, tenant_id: str) -> dict[str, int]:
    counts = {label: _count_by_tenant(db, table_name, tenant_id) for label, table_name in COUNT_TABLES.items()}
    counts["usuarios"] = _count_users(db, tenant_id)
    return counts


def _tenant_row_to_item(db: Session, row: dict[str, Any]) -> dict[str, Any]:
    tenant_id = str(row["id"])
    return {
        "id": tenant_id,
        "name": row["name"],
        "status": row.get("status") or "active",
        "plan": row.get("plan") or "free",
        "billing_status": row.get("billing_status") or "active",
        "subscription_source": row.get("subscription_source") or "manual",
        "subscription_activated_at": row.get("subscription_activated_at"),
        "organization_type": row.get("organization_type") or "petshop",
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "principal_user": _principal_user(db, tenant_id),
        "counts": _tenant_counts(db, tenant_id),
        "base_catalog": _base_catalog_status(db, tenant_id),
    }


def list_ops_tenants(
    db: Session,
    *,
    search: str | None = None,
    status: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    if not _table_exists(db, "tenants"):
        return {"items": [], "summary": {"total": 0, "active": 0, "with_base_catalog": 0}}

    clauses = []
    params: dict[str, Any] = {"limit": int(limit)}
    if search:
        clauses.append("(lower(name) LIKE lower(:search) OR lower(CAST(id AS TEXT)) LIKE lower(:search))")
        params["search"] = f"%{search.strip()}%"
    if status:
        clauses.append("lower(status) = lower(:status)")
        params["status"] = status.strip()

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = db.execute(
        text(
            f"""
            SELECT id, name, status, plan, billing_status, subscription_source,
                   subscription_activated_at, organization_type, created_at, updated_at
            FROM tenants
            {where_sql}
            ORDER BY name ASC
            LIMIT :limit
            """
        ),
        params,
    ).mappings()
    items = [_tenant_row_to_item(db, dict(row)) for row in rows]
    summary = {
        "total": len(items),
        "active": sum(1 for item in items if str(item.get("status") or "").lower() in {"active", "ativo"}),
        "with_base_catalog": sum(1 for item in items if item["base_catalog"]["installed"]),
    }
    return {"items": items, "summary": summary}


def _resolve_source_tenant_id(db: Session, source_email: str = DEFAULT_BASE_CATALOG_SOURCE_EMAIL) -> str:
    if not _table_exists(db, "users"):
        raise OpsTenantActionError("Tabela de usuarios ausente.")

    row = db.execute(
        text(
            """
            SELECT tenant_id
            FROM users
            WHERE lower(email) = lower(:email)
              AND tenant_id IS NOT NULL
            ORDER BY id ASC
            LIMIT 1
            """
        ),
        {"email": source_email},
    ).first()
    if not row:
        raise OpsTenantActionError(f"Usuario fonte nao encontrado: {source_email}.")
    return str(row[0])


def _resolve_target_user_id(db: Session, tenant_id: str) -> int:
    principal = _principal_user(db, tenant_id)
    if not principal:
        raise OpsTenantActionError(f"Tenant sem usuario principal: {tenant_id}.")
    return int(principal["id"])


def _ensure_target_tenant(db: Session, tenant_id: str) -> None:
    exists = db.execute(
        text("SELECT 1 FROM tenants WHERE CAST(id AS TEXT) = :tenant_id LIMIT 1"),
        {"tenant_id": tenant_id},
    ).scalar()
    if not exists:
        raise OpsTenantActionError(f"Tenant nao encontrado: {tenant_id}.")


def preview_base_catalog_import(db: Session, *, tenant_id: str) -> dict[str, Any]:
    target_tenant_id = str(tenant_id).strip()
    _ensure_target_tenant(db, target_tenant_id)
    return import_base_catalog(
        db=db,
        source_tenant_id=_resolve_source_tenant_id(db),
        target_tenant_id=target_tenant_id,
        user_id=_resolve_target_user_id(db, target_tenant_id),
        dry_run=True,
    )


def apply_base_catalog_import(
    db: Session,
    *,
    tenant_id: str,
    actor_user_id: int,
    confirm: bool,
) -> dict[str, Any]:
    if not confirm:
        raise OpsTenantActionError("Importacao real exige confirmacao explicita.")

    target_tenant_id = str(tenant_id).strip()
    _ensure_target_tenant(db, target_tenant_id)
    return import_base_catalog(
        db=db,
        source_tenant_id=_resolve_source_tenant_id(db),
        target_tenant_id=target_tenant_id,
        user_id=_resolve_target_user_id(db, target_tenant_id) or int(actor_user_id),
        dry_run=False,
    )
