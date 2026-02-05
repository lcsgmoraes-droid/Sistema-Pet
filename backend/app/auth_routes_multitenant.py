"""
Rotas de Autenticação Multi-Tenant
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta, timezone
from jose import jwt
import uuid

from app.db import get_session
from app import models
from app.auth import (
    verify_password, 
    create_access_token, 
    get_current_user
)
from app.auth.permission_dependencies import expand_permissions
from app.config import JWT_SECRET_KEY as SECRET_KEY
from app.auth.core import ALGORITHM, ACCESS_TOKEN_EXPIRE_DAYS
from app.session_manager import create_session, validate_session, revoke_session, get_active_sessions, get_session_by_jti
from app.auth.dependencies import get_current_user_and_tenant
# from app.audit import log_audit  # TODO: Fix audit import conflict

security = HTTPBearer()
router = APIRouter(prefix="/auth", tags=["auth-multitenant"])


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict
    tenants: List[dict]


class SelectTenantRequest(BaseModel):
    tenant_id: str


class SelectTenantResponse(BaseModel):
    access_token: str
    token_type: str
    tenant: dict


@router.post("/login-multitenant", response_model=LoginResponse)
def login_multitenant(request: Request, credentials: LoginRequest, db: Session = Depends(get_session)):
    """
    Fase 1: Autentica usuário e retorna lista de tenants disponíveis.
    Token gerado SEM tenant_id.
    """
    user = db.query(models.User).filter(models.User.email == credentials.email).first()
    
    if not user or not verify_password(credentials.password, user.hashed_password):
        # log_audit(
        #     db=db,
        #     user_id=user.id if user else None,
        #     action="login_failed",
        #     entity_type="user",
        #     entity_id=user.id if user else None,
        #     ip_address=request.client.host if request.client else None,
        #     user_agent=request.headers.get("user-agent")
        # )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo",
        )
    
    user_tenants = db.query(models.UserTenant).filter(
        models.UserTenant.user_id == user.id
    ).all()
    
    if not user_tenants:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário não possui acesso a nenhum tenant",
        )
    
    # Criar sessão (gera o JTI internamente)
    db_session = create_session(
        db=db,
        user_id=user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        expires_in_days=ACCESS_TOKEN_EXPIRE_DAYS
    )
    
    # Usar o JTI gerado pela sessão
    token_jti = db_session.token_jti
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "jti": token_jti,
            "tenant_id": None
        }
    )
    
    # log_audit(
    #     db=db,
    #     user_id=user.id,
    #     action="login_success",
    #     entity_type="user",
    #     entity_id=user.id,
    #     ip_address=request.client.host if request.client else None,
    #     user_agent=request.headers.get("user-agent")
    # )
    
    tenants_list = []
    for ut in user_tenants:
        tenant = db.query(models.Tenant).filter(models.Tenant.id == ut.tenant_id).first()
        if tenant:
            tenants_list.append({
                "id": str(tenant.id),
                "name": tenant.name,
                "role_id": ut.role_id
            })
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user={
            "id": user.id,
            "name": user.nome,
            "email": user.email,
            "is_active": user.is_active
        },
        tenants=tenants_list
    )


@router.post("/select-tenant", response_model=SelectTenantResponse)
def select_tenant(
    request: Request,
    body: SelectTenantRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_session),
    current_user: models.User = Depends(get_current_user)
):
    """
    Fase 2: Seleciona tenant e gera token COM tenant_id.
    REUTILIZA a sessão criada no login.
    """
    from uuid import UUID
    
    try:
        tenant_uuid = UUID(body.tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id inválido"
        )
    
    user_tenant = db.query(models.UserTenant).filter(
        models.UserTenant.user_id == current_user.id,
        models.UserTenant.tenant_id == tenant_uuid
    ).first()
    
    if not user_tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem acesso a este tenant"
        )
    
    tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_uuid).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant não encontrado"
        )
    
    # Extrair JTI do token atual
    token = credentials.credentials
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    token_jti = payload.get("jti")
    
    if not token_jti:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido - JTI não encontrado"
        )
    
    # Buscar sessão EXISTENTE
    db_session = get_session_by_jti(db, token_jti)
    
    if not db_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão não encontrada. Faça login novamente."
        )
    
    # Atualizar tenant_id na sessão EXISTENTE
    db_session.tenant_id = tenant_uuid
    db.commit()
    
    # Gerar NOVO token COM tenant_id (MESMO JTI)
    access_token = create_access_token(
        data={
            "sub": str(current_user.id),
            "jti": token_jti,
            "tenant_id": str(tenant_uuid)
        }
    )
    
    # log_audit(
    #     db=db,
    #     user_id=current_user.id,
    #     action="tenant_selected",
    #     entity_type="tenant",
    #     entity_id=str(tenant_uuid),
    #     ip_address=request.client.host if request.client else None,
    #     user_agent=request.headers.get("user-agent"),
    #     tenant_id=tenant_uuid
    # )
    
    return SelectTenantResponse(
        access_token=access_token,
        token_type="bearer",
        tenant={
            "id": str(tenant.id),
            "name": tenant.name,
            "role_id": user_tenant.role_id
        }
    )


@router.get("/me-multitenant")
def get_me_multitenant(
    db: Session = Depends(get_session),
    user_and_tenant = Depends(get_current_user_and_tenant),
):
    """
    Retorna dados do usuário no contexto multi-tenant.
    
    ORDEM GARANTIDA:
    1. get_current_user valida token + seta tenant no contexto
    2. get_current_user_and_tenant valida tenant no contexto
    3. Endpoint usa current_user + tenant_id
    """
    current_user, tenant_id = user_and_tenant
    
    user_tenant = db.query(models.UserTenant).filter(
        models.UserTenant.user_id == current_user.id,
        models.UserTenant.tenant_id == tenant_id
    ).first()
    
    if not user_tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário não tem acesso ao tenant selecionado"
        )
    
    tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    
    role = None
    if user_tenant.role_id:
        role = db.query(models.Role).filter(models.Role.id == user_tenant.role_id).first()
    
    permissions = []
    if role:
        role_permissions = db.query(models.RolePermission).filter(
            models.RolePermission.role_id == role.id
        ).all()
        
        for rp in role_permissions:
            perm = db.query(models.Permission).filter(
                models.Permission.id == rp.permission_id
            ).first()
            if perm:
                permissions.append(perm.code)
    
    # 🔑 EXPANSÃO AUTOMÁTICA: Adicionar dependências implícitas
    permissions = expand_permissions(permissions)
    
    return {
        "id": current_user.id,
        "name": current_user.nome,
        "email": current_user.email,
        "is_active": current_user.is_active,
        "tenant": {
            "id": str(tenant.id),
            "name": tenant.name
        } if tenant else None,
        "role": {
            "id": role.id,
            "name": role.name
        } if role else None,
        "permissions": permissions
    }


@router.post("/logout-multitenant")
def logout_multitenant(
    db: Session = Depends(get_session),
    current_user: models.User = Depends(get_current_user)
):
    """
    Revoga todas as sessões do usuário.
    """
    sessions = get_active_sessions(db, current_user.id)
    
    for session in sessions:
        revoke_session(db, session.id, current_user.id, "user_logout")
    
    return {"message": "Logout realizado com sucesso"}
