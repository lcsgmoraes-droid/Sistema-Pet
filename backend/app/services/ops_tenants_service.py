from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.ops_models import OpsTenantOnboardingNote
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
    "produto_imagens": "produto_imagens",
    "agendamentos_vet": "vet_agendamentos",
    "consultas_vet": "vet_consultas",
}

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
BUSINESS_TIMEZONE = ZoneInfo("America/Sao_Paulo")


class OpsTenantActionError(RuntimeError):
    pass


def _table_exists(db: Session, table_name: str) -> bool:
    return inspect(db.connection()).has_table(table_name)


def _column_exists(db: Session, table_name: str, column_name: str) -> bool:
    if not _table_exists(db, table_name):
        return False
    return column_name in {
        column["name"] for column in inspect(db.connection()).get_columns(table_name)
    }


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except ValueError:
        return None


def _business_today() -> date:
    return datetime.now(BUSINESS_TIMEZONE).date()


def _count_by_tenant(db: Session, table_name: str, tenant_id: str) -> int:
    if not _table_exists(db, table_name):
        return 0
    return int(
        db.execute(
            text(
                f"SELECT COUNT(*) FROM {table_name} WHERE CAST(tenant_id AS TEXT) = :tenant_id"
            ),
            {"tenant_id": tenant_id},
        ).scalar()
        or 0
    )


def _count_users(db: Session, tenant_id: str) -> int:
    if _table_exists(db, "user_tenants"):
        return int(
            db.execute(
                text("""
                    SELECT COUNT(DISTINCT user_id)
                    FROM user_tenants
                    WHERE CAST(tenant_id AS TEXT) = :tenant_id
                      AND COALESCE(CAST(is_active AS TEXT), 'true') NOT IN ('false', '0')
                    """),
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

    row = (
        db.execute(
            text("""
            SELECT id, email, nome, is_active, is_admin, email_verified, last_login_at
            FROM users
            WHERE CAST(tenant_id AS TEXT) = :tenant_id
            ORDER BY is_admin DESC, id ASC
            LIMIT 1
            """),
            {"tenant_id": tenant_id},
        )
        .mappings()
        .first()
    )

    if not row and _table_exists(db, "user_tenants"):
        row = (
            db.execute(
                text("""
                SELECT u.id, u.email, u.nome, u.is_active, u.is_admin,
                       u.email_verified, u.last_login_at
                FROM user_tenants ut
                JOIN users u ON u.id = ut.user_id
                WHERE CAST(ut.tenant_id AS TEXT) = :tenant_id
                ORDER BY u.is_admin DESC, u.id ASC
                LIMIT 1
                """),
                {"tenant_id": tenant_id},
            )
            .mappings()
            .first()
        )

    if not row:
        return None
    return {
        "id": int(row["id"]),
        "email": row["email"],
        "nome": row.get("nome"),
        "is_active": bool(row.get("is_active")),
        "is_admin": bool(row.get("is_admin")),
        "email_verified": bool(row.get("email_verified")),
        "last_login_at": _iso(row.get("last_login_at")),
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

    row = (
        db.execute(
            text("""
            SELECT status, updated_at, created_at, created_by_user_id
            FROM tenant_template_installs
            WHERE CAST(tenant_id AS TEXT) = :tenant_id
              AND bundle_code = :bundle_code
              AND bundle_version = :bundle_version
            ORDER BY updated_at DESC, created_at DESC, id DESC
            LIMIT 1
            """),
            {
                "tenant_id": tenant_id,
                "bundle_code": DEFAULT_BASE_CATALOG_BUNDLE_CODE,
                "bundle_version": DEFAULT_BASE_CATALOG_BUNDLE_VERSION,
            },
        )
        .mappings()
        .first()
    )
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
    counts = {
        label: _count_by_tenant(db, table_name, tenant_id)
        for label, table_name in COUNT_TABLES.items()
    }
    counts["usuarios"] = _count_users(db, tenant_id)
    return counts


def _image_bytes(db: Session, tenant_id: str) -> int:
    if not _table_exists(db, "produto_imagens"):
        return 0
    return int(
        db.execute(
            text("""
                SELECT COALESCE(SUM(COALESCE(tamanho, 0)), 0)
                FROM produto_imagens
                WHERE CAST(tenant_id AS TEXT) = :tenant_id
                """),
            {"tenant_id": tenant_id},
        ).scalar()
        or 0
    )


def _tenant_usage(
    db: Session, tenant_id: str, counts: dict[str, int]
) -> dict[str, Any]:
    image_bytes = _image_bytes(db, tenant_id)
    return {
        "records_total": sum(int(value or 0) for value in counts.values()),
        "image_count": int(counts.get("produto_imagens") or 0),
        "image_bytes": image_bytes,
        "image_mb": round(image_bytes / 1024 / 1024, 2),
    }


def _latest_tenant_timestamp(
    db: Session, tenant_id: str, table_name: str, column_name: str
) -> str | None:
    if not _column_exists(db, table_name, column_name):
        return None
    value = db.execute(
        text(f"""
            SELECT MAX({column_name})
            FROM {table_name}
            WHERE CAST(tenant_id AS TEXT) = :tenant_id
            """),
        {"tenant_id": tenant_id},
    ).scalar()
    return _iso(value)


def _latest_user_login(db: Session, tenant_id: str) -> str | None:
    if not _column_exists(db, "users", "last_login_at"):
        return None
    candidates = [
        db.execute(
            text("""
                SELECT MAX(last_login_at)
                FROM users
                WHERE CAST(tenant_id AS TEXT) = :tenant_id
                """),
            {"tenant_id": tenant_id},
        ).scalar()
    ]
    if _table_exists(db, "user_tenants"):
        candidates.append(
            db.execute(
                text("""
                    SELECT MAX(u.last_login_at)
                    FROM user_tenants ut
                    JOIN users u ON u.id = ut.user_id
                    WHERE CAST(ut.tenant_id AS TEXT) = :tenant_id
                    """),
                {"tenant_id": tenant_id},
            ).scalar()
        )
    parsed = []
    for value in candidates:
        parsed_value = _parse_datetime(value)
        if parsed_value is not None:
            parsed.append((parsed_value, value))
    return _iso(max(parsed, key=lambda item: item[0])[1]) if parsed else None


def _pilot_errors_7d(db: Session, tenant_id: str) -> int:
    if not _table_exists(db, "ops_error_events"):
        return 0
    since = datetime.now(timezone.utc) - timedelta(days=7)
    return int(
        db.execute(
            text("""
                SELECT COUNT(*)
                FROM ops_error_events
                WHERE CAST(tenant_id AS TEXT) = :tenant_id
                  AND status_code >= 500
                  AND created_at >= :since
                """),
            {"tenant_id": tenant_id, "since": since},
        ).scalar()
        or 0
    )


def _pilot_critical_alerts(db: Session, tenant_id: str) -> int:
    if not _table_exists(db, "ops_alerts"):
        return 0
    return int(
        db.execute(
            text("""
                SELECT COUNT(*)
                FROM ops_alerts
                WHERE CAST(tenant_id AS TEXT) = :tenant_id
                  AND lower(severity) = 'critical'
                  AND lower(status) = 'open'
                """),
            {"tenant_id": tenant_id},
        ).scalar()
        or 0
    )


def _pilot_follow_up(
    *,
    days_since_start: int | None,
    access_confirmed: bool,
    setup_records: int,
    operational_events: int,
    errors_7d: int,
    critical_alerts_open: int,
    onboarding_owner_name: str | None,
    onboarding_satisfaction: str | None,
    onboarding_next_contact_on: date | str | None,
) -> dict[str, Any]:
    reasons: list[dict[str, Any]] = []
    overdue_milestones: list[str] = []

    def add_reason(
        code: str, label: str, severity: str, *, overdue_milestone: str | None = None
    ) -> None:
        reasons.append(
            {
                "code": code,
                "label": label,
                "severity": severity,
                "overdue": overdue_milestone is not None,
            }
        )
        if overdue_milestone:
            overdue_milestones.append(overdue_milestone)

    if critical_alerts_open:
        add_reason(
            "critical_alert",
            f"{critical_alerts_open} alerta(s) critico(s) aberto(s)",
            "critical",
        )
    if not access_confirmed:
        access_overdue = days_since_start is not None and days_since_start >= 1
        add_reason(
            "access_pending",
            "primeiro acesso ainda nao confirmado",
            "high" if access_overdue else "normal",
            overdue_milestone="D1" if access_overdue else None,
        )
    if errors_7d:
        add_reason(
            "recent_server_errors",
            f"{errors_7d} erro(s) 5xx nos ultimos 7 dias",
            "high",
        )
    if setup_records <= 0:
        setup_overdue = days_since_start is not None and days_since_start >= 3
        add_reason(
            "setup_pending",
            "cadastros iniciais ainda nao identificados",
            "high" if setup_overdue else "normal",
            overdue_milestone="D3" if setup_overdue else None,
        )
    if operational_events <= 0:
        operation_overdue = days_since_start is not None and days_since_start >= 7
        add_reason(
            "first_operation_pending",
            "primeira operacao ainda nao identificada",
            "high" if operation_overdue else "normal",
            overdue_milestone="D7" if operation_overdue else None,
        )

    owner_name = str(onboarding_owner_name or "").strip()
    satisfaction = str(onboarding_satisfaction or "not_collected").strip().lower()
    next_contact_on = _parse_date(onboarding_next_contact_on)
    today = _business_today()
    if next_contact_on and next_contact_on < today:
        add_reason(
            "follow_up_overdue",
            f"contato agendado para {next_contact_on.strftime('%d/%m/%Y')} esta atrasado",
            "high",
        )
    elif next_contact_on == today:
        add_reason(
            "follow_up_due_today",
            "contato de acompanhamento agendado para hoje",
            "normal",
        )
    if not owner_name:
        add_reason(
            "owner_pending",
            "responsavel pelo acompanhamento ainda nao definido",
            "normal",
        )
    if satisfaction == "dissatisfied":
        add_reason(
            "initial_dissatisfaction",
            "empresa informou insatisfacao no acompanhamento inicial",
            "high",
        )
    elif satisfaction == "neutral":
        add_reason(
            "initial_satisfaction_neutral",
            "satisfacao inicial neutra precisa de retorno",
            "normal",
        )
    elif satisfaction == "not_collected" and operational_events > 0:
        add_reason(
            "initial_satisfaction_pending",
            "satisfacao inicial ainda nao registrada",
            "normal",
        )

    severities = {reason["severity"] for reason in reasons}
    if "critical" in severities:
        attention_level = "critical"
    elif "high" in severities:
        attention_level = "high"
    elif reasons:
        attention_level = "normal"
    else:
        attention_level = "healthy"

    if critical_alerts_open:
        next_action = "Resolver o alerta critico e validar a jornada afetada."
    elif not access_confirmed:
        next_action = "Confirmar o primeiro acesso do responsavel pela empresa."
    elif errors_7d:
        next_action = "Investigar os erros 5xx antes do proximo acompanhamento."
    elif next_contact_on and next_contact_on <= today:
        next_action = (
            "Realizar o contato de acompanhamento agendado para "
            f"{next_contact_on.strftime('%d/%m/%Y')}."
        )
    elif setup_records <= 0:
        next_action = "Concluir os cadastros iniciais ou a importacao assistida."
    elif operational_events <= 0:
        next_action = "Acompanhar a primeira venda, agenda ou consulta."
    elif satisfaction == "dissatisfied":
        next_action = "Agendar retorno e tratar o motivo da insatisfacao inicial."
    elif not owner_name:
        next_action = "Definir o responsavel pelo acompanhamento desta empresa."
    elif satisfaction == "not_collected":
        next_action = "Confirmar e registrar a satisfacao inicial da empresa."
    elif satisfaction == "neutral":
        next_action = "Entender o que falta para a empresa ficar satisfeita."
    else:
        next_action = "Manter acompanhamento semanal."

    return {
        "attention_level": attention_level,
        "needs_follow_up": attention_level != "healthy",
        "attention_reasons": reasons,
        "overdue_milestones": overdue_milestones,
        "next_action": next_action,
    }


def _tenant_pilot_status(
    db: Session,
    *,
    tenant_id: str,
    row: dict[str, Any],
    principal_user: dict[str, Any] | None,
    counts: dict[str, int],
) -> dict[str, Any]:
    kind = (
        "veterinario"
        if str(row.get("organization_type") or "").lower() == "veterinary_clinic"
        or int(counts.get("agendamentos_vet") or 0) > 0
        or int(counts.get("consultas_vet") or 0) > 0
        else "plano_basico"
    )
    operational_events = int(counts.get("vendas") or 0)
    if kind == "veterinario":
        operational_events += int(counts.get("agendamentos_vet") or 0)
        operational_events += int(counts.get("consultas_vet") or 0)

    activity_candidates = [
        _latest_user_login(db, tenant_id),
        _latest_tenant_timestamp(db, tenant_id, "vendas", "data_venda"),
        _latest_tenant_timestamp(db, tenant_id, "vet_agendamentos", "created_at"),
        _latest_tenant_timestamp(db, tenant_id, "vet_consultas", "created_at"),
    ]
    parsed_activity = []
    for value in activity_candidates:
        parsed = _parse_datetime(value)
        if parsed is not None:
            parsed_activity.append((parsed, value))
    last_activity_at = (
        max(parsed_activity, key=lambda item: item[0])[1] if parsed_activity else None
    )

    errors_7d = _pilot_errors_7d(db, tenant_id)
    critical_alerts_open = _pilot_critical_alerts(db, tenant_id)
    access_confirmed = bool(
        principal_user
        and principal_user.get("is_active")
        and principal_user.get("email_verified")
        and principal_user.get("last_login_at")
    )
    setup_records = sum(
        int(counts.get(field) or 0) for field in ("produtos", "clientes", "pets")
    )

    if critical_alerts_open:
        status = "blocked"
    elif access_confirmed and operational_events:
        status = "active"
    elif access_confirmed and setup_records:
        status = "ready"
    else:
        status = "pending"

    started_at = row.get("subscription_activated_at") or row.get("created_at")
    parsed_start = _parse_datetime(started_at)
    days_since_start = (
        max((datetime.now(timezone.utc) - parsed_start).days, 0)
        if parsed_start
        else None
    )
    follow_up = _pilot_follow_up(
        days_since_start=days_since_start,
        access_confirmed=access_confirmed,
        setup_records=setup_records,
        operational_events=operational_events,
        errors_7d=errors_7d,
        critical_alerts_open=critical_alerts_open,
        onboarding_owner_name=row.get("onboarding_owner_name"),
        onboarding_satisfaction=row.get("onboarding_satisfaction"),
        onboarding_next_contact_on=row.get("onboarding_next_contact_on"),
    )
    return {
        "kind": kind,
        "status": status,
        "started_at": _iso(started_at),
        "days_since_start": days_since_start,
        "access_confirmed": access_confirmed,
        "setup_records": setup_records,
        "operational_events": operational_events,
        "last_activity_at": _iso(last_activity_at),
        "errors_7d": errors_7d,
        "critical_alerts_open": critical_alerts_open,
        "milestones": {
            "day_1_access": access_confirmed,
            "day_3_setup": setup_records > 0,
            "day_7_operation": operational_events > 0
            and errors_7d == 0
            and critical_alerts_open == 0,
        },
        **follow_up,
    }


def _is_billing_attention(status: str | None) -> bool:
    return str(status or "").strip().lower() in {
        "past_due",
        "overdue",
        "late",
        "inadimplente",
        "suspended",
        "blocked",
        "bloqueado",
    }


def _tenant_row_to_item(db: Session, row: dict[str, Any]) -> dict[str, Any]:
    tenant_id = str(row["id"])
    counts = _tenant_counts(db, tenant_id)
    principal_user = _principal_user(db, tenant_id)
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
        "principal_user": principal_user,
        "onboarding_follow_up": {
            "owner_name": row.get("onboarding_owner_name"),
            "unblocked_on": _iso(row.get("onboarding_unblocked_on")),
            "next_contact_on": _iso(row.get("onboarding_next_contact_on")),
            "satisfaction": row.get("onboarding_satisfaction") or "not_collected",
            "updated_at": _iso(row.get("onboarding_follow_up_updated_at")),
        },
        "counts": counts,
        "usage": _tenant_usage(db, tenant_id, counts),
        "base_catalog": _base_catalog_status(db, tenant_id),
        "pilot": _tenant_pilot_status(
            db,
            tenant_id=tenant_id,
            row=row,
            principal_user=principal_user,
            counts=counts,
        ),
    }


def _fetch_tenant_item(db: Session, tenant_id: str) -> dict[str, Any]:
    row = (
        db.execute(
            text("""
            SELECT id, name, status, plan, billing_status, subscription_source,
                   subscription_activated_at, organization_type,
                   onboarding_owner_name, onboarding_unblocked_on, onboarding_next_contact_on,
                   onboarding_satisfaction, onboarding_follow_up_updated_at,
                   created_at, updated_at
            FROM tenants
            WHERE CAST(id AS TEXT) = :tenant_id
            LIMIT 1
            """),
            {"tenant_id": tenant_id},
        )
        .mappings()
        .first()
    )
    if not row:
        raise OpsTenantActionError(f"Tenant nao encontrado: {tenant_id}.")
    return _tenant_row_to_item(db, dict(row))


def list_ops_tenants(
    db: Session,
    *,
    search: str | None = None,
    status: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    if not _table_exists(db, "tenants"):
        return {
            "items": [],
            "summary": {"total": 0, "active": 0, "with_base_catalog": 0},
        }

    clauses = []
    params: dict[str, Any] = {"limit": int(limit)}
    if search:
        clauses.append(
            "(lower(name) LIKE lower(:search) OR lower(CAST(id AS TEXT)) LIKE lower(:search))"
        )
        params["search"] = f"%{search.strip()}%"
    if status:
        clauses.append("lower(status) = lower(:status)")
        params["status"] = status.strip()

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = db.execute(
        text(f"""
            SELECT id, name, status, plan, billing_status, subscription_source,
                   subscription_activated_at, organization_type,
                   onboarding_owner_name, onboarding_unblocked_on, onboarding_next_contact_on,
                   onboarding_satisfaction, onboarding_follow_up_updated_at,
                   created_at, updated_at
            FROM tenants
            {where_sql}
            ORDER BY name ASC
            LIMIT :limit
            """),
        params,
    ).mappings()
    items = [_tenant_row_to_item(db, dict(row)) for row in rows]
    summary = {
        "total": len(items),
        "active": sum(
            1
            for item in items
            if str(item.get("status") or "").lower() in {"active", "ativo"}
        ),
        "with_base_catalog": sum(
            1 for item in items if item["base_catalog"]["installed"]
        ),
        "billing_attention": sum(
            1 for item in items if _is_billing_attention(item.get("billing_status"))
        ),
        "records_total": sum(
            int(item.get("usage", {}).get("records_total") or 0) for item in items
        ),
        "image_bytes": sum(
            int(item.get("usage", {}).get("image_bytes") or 0) for item in items
        ),
        "pilots_active": sum(
            1 for item in items if item.get("pilot", {}).get("status") == "active"
        ),
        "pilots_blocked": sum(
            1 for item in items if item.get("pilot", {}).get("status") == "blocked"
        ),
        "pilots_need_follow_up": sum(
            1 for item in items if bool(item.get("pilot", {}).get("needs_follow_up"))
        ),
    }
    return {"items": items, "summary": summary}


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
