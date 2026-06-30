from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session

from app.ia.aba5_models import FluxoCaixa
from app.models import User


def _get_user_tenant_id(usuario_id: int, db: Session) -> Optional[str]:
    """Busca o tenant_id do usuário"""
    user = db.query(User).filter(User.id == usuario_id).first()
    return user.tenant_id if user else None


def _resolve_tenant_id(
    usuario_id: int, db: Session, tenant_id: Optional[str] = None
) -> Optional[str]:
    if tenant_id:
        return str(tenant_id)
    tenant = _get_user_tenant_id(usuario_id, db)
    return str(tenant) if tenant else None


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _saldo_realizado_atual(usuario_id: int, tenant_id: str, db: Session) -> float:
    saldo = (
        db.query(
            func.sum(
                case(
                    (FluxoCaixa.tipo == "receita", FluxoCaixa.valor),
                    else_=-FluxoCaixa.valor,
                )
            )
        )
        .filter(
            and_(
                FluxoCaixa.usuario_id == usuario_id,
                FluxoCaixa.tenant_id == tenant_id,
                FluxoCaixa.status == "realizado",
            )
        )
        .scalar()
        or 0.0
    )
    return float(saldo)
