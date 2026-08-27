"""Fachada das operacoes administrativas de empresas.

As rotas continuam importando este modulo. Consultas, metricas e montagem da
visao operacional ficam em ``ops_tenants_read_service``; comandos comerciais,
acompanhamento e importacao de catalogo permanecem aqui.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.ops_models import OpsTenantOnboardingNote
from app.services.base_catalog_import_service import (
    DEFAULT_BASE_CATALOG_BUNDLE_CODE,
    DEFAULT_BASE_CATALOG_BUNDLE_VERSION,
    DEFAULT_BASE_CATALOG_SOURCE_EMAIL,
    import_base_catalog,
)
from app.services.ops_tenants_common import (
    BUSINESS_TIMEZONE,
    OpsTenantActionError,
    _business_today,
    _column_exists,
    _iso,
    _parse_date,
    _parse_datetime,
    _table_exists,
)
from app.services.ops_tenants_read_service import (
    COUNT_TABLES,
    _base_catalog_status,
    _count_by_tenant,
    _count_users,
    _fetch_tenant_item,
    _image_bytes,
    _is_billing_attention,
    _latest_tenant_timestamp,
    _latest_user_login,
    _pilot_critical_alerts,
    _pilot_errors_7d,
    _pilot_follow_up,
    _principal_user,
    _tenant_counts,
    _tenant_pilot_status,
    _tenant_row_to_item,
    _tenant_usage,
    list_ops_tenants,
)

__all__ = [
    "BUSINESS_TIMEZONE",
    "COMMERCIAL_STATE_LABELS",
    "COMMERCIAL_STATE_OPTIONS",
    "COUNT_TABLES",
    "DEFAULT_BASE_CATALOG_BUNDLE_CODE",
    "DEFAULT_BASE_CATALOG_BUNDLE_VERSION",
    "DEFAULT_BASE_CATALOG_SOURCE_EMAIL",
    "ONBOARDING_SATISFACTION_OPTIONS",
    "OpsTenantActionError",
    "_base_catalog_status",
    "_business_today",
    "_column_exists",
    "_count_by_tenant",
    "_count_users",
    "_fetch_tenant_item",
    "_image_bytes",
    "_is_billing_attention",
    "_iso",
    "_latest_tenant_timestamp",
    "_latest_user_login",
    "_parse_date",
    "_parse_datetime",
    "_pilot_critical_alerts",
    "_pilot_errors_7d",
    "_pilot_follow_up",
    "_principal_user",
    "_table_exists",
    "_tenant_counts",
    "_tenant_pilot_status",
    "_tenant_row_to_item",
    "_tenant_usage",
    "apply_base_catalog_import",
    "create_ops_tenant_onboarding_note",
    "list_ops_tenant_onboarding_notes",
    "list_ops_tenants",
    "preview_base_catalog_import",
    "update_ops_tenant_commercial_state",
    "update_ops_tenant_onboarding_follow_up",
]

COMMERCIAL_STATE_OPTIONS = {
    "status": {"active", "trial", "inactive", "suspended"},
    "plan": {"free", "basico", "basic", "premium", "enterprise", "legacy", "completo"},
    "billing_status": {
        "active",
        "trial",
        "paid",
        "ok",
        "em_dia",
        "past_due",
        "overdue",
        "late",
        "inadimplente",
        "blocked",
        "canceled",
        "expired",
    },
    "subscription_source": {
        "manual",
        "admin",
        "trial",
        "stripe",
        "asaas",
        "mercado_pago",
        "bling",
        "external",
    },
}

COMMERCIAL_STATE_LABELS = {
    "status": "Status",
    "plan": "Plano",
    "billing_status": "Status de cobranca",
    "subscription_source": "Origem da assinatura",
}

ONBOARDING_SATISFACTION_OPTIONS = {
    "not_collected",
    "satisfied",
    "neutral",
    "dissatisfied",
}


def _normalize_commercial_value(field: str, value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if not normalized:
        raise OpsTenantActionError(
            f"{COMMERCIAL_STATE_LABELS[field]} nao pode ficar vazio."
        )
    if normalized not in COMMERCIAL_STATE_OPTIONS[field]:
        allowed = ", ".join(sorted(COMMERCIAL_STATE_OPTIONS[field]))
        raise OpsTenantActionError(
            f"{COMMERCIAL_STATE_LABELS[field]} invalido. Use um destes valores: {allowed}."
        )
    return normalized


def update_ops_tenant_commercial_state(
    db: Session,
    *,
    tenant_id: str,
    changes: dict[str, Any],
) -> dict[str, Any]:
    target_tenant_id = str(tenant_id).strip()
    _ensure_target_tenant(db, target_tenant_id)

    normalized: dict[str, str] = {}
    for field in COMMERCIAL_STATE_OPTIONS:
        if field in changes and changes[field] is not None:
            normalized[field] = _normalize_commercial_value(field, changes[field])

    if not normalized:
        raise OpsTenantActionError("Nenhuma alteracao comercial informada.")

    assignments = ", ".join(f"{field} = :{field}" for field in normalized)
    params: dict[str, Any] = {"tenant_id": target_tenant_id, **normalized}
    db.execute(
        text(f"""
            UPDATE tenants
            SET {assignments}
            WHERE CAST(id AS TEXT) = :tenant_id
            """),
        params,
    )
    return _fetch_tenant_item(db, target_tenant_id)


def _normalize_onboarding_owner(value: Any) -> str | None:
    normalized = str(value or "").strip()
    if len(normalized) > 160:
        raise OpsTenantActionError(
            "Responsavel pelo acompanhamento deve ter no maximo 160 caracteres."
        )
    return normalized or None


def _normalize_onboarding_date(value: Any, *, label: str) -> date | None:
    if value in {None, ""}:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError as exc:
        raise OpsTenantActionError(
            f"{label} invalida. Use o formato AAAA-MM-DD."
        ) from exc


def _normalize_onboarding_satisfaction(value: Any) -> str:
    normalized = str(value or "not_collected").strip().lower()
    if normalized not in ONBOARDING_SATISFACTION_OPTIONS:
        allowed = ", ".join(sorted(ONBOARDING_SATISFACTION_OPTIONS))
        raise OpsTenantActionError(
            f"Satisfacao inicial invalida. Use um destes valores: {allowed}."
        )
    return normalized


def update_ops_tenant_onboarding_follow_up(
    db: Session,
    *,
    tenant_id: str,
    changes: dict[str, Any],
) -> dict[str, Any]:
    target_tenant_id = str(tenant_id).strip()
    _ensure_target_tenant(db, target_tenant_id)

    normalizers = {
        "onboarding_owner_name": _normalize_onboarding_owner,
        "onboarding_unblocked_on": lambda value: _normalize_onboarding_date(
            value, label="Data de desbloqueio"
        ),
        "onboarding_next_contact_on": lambda value: _normalize_onboarding_date(
            value, label="Data do proximo contato"
        ),
        "onboarding_satisfaction": _normalize_onboarding_satisfaction,
    }
    normalized = {
        field: normalizer(changes[field])
        for field, normalizer in normalizers.items()
        if field in changes
    }
    if not normalized:
        raise OpsTenantActionError("Nenhuma alteracao de onboarding informada.")

    assignments = [f"{field} = :{field}" for field in normalized]
    assignments.append("onboarding_follow_up_updated_at = :updated_at")
    params: dict[str, Any] = {
        "tenant_id": target_tenant_id,
        "updated_at": datetime.now(timezone.utc),
        **normalized,
    }
    db.execute(
        text(f"""
            UPDATE tenants
            SET {", ".join(assignments)}
            WHERE CAST(id AS TEXT) = :tenant_id
            """),
        params,
    )
    return _fetch_tenant_item(db, target_tenant_id)


def _normalize_onboarding_note(value: Any) -> str:
    normalized = str(value or "").strip()
    if len(normalized) < 3:
        raise OpsTenantActionError("A nota deve ter pelo menos 3 caracteres.")
    if len(normalized) > 1000:
        raise OpsTenantActionError("A nota deve ter no maximo 1000 caracteres.")
    return normalized


def _onboarding_note_to_item(note: OpsTenantOnboardingNote) -> dict[str, Any]:
    return {
        "id": int(note.id),
        "tenant_id": str(note.tenant_id),
        "note": note.note,
        "next_contact_on": _iso(note.next_contact_on),
        "created_by": {
            "platform_admin_id": int(note.created_by_platform_admin_id),
            "label": note.created_by_label,
        },
        "created_at": _iso(note.created_at),
    }


def list_ops_tenant_onboarding_notes(
    db: Session,
    *,
    tenant_id: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    target_tenant_id = str(tenant_id).strip()
    _ensure_target_tenant(db, target_tenant_id)
    rows = (
        db.query(OpsTenantOnboardingNote)
        .filter(OpsTenantOnboardingNote.tenant_id == target_tenant_id)
        .order_by(
            OpsTenantOnboardingNote.created_at.desc(),
            OpsTenantOnboardingNote.id.desc(),
        )
        .limit(max(1, min(int(limit), 100)))
        .all()
    )
    return [_onboarding_note_to_item(row) for row in rows]


def create_ops_tenant_onboarding_note(
    db: Session,
    *,
    tenant_id: str,
    note: str,
    platform_admin_id: int,
    platform_admin_label: str,
) -> dict[str, Any]:
    target_tenant_id = str(tenant_id).strip()
    _ensure_target_tenant(db, target_tenant_id)
    normalized_note = _normalize_onboarding_note(note)
    normalized_label = str(platform_admin_label or "").strip()
    if not normalized_label:
        raise OpsTenantActionError("Administrador responsavel nao identificado.")

    next_contact_on = db.execute(
        text("""
            SELECT onboarding_next_contact_on
            FROM tenants
            WHERE CAST(id AS TEXT) = :tenant_id
            LIMIT 1
            """),
        {"tenant_id": target_tenant_id},
    ).scalar()
    row = OpsTenantOnboardingNote(
        tenant_id=target_tenant_id,
        note=normalized_note,
        next_contact_on=_parse_date(next_contact_on),
        created_by_platform_admin_id=int(platform_admin_id),
        created_by_label=normalized_label[:255],
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.flush()
    return _onboarding_note_to_item(row)


def _resolve_source_tenant_id(
    db: Session, source_email: str = DEFAULT_BASE_CATALOG_SOURCE_EMAIL
) -> str:
    if not _table_exists(db, "users"):
        raise OpsTenantActionError("Tabela de usuarios ausente.")

    row = db.execute(
        text("""
            SELECT tenant_id
            FROM users
            WHERE lower(email) = lower(:email)
              AND tenant_id IS NOT NULL
            ORDER BY id ASC
            LIMIT 1
            """),
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
    confirm: bool,
) -> dict[str, Any]:
    if not confirm:
        raise OpsTenantActionError("Importacao real exige confirmacao explicita.")

    target_tenant_id = str(tenant_id).strip()
    _ensure_target_tenant(db, target_tenant_id)
    target_user_id = _resolve_target_user_id(db, target_tenant_id)
    return import_base_catalog(
        db=db,
        source_tenant_id=_resolve_source_tenant_id(db),
        target_tenant_id=target_tenant_id,
        user_id=target_user_id,
        dry_run=False,
    )
