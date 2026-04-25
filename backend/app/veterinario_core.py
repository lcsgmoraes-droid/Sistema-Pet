"""Helpers compartilhados do modulo veterinario."""

import re
from datetime import date, datetime, time
from typing import Optional

from sqlalchemy.orm import Session

from .utils.timezone import now_brasilia, to_brasilia
from .veterinario_models import VetPartnerLink


def _get_tenant(current: tuple) -> tuple:
    """Extrai user e tenant_id do tuple retornado pelo Depends."""
    user, tenant_id = current
    return user, tenant_id


def _vet_now() -> datetime:
    return now_brasilia()


def _normalizar_datetime_vet(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if getattr(value, "tzinfo", None):
        try:
            return to_brasilia(value).replace(tzinfo=None)
        except Exception:
            return value.replace(tzinfo=None)
    return value


def _serializar_datetime_vet(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    try:
        if getattr(value, "tzinfo", None):
            return to_brasilia(value).replace(tzinfo=None)
    except Exception:
        if getattr(value, "tzinfo", None):
            return value.replace(tzinfo=None)
    return value


def _date_para_datetime_vet(value: Optional[date]) -> Optional[datetime]:
    if value is None:
        return None
    return datetime.combine(value, time(hour=12, minute=0))


def _get_partner_tenant_ids(db: Session, tenant_id) -> list:
    """Retorna lista de empresa_tenant_ids onde este vet e parceiro ativo."""
    links = db.query(VetPartnerLink).filter(
        VetPartnerLink.vet_tenant_id == str(tenant_id),
        VetPartnerLink.ativo == True,
    ).all()
    return [link.empresa_tenant_id for link in links]


def _all_accessible_tenant_ids(db: Session, tenant_id) -> list:
    """Retorna tenant_id atual + todos os tenants das empresas parceiras vinculadas."""
    return [str(tenant_id)] + _get_partner_tenant_ids(db, tenant_id)


def _parse_numeric_text(value) -> Optional[float]:
    if value is None:
        return None
    texto = str(value).strip()
    if not texto:
        return None

    texto = re.sub(r"[^0-9,.\-]", "", texto)
    if not texto:
        return None

    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif texto.count(",") == 1 and texto.count(".") == 0:
        texto = texto.replace(",", ".")
    elif texto.count(".") > 1 and texto.count(",") == 0:
        partes = texto.split(".")
        texto = "".join(partes[:-1]) + "." + partes[-1]

    try:
        return float(texto)
    except (TypeError, ValueError):
        return None
