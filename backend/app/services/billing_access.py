"""Cobranca informativa e continuidade operacional ate decisao administrativa."""

from datetime import date, datetime, timezone

from app.utils.timezone import BRASILIA_TZ, now_brasilia


OVERDUE_GRACE_DAYS = 15


def normalize_billing_status(value: object) -> str:
    status = str(value or "active").strip().lower()
    if status in {"overdue", "late", "inadimplente"}:
        return "past_due"
    if status in {"paid", "ok", "em_dia"}:
        return "active"
    return status


def operational_access_allowed(tenant: object) -> bool:
    """Somente o status cadastral, alterado pela administracao, suspende acesso."""
    status = str(getattr(tenant, "status", "active") or "").strip().lower()
    return status in {"active", "ativo"}


def manual_full_access_allowed(tenant: object) -> bool:
    """Concessao sem vencimento; suspensao cadastral continua soberana."""
    return getattr(
        tenant, "manual_full_access", False
    ) is True and operational_access_allowed(tenant)


def trial_access_preserved(tenant: object, now: datetime | None = None) -> bool:
    """O fim do teste encaminha revisao, sem retirar recursos em uso."""
    if not operational_access_allowed(tenant):
        return False
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    ends_at = getattr(tenant, "trial_ends_at", None)
    if isinstance(ends_at, datetime):
        if ends_at.tzinfo is None:
            ends_at = ends_at.replace(tzinfo=timezone.utc)
        # Um pagamento antecipado preserva a experiencia completa ate o fim.
        if ends_at > now:
            return True
    trial_registered = bool(getattr(tenant, "trial_started_at", None) or ends_at)
    billing_status = normalize_billing_status(getattr(tenant, "billing_status", None))
    pending_review = billing_status in {
        "trial",
        "expired",
        "pending",
        "past_due",
        "overdue",
        "late",
        "inadimplente",
        "blocked",
        "refunded",
        "canceled",
    }
    return (
        trial_registered
        and pending_review
        and not getattr(tenant, "subscription_activated_at", None)
    )


def billing_warning_state(
    tenant: object, today: date | None = None, *, effective_status: str | None = None
) -> dict:
    """Escalona avisos; nenhuma etapa agenda ou executa bloqueio automatico."""
    today = today or now_brasilia().date()
    status = normalize_billing_status(
        effective_status or getattr(tenant, "billing_status", None)
    )
    stage = None
    overdue_days = None
    review_required = False
    if status in {"past_due", "overdue", "late", "inadimplente"}:
        due_date = getattr(tenant, "billing_next_due_date", None)
        if isinstance(due_date, datetime):
            due_date = due_date.date()
        if isinstance(due_date, date):
            overdue_days = max(0, (today - due_date).days)
            stage = (
                "lembrete"
                if overdue_days <= 7
                else "atencao"
                if overdue_days <= OVERDUE_GRACE_DAYS
                else "revisao_manual"
            )
        else:
            stage = "atencao"
        review_required = stage == "revisao_manual" or overdue_days is None
    elif status in {"expired", "blocked", "refunded", "canceled"}:
        stage = "revisao_manual"
        review_required = True
    elif status == "trial":
        ends_at = getattr(tenant, "trial_ends_at", None)
        if isinstance(ends_at, datetime):
            if ends_at.tzinfo is None:
                ends_at = ends_at.replace(tzinfo=timezone.utc)
            if ends_at.astimezone(BRASILIA_TZ).date() < today:
                stage = "revisao_manual"
                review_required = True
    elif status == "pending":
        stage = "lembrete"
    return {
        "etapa": stage,
        "dias_atraso": overdue_days,
        "requer_revisao": review_required,
    }


def overdue_grace_state(tenant: object, today: date | None = None) -> dict:
    """Contrato legado de tolerancia, agora sem data para bloqueio automatico."""
    status = normalize_billing_status(getattr(tenant, "billing_status", None))
    return {
        "in_grace": status == "past_due" and operational_access_allowed(tenant),
        "access_allowed": operational_access_allowed(tenant),
        "days_until_block": None,
        "block_on": None,
    }
