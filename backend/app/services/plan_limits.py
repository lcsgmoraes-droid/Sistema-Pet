"""Medicao e aplicacao dos limites comerciais dos planos CorePet."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Tenant, UserSession
from app.services.plan_catalog import PLAN_CATALOG, get_plan
from app.utils.timezone import now_brasilia
from app.vendas_models import Venda


def _trial_is_active(tenant: Tenant, now_utc: datetime | None = None) -> bool:
    if str(getattr(tenant, "billing_status", "") or "").strip().lower() != "trial":
        return False

    ends_at = getattr(tenant, "trial_ends_at", None)
    if ends_at is None:
        return False
    if ends_at.tzinfo is None:
        ends_at = ends_at.replace(tzinfo=timezone.utc)
    return ends_at > (now_utc or datetime.now(timezone.utc))


def _month_bounds(now: datetime | None = None) -> tuple[datetime, datetime]:
    current = now or now_brasilia()
    start = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def monthly_sales_usage(
    db: Session, tenant_id: str | UUID, now: datetime | None = None
) -> int:
    start, end = _month_bounds(now)
    return (
        db.query(Venda)
        .filter(
            Venda.tenant_id == tenant_id,
            Venda.data_venda >= start,
            Venda.data_venda < end,
            Venda.status != "cancelada",
        )
        .count()
    )


def enforce_monthly_sales_limit(
    db: Session, tenant_id: str | UUID | None, now: datetime | None = None
) -> None:
    if not tenant_id:
        return

    tenant = (
        db.query(Tenant).filter(Tenant.id == str(tenant_id)).with_for_update().first()
    )
    if tenant is None or _trial_is_active(tenant):
        return

    raw_plan = str(getattr(tenant, "plan", "") or "").strip().lower()
    billing_status = str(getattr(tenant, "billing_status", "active") or "active")
    if raw_plan in PLAN_CATALOG and billing_status.strip().lower() in {
        "trial",
        "expired",
        "blocked",
        "canceled",
    }:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": "subscription_inactive",
                "message": (
                    "O periodo gratuito terminou. Ative um plano para registrar novas vendas."
                ),
            },
        )

    plan = get_plan(getattr(tenant, "plan", None))
    limit = plan.monthly_sales_limit if plan else None
    if limit is None:
        return

    used = monthly_sales_usage(db, tenant_id, now)
    if used < limit:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "code": "monthly_sales_limit_reached",
            "message": (
                f"O limite de {limit} vendas deste mes foi atingido. "
                "Escolha um plano com vendas ilimitadas para continuar vendendo."
            ),
            "plano": plan.code,
            "limite": limit,
            "uso": used,
        },
    )


def active_session_usage(db: Session, tenant_id: str | UUID) -> int:
    session_tenant_id = _session_tenant_id(tenant_id)
    return (
        db.query(UserSession)
        .filter(
            UserSession.tenant_id == session_tenant_id,
            UserSession.revoked.is_(False),
            UserSession.expires_at > datetime.now(timezone.utc),
        )
        .count()
    )


def enforce_simultaneous_session_limit(
    db: Session,
    tenant: Tenant,
    current_session: UserSession,
    now_utc: datetime | None = None,
) -> int:
    """Revoga as sessoes mais antigas para manter o limite do plano.

    O login mais recente prevalece, portanto no Start abrir em outro computador
    derruba a sessao anterior, como definido na oferta comercial.
    """

    now = now_utc or datetime.now(timezone.utc)
    if _trial_is_active(tenant, now):
        return 0

    plan = get_plan(getattr(tenant, "plan", None))
    limit = plan.simultaneous_sessions_limit if plan else None
    if limit is None:
        return 0

    session_tenant_id = _session_tenant_id(tenant.id)
    active = (
        db.query(UserSession)
        .filter(
            UserSession.tenant_id == session_tenant_id,
            UserSession.token_jti != current_session.token_jti,
            UserSession.revoked.is_(False),
            UserSession.expires_at > now,
        )
        .order_by(UserSession.last_activity_at.asc(), UserSession.created_at.asc())
        .all()
    )

    revoke_count = max(0, len(active) - limit + 1)
    for session in active[:revoke_count]:
        session.revoked = True
        session.revoked_at = now
        session.revoke_reason = "plan_simultaneous_session_limit"
    return revoke_count


def _session_tenant_id(tenant_id: str | UUID) -> str | UUID:
    try:
        return UUID(str(tenant_id))
    except (TypeError, ValueError):
        return tenant_id
