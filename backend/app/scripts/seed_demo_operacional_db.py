"""Database lookup helpers for the operational demo seed."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text


def _set_tenant_context(db, tenant_id: str) -> None:
    db.execute(
        text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
        {"tenant_id": tenant_id},
    )


def _resolve_tenant_context(db, target_email: str) -> dict[str, Any]:
    row = (
        db.execute(
            text(
                """
                SELECT id AS user_id,
                       email,
                       COALESCE(NULLIF(nome, ''), email) AS user_name,
                       tenant_id::text AS tenant_id
                FROM users
                WHERE lower(email) = lower(:email)
                ORDER BY id
                LIMIT 1
                """
            ),
            {"email": target_email.strip()},
        )
        .mappings()
        .first()
    )
    if not row:
        raise ValueError(f"Usuario alvo nao encontrado: {target_email}")
    if not row["tenant_id"]:
        raise ValueError(f"Usuario alvo sem tenant: {target_email}")
    return dict(row)


def _resolve_source_tenant_id(db, source_email: str) -> str | None:
    row = db.execute(
        text(
            """
            SELECT tenant_id::text
            FROM users
            WHERE lower(email) = lower(:email)
              AND tenant_id IS NOT NULL
            ORDER BY id
            LIMIT 1
            """
        ),
        {"email": source_email.strip()},
    ).first()
    return str(row[0]) if row else None


def _maybe_import_catalog(
    *,
    db,
    source_email: str,
    target_tenant_id: str,
    user_id: int,
    dry_run: bool,
    skip: bool,
) -> dict[str, Any]:
    if skip:
        return {"status": "skipped"}

    source_tenant_id = _resolve_source_tenant_id(db, source_email)
    if not source_tenant_id:
        return {
            "status": "source_missing",
            "source_email": source_email,
            "message": "Tenant fonte nao existe neste banco.",
        }
    if source_tenant_id == target_tenant_id:
        return {"status": "skipped_same_tenant", "source_email": source_email}

    from app.services.base_catalog_import_service import import_base_catalog

    result = import_base_catalog(
        db=db,
        source_tenant_id=source_tenant_id,
        target_tenant_id=target_tenant_id,
        user_id=user_id,
        dry_run=dry_run,
    )
    result["status"] = "dry_run" if dry_run else "applied"
    return result


def _scalar(db, sql: str, params: dict[str, Any]) -> Any:
    return db.execute(text(sql), params).scalar()


def _one_mapping(db, sql: str, params: dict[str, Any]) -> dict[str, Any] | None:
    row = db.execute(text(sql), params).mappings().first()
    return dict(row) if row else None


def _all_mappings(db, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(row) for row in db.execute(text(sql), params).mappings().all()]
