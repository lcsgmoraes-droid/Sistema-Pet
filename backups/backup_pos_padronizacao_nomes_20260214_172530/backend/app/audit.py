"""
Módulo de auditoria simplificado
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from uuid import UUID

from app.models import AuditLog
from app.utils.logger import logger


def log_audit(
    db: Session,
    user_id: Optional[int],
    action: str,
    entity_type: str,
    entity_id: Optional[int] = None,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    tenant_id: Optional[UUID] = None
) -> Optional[AuditLog]:
    """
    Registra um evento de auditoria.
    """
    try:
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=old_value,
            new_value=new_value,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.now(timezone.utc),
            tenant_id=tenant_id
        )
        
        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)
        
        return audit_log
        
    except Exception as e:
        db.rollback()
        logger.info(f"⚠️  Erro ao registrar log de auditoria: {e}")
        return None
