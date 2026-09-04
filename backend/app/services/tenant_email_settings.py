"""Configurações de resposta de e-mail específicas de cada empresa."""

from email_validator import EmailNotValidError, validate_email
from sqlalchemy.orm import Session


def _normalize_email(value: object) -> str | None:
    raw_value = str(value or "").strip()
    if not raw_value:
        return None
    try:
        return validate_email(raw_value, check_deliverability=False).normalized
    except EmailNotValidError:
        return None


def resolve_tenant_reply_to(db: Session, tenant_id: object) -> str | None:
    """Retorna o e-mail que deve receber respostas, sempre limitado ao tenant."""
    from app.models import Tenant

    tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
    if not tenant:
        return None

    return _normalize_email(
        getattr(tenant, "email_resposta", None)
    ) or _normalize_email(getattr(tenant, "email", None))
