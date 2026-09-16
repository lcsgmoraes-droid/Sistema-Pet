"""Identidade publica usada para localizar a empresa antes da autenticacao."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import TenantLoginName
from app.tenant_identity import normalize_tenant_name


MIN_LOGIN_NAME_LENGTH = 3
MAX_LOGIN_NAME_LENGTH = 120


class TenantLoginNameError(ValueError):
    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


@dataclass(frozen=True)
class TenantLoginNameChange:
    row: TenantLoginName
    old_name: str | None
    new_name: str
    changed: bool


def clean_tenant_login_name(value: str | None) -> tuple[str, str]:
    clean_name = " ".join(str(value or "").strip().split())
    if len(clean_name) < MIN_LOGIN_NAME_LENGTH:
        raise TenantLoginNameError(
            f"O nome de acesso deve ter pelo menos {MIN_LOGIN_NAME_LENGTH} caracteres."
        )
    if len(clean_name) > MAX_LOGIN_NAME_LENGTH:
        raise TenantLoginNameError(
            f"O nome de acesso deve ter no maximo {MAX_LOGIN_NAME_LENGTH} caracteres."
        )

    normalized = normalize_tenant_name(clean_name)
    if len(normalized) < MIN_LOGIN_NAME_LENGTH:
        raise TenantLoginNameError("Informe um nome de acesso valido.")
    return clean_name, normalized


def _tenant_key(tenant_id) -> str:
    return str(tenant_id if isinstance(tenant_id, UUID) else UUID(str(tenant_id)))


def _belongs_to_tenant(row: TenantLoginName, tenant_id: str) -> bool:
    return str(row.tenant_id) == tenant_id


def get_primary_tenant_login_name(db: Session, tenant_id) -> TenantLoginName | None:
    return (
        db.query(TenantLoginName)
        .filter(
            TenantLoginName.tenant_id == _tenant_key(tenant_id),
            TenantLoginName.is_primary.is_(True),
        )
        .first()
    )


def get_primary_tenant_login_name_value(
    db: Session, tenant_id, *, fallback: str | None = None
) -> str | None:
    row = get_primary_tenant_login_name(db, tenant_id)
    return row.name if row else fallback


def resolve_tenant_id_by_login_name(db: Session, value: str | None) -> UUID | None:
    normalized = normalize_tenant_name(value)
    if not normalized:
        return None
    row = (
        db.query(TenantLoginName)
        .filter(TenantLoginName.name_normalized == normalized)
        .first()
    )
    return UUID(str(row.tenant_id)) if row else None


def set_primary_tenant_login_name(
    db: Session,
    tenant_id,
    value: str | None,
) -> TenantLoginNameChange:
    """Troca o nome principal e preserva o anterior como alias de login."""
    clean_name, normalized = clean_tenant_login_name(value)
    tenant_key = _tenant_key(tenant_id)

    requested_row = (
        db.query(TenantLoginName)
        .filter(TenantLoginName.name_normalized == normalized)
        .with_for_update()
        .first()
    )
    if requested_row and not _belongs_to_tenant(requested_row, tenant_key):
        raise TenantLoginNameError(
            "Este nome de acesso ja esta em uso por outra empresa.",
            status_code=409,
        )

    current_row = (
        db.query(TenantLoginName)
        .filter(
            TenantLoginName.tenant_id == tenant_key,
            TenantLoginName.is_primary.is_(True),
        )
        .with_for_update()
        .first()
    )
    old_name = current_row.name if current_row else None

    if requested_row is not None and requested_row is current_row:
        changed = requested_row.name != clean_name
        requested_row.name = clean_name
        db.flush()
        return TenantLoginNameChange(requested_row, old_name, clean_name, changed)

    if current_row:
        current_row.is_primary = False
        db.flush()

    if requested_row:
        requested_row.name = clean_name
        requested_row.is_primary = True
        row = requested_row
    else:
        row = TenantLoginName(
            tenant_id=tenant_key,
            name=clean_name,
            name_normalized=normalized,
            is_primary=True,
        )
        db.add(row)

    db.flush()
    return TenantLoginNameChange(row, old_name, clean_name, old_name != clean_name)
