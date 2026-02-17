"""
Gerenciamento de Sessões - LGPD Compliance
Sistema de logout remoto e controle de dispositivos ativos
"""
from sqlalchemy.orm import Session as DBSession
from app.models import UserSession, User
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
import uuid
import json


def create_session(
    db: DBSession,
    user_id: int,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    device_info: Optional[Dict[str, Any]] = None,
    expires_in_days: int = 30
) -> UserSession:
    """
    Cria uma nova sessão para o usuário.
    
    Args:
        db: Sessão do SQLAlchemy
        user_id: ID do usuário
        ip_address: Endereço IP
        user_agent: String do User-Agent
        device_info: Informações do dispositivo (SO, navegador, etc)
        expires_in_days: Dias até expiração (padrão 30)
    
    Returns:
        UserSession: Objeto da sessão criada
    """
    token_jti = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
    
    session = UserSession(
        user_id=user_id,
        token_jti=token_jti,
        ip_address=ip_address,
        user_agent=user_agent,
        device_info=json.dumps(device_info) if device_info else None,
        expires_at=expires_at
    )
    
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return session


def get_active_sessions(db: DBSession, user_id: int) -> List[UserSession]:
    """
    Retorna todas as sessões ativas de um usuário.
    """
    now = datetime.now(timezone.utc)
    return db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.revoked == False,
        UserSession.expires_at > now
    ).order_by(UserSession.last_activity_at.desc()).all()


def get_session_by_jti(db: DBSession, token_jti: str) -> Optional[UserSession]:
    """
    Busca uma sessão pelo JWT ID (JTI).
    """
    return db.query(UserSession).filter(UserSession.token_jti == token_jti).first()


def validate_session(db: DBSession, token_jti: str) -> bool:
    """
    Valida se uma sessão está ativa e não expirou.
    Atualiza last_activity_at automaticamente.
    """
    session = get_session_by_jti(db, token_jti)
    
    if not session:
        return False
    
    if session.revoked:
        return False
    
    now = datetime.now(timezone.utc)
    expires_at = session.expires_at
    
    # Se expires_at for naive (vindo do SQLite), adicionar timezone UTC
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if expires_at <= now:
        return False
    
    # Atualiza last_activity_at
    session.last_activity_at = now
    db.flush()
    
    return True


def revoke_session(
    db: DBSession,
    session_id: int,
    user_id: int,
    reason: str = "user_logout"
) -> bool:
    """
    Revoga uma sessão específica do usuário.
    """
    session = db.query(UserSession).filter(
        UserSession.id == session_id,
        UserSession.user_id == user_id
    ).first()
    
    if not session:
        return False
    
    session.revoked = True
    session.revoked_at = datetime.now(timezone.utc)
    session.revoke_reason = reason
    db.commit()
    
    return True


def revoke_all_sessions(
    db: DBSession,
    user_id: int,
    except_jti: Optional[str] = None,
    reason: str = "logout_all_devices"
) -> int:
    """
    Revoga todas as sessões do usuário, exceto a atual (opcional).
    
    Args:
        db: Sessão do SQLAlchemy
        user_id: ID do usuário
        except_jti: JTI da sessão atual a manter ativa (opcional)
        reason: Motivo da revogação
    
    Returns:
        int: Número de sessões revogadas
    """
    query = db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.revoked == False
    )
    
    if except_jti:
        query = query.filter(UserSession.token_jti != except_jti)
    
    sessions = query.all()
    count = 0
    
    now = datetime.now(timezone.utc)
    for session in sessions:
        session.revoked = True
        session.revoked_at = now
        session.revoke_reason = reason
        count += 1
    
    db.commit()
    return count


def cleanup_expired_sessions(db: DBSession) -> int:
    """
    Remove sessões expiradas do banco (limpeza periódica).
    """
    now = datetime.now(timezone.utc)
    deleted = db.query(UserSession).filter(
        UserSession.expires_at < now
    ).delete()
    db.commit()
    return deleted
