"""
Autenticação JWT e gerenciamento de usuários
Sistema Pet Shop Pro
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session as DBSession
from app import db, models
from app.config import JWT_SECRET_KEY

# Configurações JWT
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

security = HTTPBearer()


def hash_password(password: str) -> str:
    """
    Hash de senha usando bcrypt.
    bcrypt tem limite de 72 bytes, por isso truncamos.
    """
    senha_bytes = password.encode('utf-8')[:72]
    hashed = bcrypt.hashpw(senha_bytes, bcrypt.gensalt())
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica senha contra hash.
    Retorna False para usuários OAuth (sem senha).
    """
    if not hashed_password:
        return False
    senha_bytes = plain_password.encode('utf-8')[:72]
    return bcrypt.checkpw(senha_bytes, hashed_password.encode('utf-8'))


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
    jti: Optional[str] = None
) -> str:
    """
    Cria token JWT com suporte a JTI (JWT ID) para gerenciamento de sessões.
    
    Args:
        data: Dados a incluir no token (ex: {"sub": user_id})
        expires_delta: Tempo de expiração customizado
        jti: JWT ID para controle de sessões (opcional)
    
    Returns:
        Token JWT codificado
    """
    to_encode = data.copy()
    
    # JWT exige que "sub" seja string
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    
    # Definir expiração
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire})
    
    # Adicionar JTI se fornecido (para logout remoto/controle de sessões)
    if jti:
        to_encode["jti"] = jti
    
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: DBSession = Depends(db.get_session)
) -> models.User:
    """
    Dependency para obter usuário atual via JWT token.
    
    ⚠️ ATENÇÃO (Phase 1.2):
    - Esta dependency NÃO extrai tenant_id
    - NÃO define contexto de tenant
    - Retorna APENAS o objeto User
    
    Para rotas multi-tenant, use:
        get_current_user_and_tenant (app/auth/dependencies.py)
    
    Uso em rotas públicas ou de autenticação:
        @router.get("/me")
        def get_me(current_user: User = Depends(get_current_user)):
            return current_user
    
    Raises:
        HTTPException 401: Se token inválido ou usuário inativo
    """
    from app.session_manager import validate_session
    
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        jti = payload.get("jti")  # JWT ID para validação de sessão
        
        if user_id is None:
            raise credentials_exception
        
        try:
            user_id = int(user_id)
        except Exception:
            raise credentials_exception
        
        # Validar sessão se JTI estiver presente
        if jti and not validate_session(session, jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session revoked or expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
    except JWTError:
        raise credentials_exception
    
    # Buscar usuário no banco
    user = session.query(models.User).filter(models.User.id == user_id).first()
    
    if user is None or not user.is_active:
        raise credentials_exception
    
    return user


def get_current_user_from_token(token: str, session: DBSession) -> models.User:
    """
    Extrai usuário a partir de um token JWT (sem Depends).
    Usado internamente para validação de tokens em contextos não-HTTP.
    
    Args:
        token: Token JWT
        session: Sessão do banco
    
    Returns:
        User: Usuário autenticado
    
    Raises:
        HTTPException 401: Se token inválido
    """
    from app.session_manager import validate_session
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        jti = payload.get("jti")
        
        if user_id is None:
            raise credentials_exception
        
        try:
            user_id = int(user_id)
        except Exception:
            raise credentials_exception
        
        # Validar sessão se JTI estiver presente
        if jti and not validate_session(session, jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session revoked or expired",
            )
            
    except JWTError:
        raise credentials_exception
    
    user = session.query(models.User).filter(models.User.id == user_id).first()
    
    if user is None or not user.is_active:
        raise credentials_exception
    
    return user


def get_current_active_superuser(
    current_user: models.User = Depends(get_current_user)
) -> models.User:
    """
    Dependency para rotas que exigem permissão de admin/superuser.
    
    Uso:
        @router.delete("/users/{user_id}")
        def delete_user(
            user_id: int,
            admin: User = Depends(get_current_active_superuser)
        ):
            ...
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges"
        )
    return current_user
