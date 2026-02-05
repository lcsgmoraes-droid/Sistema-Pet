from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.db import get_session
from app.auth import get_current_user_and_tenant
from app.auth.core import hash_password
from app.tenancy.context import get_current_tenant
from app.security.permissions_decorator import require_permission
from app.models import User, UserTenant, Role

router = APIRouter(prefix="/usuarios", tags=["Usuários"])


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UsuarioListResponse(BaseModel):
    user_id: int
    email: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool

    class Config:
        from_attributes = True


@router.get("", response_model=list[UsuarioListResponse])
@require_permission("usuarios.manage")
def listar_usuarios(
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    """Lista usuários do tenant com informações de role e status"""
    current_user, tenant_id = user_and_tenant

    rows = (
        db.query(
            User.id.label("user_id"),
            User.email,
            Role.name.label("role"),
            UserTenant.is_active,
        )
        .join(UserTenant, UserTenant.user_id == User.id)
        .join(Role, Role.id == UserTenant.role_id)
        .filter(UserTenant.tenant_id == tenant_id)
        .all()
    )

    return rows


@router.post("", response_model=UserResponse)
@require_permission("usuarios.manage")
def criar_usuario(
    payload: UserCreate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = user_and_tenant
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Usuário com este email já existe",
        )

    # Criar usuário
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),  # Hash com bcrypt
        is_active=True,
        tenant_id=tenant_id,
    )
    db.add(user)
    db.flush()  # Garante que user.id seja gerado

    # Buscar role padrão "admin" (não existe 'user' no sistema)
    role_admin = db.query(Role).filter(Role.name == "admin").first()
    if not role_admin:
        raise HTTPException(
            status_code=500,
            detail="Role 'admin' não encontrada no sistema",
        )

    # Criar vínculo UserTenant para o usuário aparecer na lista
    vinculo = UserTenant(
        user_id=user.id,
        tenant_id=tenant_id,
        role_id=role_admin.id,
        is_active=True,
    )
    db.add(vinculo)
    db.commit()
    db.refresh(user)

    return user


# ==========================================
# ETAPA B2 — VINCULAR USUÁRIO AO TENANT
# ==========================================

class VinculoCreate(BaseModel):
    role_id: int


class StatusUpdate(BaseModel):
    is_active: bool


@router.post("/{user_id}/vincular")
@require_permission("usuarios.manage")
def vincular_usuario(
    user_id: int,
    payload: VinculoCreate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = user_and_tenant

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    role = (
        db.query(Role)
        .filter(Role.id == payload.role_id, Role.tenant_id == tenant_id)
        .first()
    )
    if not role:
        raise HTTPException(status_code=400, detail="Role inválido para este tenant")

    existing = (
        db.query(UserTenant)
        .filter(
            UserTenant.user_id == user_id,
            UserTenant.tenant_id == tenant_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Usuário já vinculado a este tenant")

    vinculo = UserTenant(
        user_id=user_id,
        tenant_id=tenant_id,
        role_id=role.id,
        is_active=True,
    )
    db.add(vinculo)
    db.commit()

    return {"status": "ok", "message": "Usuário vinculado com sucesso"}


@router.patch("/{user_id}/status")
@require_permission("usuarios.manage")
def atualizar_status_usuario(
    user_id: int,
    payload: StatusUpdate,
    db: Session = Depends(get_session),
    user_and_tenant=Depends(get_current_user_and_tenant),
):
    current_user, tenant_id = user_and_tenant

    vinculo = (
        db.query(UserTenant)
        .filter(
            UserTenant.user_id == user_id,
            UserTenant.tenant_id == tenant_id,
        )
        .first()
    )
    if not vinculo:
        raise HTTPException(status_code=404, detail="Usuário não vinculado a este tenant")

    vinculo.is_active = payload.is_active
    db.commit()

    return {"status": "ok", "is_active": vinculo.is_active}
