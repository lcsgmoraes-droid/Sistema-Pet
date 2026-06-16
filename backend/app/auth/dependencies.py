"""
Dependências de Autenticação
=============================

Funções de dependência para FastAPI validar permissões de usuários.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from uuid import UUID
from jose import jwt, JWTError
from .core import get_current_user  # Importa do módulo local core.py
from app.db import get_session
from app.models import Tenant, User, UserTenant
from app.config import JWT_SECRET_KEY
from app.auth.core import ALGORITHM
from app.session_manager import get_session_by_jti

security = HTTPBearer()


def _tenant_status_is_active(status_value: object) -> bool:
    return str(status_value or "").strip().lower() in {"active", "ativo"}


async def get_current_user_and_tenant(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> tuple[User, UUID]:
    """
    DEPENDENCY OFICIAL PARA ROTAS MULTI-TENANT.

    SOLUÇÃO DEFINITIVA:
    - Lê tenant_id DIRETAMENTE do JWT token (não usa ContextVar)
    - Garante que tenant_id está presente
    - Evita qualquer problema com ContextVar

    Args:
        credentials: Token JWT
        user: Usuário autenticado (injetado por get_current_user)

    Returns:
        tuple[User, UUID]: (usuário, tenant_id)

    Raises:
        HTTPException 401: Se tenant_id não estiver no token
    """
    import logging

    logger = logging.getLogger(__name__)

    token = credentials.credentials

    try:
        # Decodificar token novamente para extrair tenant_id
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        tenant_id_str = payload.get("tenant_id")
        token_jti = payload.get("jti")
        user_email = payload.get("sub")  # email do usuário

        logger.debug(f"[AUTH] User: {user_email} | Tenant ID no JWT: {tenant_id_str}")
        logger.debug(f"[get_current_user_and_tenant] tenant_id no JWT: {tenant_id_str}")

        if not tenant_id_str:
            logger.error(
                "[get_current_user_and_tenant] ERRO: tenant_id não está no JWT!"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tenant não selecionado. Use /auth/select-tenant.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not token_jti:
            logger.error("[get_current_user_and_tenant] ERRO: token sem JTI")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sessao invalida. Faca login novamente.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Converter para UUID
        try:
            tenant_id = UUID(tenant_id_str)
            logger.debug(
                f"[get_current_user_and_tenant] tenant_id convertido: {tenant_id}"
            )
        except (ValueError, TypeError) as e:
            logger.error(
                f"[get_current_user_and_tenant] Erro ao converter tenant_id: {e}"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tenant inválido no token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 🔒 CRÍTICO: Configurar contexto de tenant para injeção automática
        from app.tenancy.context import set_current_tenant

        set_current_tenant(tenant_id)
        logger.debug(f"[MULTI-TENANT] Contexto configurado: tenant_id={tenant_id}")

        user_tenant = (
            db.query(UserTenant)
            .filter(
                UserTenant.user_id == user.id,
                UserTenant.tenant_id == tenant_id,
                UserTenant.is_active.is_(True),
            )
            .first()
        )

        if not user_tenant:
            logger.warning(
                "[get_current_user_and_tenant] Acesso negado: user_id=%s tenant_id=%s sem vinculo ativo",
                user.id,
                tenant_id,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario nao tem acesso ativo ao tenant selecionado",
            )

        tenant = db.query(Tenant).filter(Tenant.id == str(tenant_id)).first()
        if not tenant or not _tenant_status_is_active(tenant.status):
            logger.warning(
                "[get_current_user_and_tenant] Acesso negado: tenant_id=%s inativo ou inexistente",
                tenant_id,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant inativo ou indisponivel",
            )

        db_session = get_session_by_jti(db, token_jti)
        if not db_session or db_session.user_id != user.id:
            logger.warning(
                "[get_current_user_and_tenant] Sessao/JTI invalida para user_id=%s tenant_id=%s",
                user.id,
                tenant_id,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sessao invalida. Faca login novamente.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if db_session.tenant_id and str(db_session.tenant_id) != str(tenant_id):
            logger.warning(
                "[get_current_user_and_tenant] Sessao pertence a outro tenant: session=%s jwt=%s",
                db_session.tenant_id,
                tenant_id,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sessao pertence a outro tenant. Faca login novamente.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if db_session.tenant_id is None:
            db_session.tenant_id = tenant_id
            db.flush()

        logger.debug(
            f"[get_current_user_and_tenant] Retornando user.id={user.id} + tenant_id={tenant_id}"
        )
        return user, tenant_id

    except JWTError as e:
        logger.error(f"[get_current_user_and_tenant] Erro ao decodificar JWT: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency que requer permissão de administrador.

    Uso:
        @router.get("/admin-only")
        def admin_endpoint(user: User = Depends(require_admin)):
            return {"message": "Admin access granted"}

    Args:
        current_user: Usuário atual (injetado por get_current_user)

    Returns:
        User: Usuário autenticado com permissão de admin

    Raises:
        HTTPException 403: Se usuário não é administrador
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas administradores podem acessar este recurso.",
        )

    return current_user


def require_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency que requer usuário ativo.

    (Já validado em get_current_user, mas explícito para clareza)

    Args:
        current_user: Usuário atual

    Returns:
        User: Usuário ativo

    Raises:
        HTTPException 403: Se usuário está inativo
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo. Entre em contato com o administrador.",
        )

    return current_user


def get_current_tenant(
    user_and_tenant: tuple[User, UUID] = Depends(get_current_user_and_tenant),
) -> UUID:
    """
    Dependency que retorna apenas o tenant_id como UUID.

    Útil para rotas que precisam apenas do tenant_id sem o usuário.

    Args:
        user_and_tenant: Tupla (user, tenant_id) injetada

    Returns:
        UUID: tenant_id
    """
    _, tenant_id = user_and_tenant
    return tenant_id
