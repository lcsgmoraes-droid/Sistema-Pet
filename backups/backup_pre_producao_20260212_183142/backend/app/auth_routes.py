"""
Rotas de Autenticação
Registro, Login, Logout, Recuperação de Senha
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session as DBSession
from app import db, models
from app.auth import hash_password, verify_password, create_access_token, get_current_user
from app.audit_log import log_login, log_logout, log_action
from app.session_manager import create_session, revoke_all_sessions, get_active_sessions
from datetime import datetime, timezone
import pyotp
import secrets

router = APIRouter()


# ====================
# SCHEMAS (PYDANTIC)
# ====================

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    nome: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    code_2fa: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    nome: Optional[str]
    is_admin: bool
    is_active: bool
    two_factor_enabled: bool
    consent_date: Optional[datetime]


# ====================
# ROTAS
# ====================

@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, session: DBSession = Depends(db.get_session)):
    """
    Criar nova conta de usuário.
    
    - **email**: Email único
    - **password**: Senha (min 6 caracteres)
    - **nome**: Nome do usuário (opcional)
    """
    # Verificar se email já existe
    existing = session.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    
    # Criar usuário
    user = models.User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        nome=payload.nome,
        is_active=True,
        consent_date=datetime.now(timezone.utc)  # LGPD - aceite dos termos
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    
    # Log de auditoria
    log_action(
        session,
        user.id,
        action="register",
        entity_type="user",
        entity_id=user.id,
        details="Novo usuário registrado"
    )
    
    # Gerar token
    token = create_access_token(data={"sub": str(user.id), "email": user.email})
    
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(
    request: Request,
    payload: LoginRequest,
    session: DBSession = Depends(db.get_session)
):
    """
    Login com email e senha.
    Suporta 2FA se habilitado.
    
    auth_mode é ativado automaticamente pelo TenantContextMiddleware
    """
    try:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent")
        
        # Buscar usuário
        user = session.query(models.User).filter(models.User.email == payload.email).first()
        
        if not user or not verify_password(payload.password, user.hashed_password):
            log_login(session, user.id if user else 0, ip_address, user_agent or "", success=False)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha incorretos",
            )
        
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Conta desativada")
        
        # Verificar 2FA (se habilitado)
        if user.two_factor_enabled:
            if not payload.code_2fa:
                raise HTTPException(
                    status_code=403,
                    detail="Código 2FA obrigatório",
                    headers={"X-Require-2FA": "true"}
                )
            
            # Validar código TOTP
            totp = pyotp.TOTP(user.two_factor_secret)
            if not totp.verify(payload.code_2fa, valid_window=5):
                raise HTTPException(status_code=401, detail="Código 2FA inválido")
        
        # Criar sessão
        db_session = create_session(
            db=session,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Log de auditoria
        log_login(session, user.id, ip_address or "", user_agent or "", success=True)
        
        # Gerar token com JTI da sessão
        token = create_access_token(
            data={"sub": str(user.id), "email": user.email},
            jti=db_session.token_jti
        )
        
        return TokenResponse(access_token=token)
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro no login: {str(e)}")


@router.post("/logout")
def logout(
    request: Request,
    current_user: models.User = Depends(get_current_user),
    session: DBSession = Depends(db.get_session)
):
    """
    Logout - revoga sessão atual.
    """
    ip_address = request.client.host if request.client else None
    
    # Revogar todas as sessões do usuário
    revoked_count = revoke_all_sessions(session, current_user.id)
    
    # Log
    log_logout(session, current_user.id, ip_address or "")
    
    return {
        "message": "Logout realizado com sucesso",
        "sessions_revoked": revoked_count
    }


@router.get("/me", response_model=UserResponse)
def get_me(current_user: models.User = Depends(get_current_user)):
    """
    Retorna informações do usuário logado.
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "nome": current_user.nome,
        "is_admin": current_user.is_admin,
        "is_active": current_user.is_active,
        "two_factor_enabled": current_user.two_factor_enabled,
        "consent_date": current_user.consent_date
    }


@router.get("/sessions")
def get_sessions(
    current_user: models.User = Depends(get_current_user),
    session: DBSession = Depends(db.get_session)
):
    """
    Lista sessões ativas do usuário.
    """
    sessions = get_active_sessions(session, current_user.id)
    
    return {
        "sessions": [
            {
                "id": s.id,
                "ip_address": s.ip_address,
                "user_agent": s.user_agent,
                "created_at": s.created_at,
                "last_activity_at": s.last_activity_at,
                "expires_at": s.expires_at
            }
            for s in sessions
        ]
    }


# ====================
# PLACEHOLDER: RECUPERAÇÃO DE SENHA
# ====================
# Implementar depois:
# - /forgot-password (envia email com token)
# - /reset-password (valida token e redefine senha)
# - /enable-2fa (ativa 2FA, retorna QR code)
# - /disable-2fa (desativa 2FA)
