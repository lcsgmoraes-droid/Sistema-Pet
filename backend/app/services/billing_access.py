"""Prazo de tolerancia operacional para cobrancas vencidas."""

from datetime import date, datetime, timedelta

from app.utils.timezone import now_brasilia


OVERDUE_GRACE_DAYS = 15


def overdue_grace_state(tenant: object, today: date | None = None) -> dict:
    """O acesso so e suspenso depois de 15 dias completos de atraso."""
    status = str(getattr(tenant, "billing_status", "") or "").strip().lower()
    if status != "past_due":
        return {
            "in_grace": False,
            "access_allowed": False,
            "days_until_block": None,
            "block_on": None,
        }

    due_date = getattr(tenant, "billing_next_due_date", None)
    if isinstance(due_date, datetime):
        due_date = due_date.date()
    if not isinstance(due_date, date):
        # Sem vencimento confiavel, nao aplicar bloqueio automatico.
        return {
            "in_grace": True,
            "access_allowed": True,
            "days_until_block": None,
            "block_on": None,
        }

    today = today or now_brasilia().date()
    block_on = due_date + timedelta(days=OVERDUE_GRACE_DAYS + 1)
    days_until_block = max(0, (block_on - today).days)
    in_grace = today < block_on
    return {
        "in_grace": in_grace,
        "access_allowed": in_grace,
        "days_until_block": days_until_block,
        "block_on": block_on.isoformat(),
    }
