"""
Sistema de Auditoria - LGPD Compliance
Registra todas as ações importantes no sistema
"""

from sqlalchemy.orm import Session as DBSession
from app.models import AuditLog
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID
import json
from app.utils.logger import logger
from app.tenancy.context import get_current_tenant


def _resolver_tenant_id(tenant_id: Optional[Any]):
    valor = tenant_id or get_current_tenant()
    if not valor:
        return None
    if isinstance(valor, UUID):
        return valor
    return UUID(str(valor))


def log_action(
    db: DBSession,
    user_id: Optional[int],
    action: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    old_value: Optional[Dict[str, Any]] = None,
    new_value: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[str] = None,
    tenant_id: Optional[Any] = None,
    commit: bool = True,
):
    """
    Registra uma ação no log de auditoria.

    Args:
        db: Sessão do banco
        user_id: ID do usuário (None para ações do sistema)
        action: Ação realizada (ex: "login", "create_product", "delete_sale")
        entity_type: Tipo de entidade afetada (ex: "product", "sale", "user")
        entity_id: ID da entidade afetada
        old_value: Valor anterior (para updates/deletes)
        new_value: Valor novo (para creates/updates)
        ip_address: IP da requisição
        user_agent: User-Agent da requisição
        details: Detalhes adicionais
    """
    try:
        tenant_id_resolvido = _resolver_tenant_id(tenant_id)
        if tenant_id_resolvido is None:
            logger.warning(
                "audit_log_skipped",
                "Log de auditoria ignorado por falta de tenant_id",
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
            )
            return None

        log = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=json.dumps(old_value) if old_value else None,
            new_value=json.dumps(new_value) if new_value else None,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
            timestamp=datetime.now(timezone.utc),
            tenant_id=tenant_id_resolvido,
        )

        db.add(log)
        if commit:
            db.commit()
        else:
            db.flush()
        return log
    except Exception as e:
        logger.warning(
            "audit_log_error",
            f"Erro ao registrar log de auditoria: {e}",
            exception=str(e),
        )
        if commit:
            db.rollback()
        else:
            raise


# Atalhos para ações comuns


def log_login(
    db: DBSession, user_id: int, ip: str, user_agent: str, success: bool = True
):
    """Registra tentativa de login"""
    log_action(
        db,
        user_id,
        action="login_success" if success else "login_failed",
        entity_type="user",
        entity_id=user_id,
        ip_address=ip,
        user_agent=user_agent,
    )


def log_logout(db: DBSession, user_id: int, ip: str):
    """Registra logout"""
    log_action(
        db,
        user_id,
        action="logout",
        entity_type="user",
        entity_id=user_id,
        ip_address=ip,
    )


def log_create(
    db: DBSession,
    user_id: int,
    entity_type: str,
    entity_id: int,
    data: dict,
    ip: str = None,
):
    """Registra criação de entidade"""
    log_action(
        db,
        user_id,
        action=f"create_{entity_type}",
        entity_type=entity_type,
        entity_id=entity_id,
        new_value=data,
        ip_address=ip,
    )


def log_update(
    db: DBSession,
    user_id: int,
    entity_type: str,
    entity_id: int,
    old_data: dict,
    new_data: dict,
    ip: str = None,
):
    """Registra atualização de entidade"""
    log_action(
        db,
        user_id,
        action=f"update_{entity_type}",
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=old_data,
        new_value=new_data,
        ip_address=ip,
    )


def log_delete(
    db: DBSession,
    user_id: int,
    entity_type: str,
    entity_id: int,
    data: dict,
    ip: str = None,
):
    """Registra exclusão de entidade"""
    log_action(
        db,
        user_id,
        action=f"delete_{entity_type}",
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=data,
        ip_address=ip,
    )
